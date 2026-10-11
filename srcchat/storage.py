import hashlib
import json
import tempfile
import time
from pathlib import Path
from typing import Optional

from langchain_chroma import Chroma
from tqdm.auto import tqdm

from .config import DATA_DIR, EMBED_MODEL, MAX_CHUNKS_PER_REPO, MAX_REPOS, REG_FILE
from .ingestion import (
    build_documents,
    cleanup,
    collect_files,
    overview_doc,
    parse_github_url,
    precheck_size,
    shallow_clone,
)
from .ollama import get_embeddings

DATA_DIR.mkdir(exist_ok=True)
_embeddings = None
_vectorstore = None


def get_vectorstore():
    global _embeddings, _vectorstore
    if _vectorstore is None:
        if _embeddings is None:
            _embeddings = get_embeddings()
        _vectorstore = Chroma(
            collection_name="repochat",
            embedding_function=_embeddings,
            persist_directory=str(DATA_DIR / "chroma"),
            collection_metadata={"hnsw:space": "cosine"},
        )
    return _vectorstore


def load_registry() -> dict:
    return json.loads(REG_FILE.read_text()) if REG_FILE.exists() else {}


def save_registry():
    REG_FILE.write_text(json.dumps(registry, indent=2))


registry = load_registry()


def resolve_repos(repos=None):
    if not registry:
        raise ValueError("No repos indexed yet. Use add_repo(url) first.")
    if not repos:
        return list(registry)
    out = []
    for r in repos:
        hits = [k for k in registry if k.lower() == r.lower() or k.split("/")[1].lower() == r.lower()]
        if len(hits) != 1:
            raise ValueError(f"Repo '{r}' not found. Indexed: {list(registry)}")
        out.append(hits[0])
    return out


def add_repo(url: str, branch: Optional[str] = None, subdir: Optional[str] = None):
    """Index a public GitHub repo. Re-running for the same repo replaces its old data."""
    t0 = time.time()
    owner, name = parse_github_url(url)
    key = f"{owner}/{name}"
    if key not in registry and len(registry) >= MAX_REPOS:
        raise ValueError(f"Limit reached: {MAX_REPOS} repos. Use remove_repo(...) first.")
    precheck_size(owner, name)

    tmp = tempfile.mkdtemp(prefix="repochat_")
    try:
        print(f"[1/4] cloning {key} ...")
        sha = shallow_clone(f"https://github.com/{key}", tmp, branch)   # rebuilt from validated parts
        print("[2/4] scanning files ...")
        files, skipped = collect_files(Path(tmp), subdir)
        if not files:
            raise ValueError("No indexable text or code files found (check subdir).")
        print(f"[3/4] chunking {len(files)} files ...")
        docs = build_documents(key, sha, files)
        docs.insert(0, overview_doc(key, sha, Path(tmp).resolve(), files))
        if len(docs) > MAX_CHUNKS_PER_REPO:
            raise ValueError(f"{len(docs)} chunks exceeds the limit of {MAX_CHUNKS_PER_REPO}. "
                             "Pass subdir=... to index only part of the repo.")
    finally:
        cleanup(tmp)

    print(f"[4/4] embedding {len(docs)} chunks with {EMBED_MODEL} ...")
    vs = get_vectorstore()
    try:
        vs._collection.delete(where={"repo": key})   # replace any previous index of this repo
    except Exception:
        pass
    ids = [hashlib.sha1(f"{key}|{d.metadata['path']}|{i}".encode()).hexdigest() for i, d in enumerate(docs)]
    for i in tqdm(range(0, len(docs), 32), unit="batch"):
        vs.add_documents(docs[i:i + 32], ids=ids[i:i + 32])

    langs = sorted({lang for _, _, lang in files})
    registry[key] = {"sha": sha[:10], "subdir": subdir, "files": len(files), "chunks": len(docs),
                     "languages": langs, "skipped": skipped, "seconds": round(time.time() - t0, 1)}
    save_registry()
    print(f"Indexed {key}@{sha[:7]}: {len(files)} files, {len(docs)} chunks, languages={langs}, "
          f"skipped={skipped}, took {time.time() - t0:.0f}s")


def list_repos():
    if not registry:
        print("No repos indexed yet.")
    for k, v in registry.items():
        print(f"{k:35s} {v['files']:5d} files {v['chunks']:6d} chunks  {', '.join(v['languages'])}")


def remove_repo(name: str):
    key = resolve_repos([name])[0]
    vs = get_vectorstore()
    vs._collection.delete(where={"repo": key})
    registry.pop(key, None)
    save_registry()
    print("removed", key)
