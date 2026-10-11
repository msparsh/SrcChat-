import pytest
import os
import tempfile
import hashlib
from app.ingest.chunker import CodeChunker
from app.ingest.structure import StructureExtractor
from app.retrieval.retriever import compute_rrf
from app.core.secret_masker import mask_secrets
from app.core.language import detect_language

FIXTURE_FILES = {
    "src/main.py": """
import os
from src.auth import authenticate_user

def run_server():
    print("Starting server")
    user = authenticate_user("admin", "secret123")
    return user
""",
    "src/auth.py": """
def authenticate_user(username: str, password_hash: str):
    if username == "admin":
        return {"id": 1, "username": username}
    return None

def verify_token(token: str):
    return True
""",
    "README.md": """
# Sample Repository
This is a sample project for testing the ingest-to-search pipeline.
## Getting Started
Run python src/main.py to start.
"""
}

# 25 regression evaluation query-file pairs
RETRIEVAL_REGRESSION_SET = [
    ("How does user authentication work?", "src/auth.py"),
    ("Where is authenticate_user defined?", "src/auth.py"),
    ("What function calls authenticate_user?", "src/main.py"),
    ("Where is run_server located?", "src/main.py"),
    ("How to start the server?", "src/main.py"),
    ("What does the README describe?", "README.md"),
    ("Where is verify_token defined?", "src/auth.py"),
    ("Entry point for starting the application", "src/main.py"),
    ("Admin login credentials verification", "src/auth.py"),
    ("Server startup logs", "src/main.py"),
    ("Getting started instructions", "README.md"),
    ("Token verification function", "src/auth.py"),
    ("Authentication module imports", "src/main.py"),
    ("User dictionary format", "src/auth.py"),
    ("Sample repository project title", "README.md"),
    ("Main execution loop", "src/main.py"),
    ("Admin user check", "src/auth.py"),
    ("How to run main.py", "README.md"),
    ("Return value of authenticate_user", "src/auth.py"),
    ("Module preamble in auth", "src/auth.py"),
    ("Server runner definition", "src/main.py"),
    ("Token checker implementation", "src/auth.py"),
    ("Project documentation guide", "README.md"),
    ("Auth handler lookup", "src/auth.py"),
    ("Entry point function definition", "src/main.py"),
]


def test_fixture_ingestion_and_chunking():
    chunker = CodeChunker()
    structure_extractor = StructureExtractor()

    all_chunks = []
    all_symbols = []

    for path, content in FIXTURE_FILES.items():
        safe = mask_secrets(content)
        lang = detect_language(path)
        struct = structure_extractor.extract(path, lang, safe)
        chunks = chunker.chunk_file("sample-repo", path, lang, safe)

        all_chunks.extend(chunks)
        all_symbols.extend(struct.symbols)

    assert len(all_chunks) >= 3
    # Verify symbols detected or fallback handled
    chunk_texts = " ".join([c.text for c in all_chunks])
    assert "authenticate_user" in chunk_texts
    assert "run_server" in chunk_texts


def test_regression_set_coverage():
    """Verify regression test set contains 20+ valid benchmark queries."""
    assert len(RETRIEVAL_REGRESSION_SET) >= 25
    for query, expected_file in RETRIEVAL_REGRESSION_SET:
        assert query.strip() != ""
        assert expected_file in FIXTURE_FILES
