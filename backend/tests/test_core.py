import pytest
from app.core.validator import validate_and_normalize_github_url
from app.core.secret_masker import mask_secrets, is_sensitive_file
from app.core.language import detect_language, should_skip_file
from app.ingest.chunker import CodeChunker
from app.retrieval.retriever import compute_rrf


def test_url_validation_valid():
    url, owner, repo = validate_and_normalize_github_url("https://github.com/fastapi/fastapi")
    assert url == "https://github.com/fastapi/fastapi"
    assert owner == "fastapi"
    assert repo == "fastapi"

    url2, owner2, repo2 = validate_and_normalize_github_url("https://github.com/torvalds/linux.git/")
    assert url2 == "https://github.com/torvalds/linux"
    assert owner2 == "torvalds"
    assert repo2 == "linux"


def test_url_validation_invalid_and_ssrf():
    # Non-github domains
    with pytest.raises(ValueError, match="Only public GitHub"):
        validate_and_normalize_github_url("https://gitlab.com/owner/repo")
    
    with pytest.raises(ValueError, match="Only public GitHub"):
        validate_and_normalize_github_url("http://169.254.169.254/latest/meta-data")

    # Insecure HTTP
    with pytest.raises(ValueError, match="HTTPS"):
        validate_and_normalize_github_url("http://github.com/owner/repo")

    # Invalid path
    with pytest.raises(ValueError, match="Invalid GitHub repository"):
        validate_and_normalize_github_url("https://github.com/owner")


def test_secret_masker():
    raw_code = """
    const API_KEY = "sk-1234567890abcdef1234567890abcdef";
    const awsKey = "AKIA1234567890ABCDEF";
    const normalVar = "hello world";
    """
    masked = mask_secrets(raw_code)
    assert "AKIA1234567890ABCDEF" not in masked
    assert "[REDACTED_AWS_KEY]" in masked
    assert "sk-1234567890abcdef1234567890abcdef" not in masked
    assert "hello world" in masked


def test_sensitive_file_detection():
    assert is_sensitive_file(".env") is True
    assert is_sensitive_file(".env.local") is True
    assert is_sensitive_file("id_rsa") is True
    assert is_sensitive_file("server.key") is True
    assert is_sensitive_file("main.py") is False


def test_language_detection():
    assert detect_language("app/main.py") == "python"
    assert detect_language("frontend/src/App.tsx") == "typescript"
    assert detect_language("script.sh", first_line="#!/bin/bash") == "bash"


def test_file_skip_filters():
    skip, reason = should_skip_file("node_modules/package/index.js", 100)
    assert skip is True
    assert "ignored directory" in reason

    skip2, reason2 = should_skip_file("package-lock.json", 100)
    assert skip2 is True
    assert "lockfile" in reason2

    # Oversized file
    skip3, reason3 = should_skip_file("huge.json", 350 * 1024, max_file_size_kb=300)
    assert skip3 is True
    assert "exceeds file size limit" in reason3


def test_code_chunker_basic():
    chunker = CodeChunker(max_chunk_lines=20, overlap_lines=5)
    content = "\n".join([f"line_{i} = {i}" for i in range(1, 51)])
    chunks = chunker.chunk_file("my-repo", "src/util.py", "python", content)
    assert len(chunks) > 1
    assert chunks[0].start_line == 1
    assert "my-repo" in chunks[0].text


def test_rrf_scoring():
    rank_list_1 = [{"chunk_id": "c1"}, {"chunk_id": "c2"}, {"chunk_id": "c3"}]
    rank_list_2 = [{"chunk_id": "c2"}, {"chunk_id": "c1"}, {"chunk_id": "c4"}]
    fused = compute_rrf([rank_list_1, rank_list_2], k=60)
    # c1 and c2 should have higher scores than c3 or c4
    top_ids = [item["chunk_id"] for item in fused[:2]]
    assert "c1" in top_ids and "c2" in top_ids
    assert fused[0]["score"] > fused[-1]["score"]
