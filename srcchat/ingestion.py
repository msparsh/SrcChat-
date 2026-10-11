import json
import os
import re
import shutil
import stat
import subprocess
import urllib.error
import urllib.request
from collections import defaultdict
from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import Language, RecursiveCharacterTextSplitter

from .config import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    EXT_LANG,
    GITHUB_RE,
    LANG_SPLITTER,
    MAX_FILE_KB,
    MAX_FILES,
    MAX_REPO_MB,
    NAME_LANG,
    SECRET_FILE_RE,
    SECRET_RULES,
    SKIP_DIRS,
    SKIP_FILES,
)


def parse_github_url(url: str):
    url = url.strip().rstrip("/")
    if url.endswith(".git"):
        url = url[:-4]
    m = GITHUB_RE.fullmatch(url)
    if not m or {".", ".."} & set(m.groups()):
        raise ValueError("Only public URLs like https://github.com/owner/repo are accepted.")
    return m.group(1), m.group(2)


def mask_secrets(text: str) -> str:
    for rx, rep in SECRET_RULES:
        text = rx.sub(rep, text)
    return text


_splitters = {}


def get_splitter(lang: str):
    if lang not in _splitters:
        enum = getattr(Language, LANG_SPLITTER.get(lang, ""), None)
        kw = dict(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP, add_start_index=True)
        _splitters[lang] = (
            RecursiveCharacterTextSplitter.from_language(enum, **kw)
            if enum
            else RecursiveCharacterTextSplitter(**kw)
        )
    return _splitters[lang]


def cleanup(path):
    """Delete the temp clone (also works on Windows where .git files are read-only)."""
    def _fix(func, p, *_):
        try:
            os.chmod(p, stat.S_IWRITE)
            func(p)
        except Exception:
            pass

    try:
        shutil.rmtree(path, onexc=_fix)
    except TypeError:
        shutil.rmtree(path, onerror=_fix)


def precheck_size(owner: str, name: str):
    """Ask the GitHub API about the repo BEFORE cloning. Skips quietly if the API is unreachable."""
    req = urllib.request.Request(
        f"https://api.github.com/repos/{owner}/{name}",
        headers={"User-Agent": "repochat", "Accept": "application/vnd.github+json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            info = json.load(r)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise ValueError("Repo not found, or it is private. Only public repos are supported.")
        print(f"(size pre-check skipped: HTTP {e.code})")
        return
    except Exception as e:
        print(f"(size pre-check skipped: {type(e).__name__})")
        return
    mb = info.get("size", 0) / 1024
    if mb > MAX_REPO_MB:
        raise ValueError(f"{owner}/{name} is {mb:.0f} MB (limit {MAX_REPO_MB} MB). Try a smaller repo or pass subdir=...")


def shallow_clone(url: str, dest: Path, branch=None):
    if not shutil.which("git"):
        raise RuntimeError("git is not installed")
    cmd = ["git", "-c", "core.symlinks=false", "clone", "--depth", "1", "--single-branch", "--no-tags"]
    if branch:
        if branch.startswith("-") or not re.fullmatch(r"[A-Za-z0-9._/-]{1,100}", branch):
            raise ValueError("Invalid branch name")
        cmd += ["--branch", branch]
    cmd += ["--", url, str(dest)]
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0", "GIT_LFS_SKIP_SMUDGE": "1"}
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300, env=env)
    if r.returncode != 0:
        raise RuntimeError("git clone failed (private repo, wrong name, or wrong branch?): " + r.stderr.strip()[-300:])
    return subprocess.run(["git", "-C", str(dest), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()


def collect_files(root: Path, subdir=None):
    root = root.resolve()
    base = root
    if subdir:
        base = (root / subdir).resolve()
        if not base.is_dir() or (base != root and root not in base.parents):
            raise ValueError(f"subdir '{subdir}' was not found inside the repo.")
    files, skipped = [], defaultdict(int)
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not os.path.islink(os.path.join(dirpath, d))]
        for fn in filenames:
            p = Path(dirpath) / fn
            if p.is_symlink() or fn in SKIP_FILES or fn.endswith(".min.js") or SECRET_FILE_RE.match(fn):
                skipped["lock/secret/symlink/minified"] += 1
                continue
            lang = NAME_LANG.get(fn) or EXT_LANG.get(p.suffix.lower())
            if not lang:
                skipped["unsupported type"] += 1
                continue
            if p.stat().st_size > MAX_FILE_KB * 1024:
                skipped["too large"] += 1
                continue
            with open(p, "rb") as fh:
                if b"\0" in fh.read(4096):
                    skipped["binary"] += 1
                    continue
            files.append((p, p.resolve().relative_to(root).as_posix(), lang))
            if len(files) > MAX_FILES:
                raise ValueError(f"More than {MAX_FILES} indexable files. Pass subdir=... to index only part of the repo.")
    return sorted(files, key=lambda f: f[1]), dict(skipped)


def build_documents(key: str, sha: str, files):
    docs = []
    for p, rel, lang in files:
        text = mask_secrets(p.read_text(encoding="utf-8", errors="ignore"))
        if not text.strip():
            continue
        for d in get_splitter(lang).create_documents([text]):
            body = d.page_content
            if not body.strip():
                continue
            si = max(d.metadata.get("start_index", 0), 0)
            a = text.count("\n", 0, si) + 1
            b = a + body.count("\n")
            label = f"[{key} {rel}:L{a}-L{b}]"
            docs.append(Document(
                page_content=f"{label}\n{body}",
                metadata={"repo": key, "path": rel, "language": lang, "start_line": a, "end_line": b,
                          "sha": sha, "type": "code",
                          "url": f"https://github.com/{key}/blob/{sha}/{rel}#L{a}-L{b}"}))
    return docs


def overview_doc(key: str, sha: str, root: Path, files):
    """One extra chunk per repo (file tree + README) so questions like 'what is this repo?' work."""
    tree = "\n".join(rel for _, rel, _ in files[:200])
    readme = ""
    for cand in ("README.md", "README.rst", "README.txt", "readme.md"):
        f = root / cand
        if f.is_file() and not f.is_symlink():
            readme = mask_secrets(f.read_text(encoding="utf-8", errors="ignore"))[:2000]
            break
    body = f"Repository overview for {key}\n\nIndexed files:\n{tree}\n\nREADME:\n{readme}"
    return Document(page_content=f"[{key} (overview):L1-L1]\n{body[:4000]}",
                    metadata={"repo": key, "path": "(overview)", "language": "text", "start_line": 1,
                              "end_line": 1, "sha": sha, "type": "overview",
                              "url": f"https://github.com/{key}"})
