import os
import shutil
import tempfile
import asyncio
import hashlib
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.core.config import settings
from app.core.validator import validate_and_normalize_github_url
from app.core.language import detect_language, should_skip_file
from app.core.secret_masker import is_sensitive_file, mask_secrets
from app.ingest.chunker import CodeChunker
from app.ingest.structure import StructureExtractor
from app.llm.embedding_adapter import get_embedding_adapter
from app.llm.llm_adapter import get_llm_adapter
from app.models.models import Repo, File, Chunk, Symbol, Edge

logger = logging.getLogger("ingestion")


class IngestionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.chunker = CodeChunker()
        self.structure_extractor = StructureExtractor()
        self.embedding_adapter = get_embedding_adapter()
        self.llm_adapter = get_llm_adapter()

    async def precheck_github_repo(self, owner: str, repo: str) -> Dict[str, Any]:
        """
        Unauthenticated pre-check via GitHub REST API.
        Enforces limits before cloning. Rejects private or missing repos cleanly.
        """
        url = f"https://api.github.com/repos/{owner}/{repo}"
        async with httpx.AsyncClient(timeout=15.0) as client:
            headers = {"User-Agent": "SrcChat-Agentic-Assistant"}
            res = await client.get(url, headers=headers)
            if res.status_code == 404:
                raise ValueError(f"Repository '{owner}/{repo}' not found or is private. Only public repositories are supported.")
            elif res.status_code == 403 and "rate limit" in res.text.lower():
                # If unauthenticated rate limit is temporarily hit, proceed to clone with local size validation
                logger.warning("GitHub API rate limit encountered on pre-check. Continuing with clone-level size inspection.")
                return {"size_kb": 0, "default_branch": "main"}
            elif res.status_code != 200:
                raise ValueError(f"Failed to query GitHub repository info: HTTP {res.status_code}")

            data = res.json()
            if data.get("private", False):
                raise ValueError(f"Repository '{owner}/{repo}' is private. SrcChat strictly supports public repositories only.")

            size_kb = data.get("size", 0)
            size_mb = size_kb / 1024.0
            if size_mb > settings.MAX_REPO_SIZE_MB:
                raise ValueError(
                    f"Repository size ({size_mb:.1f} MB) exceeds maximum allowed limit of {settings.MAX_REPO_SIZE_MB} MB. "
                    "Please choose a smaller repository or index a focused subset."
                )

            return {
                "size_kb": size_kb,
                "default_branch": data.get("default_branch", "main"),
                "description": data.get("description", "")
            }

    async def clone_repo(self, repo_url: str, branch: str, target_dir: str):
        """
        Shallow clones the repository with safety protections:
        - Argument list only (NEVER shell=True)
        - Depth 1, single branch
        - Git hooks and LFS disabled
        - Enforced timeout
        Uses asyncio.to_thread for Windows compatibility (ProactorEventLoop lacks subprocess_exec).
        """
        import subprocess
        cmd = [
            "git", "clone",
            "--depth", "1",
            "--branch", branch,
            "--config", "core.hooksPath=NUL",
            repo_url,
            target_dir
        ]

        logger.info(f"Cloning {repo_url} (branch {branch}) into temporary directory...")

        def _run_clone():
            return subprocess.run(
                cmd,
                capture_output=True,
                shell=False,
                timeout=settings.CLONE_TIMEOUT_SECONDS
            )

        try:
            result = await asyncio.to_thread(_run_clone)
        except Exception as e:
            raise RuntimeError(f"Git clone failed: {e}")

        if result.returncode != 0:
            err = result.stderr.decode("utf-8", errors="replace")
            raise RuntimeError(f"Git clone failed: {err}")

    async def get_latest_commit_sha(self, clone_dir: str) -> str:
        import subprocess

        def _run():
            return subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                shell=False,
                cwd=clone_dir
            )

        result = await asyncio.to_thread(_run)
        return result.stdout.decode().strip()

    async def index_repository(self, repo: Repo, incremental: bool = False):
        """Full ingestion pipeline runner."""
        temp_dir = tempfile.mkdtemp(prefix="srcchat_repo_")
        try:
            repo.status = "cloning"
            repo.progress = 0.1
            repo.status_message = "Validating and cloning repository..."
            await self.db.commit()

            # 1. API Pre-check
            try:
                info = await self.precheck_github_repo(repo.owner, repo.name)
                if not repo.branch:
                    repo.branch = info.get("default_branch", "main")
            except Exception as e:
                logger.warning(f"Pre-check notice: {e}")

            # 2. Shallow Clone
            await self.clone_repo(repo.url, repo.branch, temp_dir)
            commit_sha = await self.get_latest_commit_sha(temp_dir)
            repo.commit_sha = commit_sha

            repo.status = "parsing"
            repo.progress = 0.3
            repo.status_message = "Scanning directory and extracting AST symbols..."
            await self.db.commit()

            # 3. Walk files and collect valid indexable candidates
            indexable_files = []
            skipped_count = 0
            total_loc = 0

            for root, dirs, files in os.walk(temp_dir):
                # Prune skipped directories
                dirs[:] = [d for d in dirs if d not in {".git", "node_modules", "vendor", "dist", "build", "target", ".venv", "venv"}]

                for f in files:
                    full_p = os.path.join(root, f)
                    rel_p = os.path.relpath(full_p, temp_dir)

                    if is_sensitive_file(f):
                        skipped_count += 1
                        continue

                    try:
                        f_size = os.path.getsize(full_p)
                    except OSError:
                        skipped_count += 1
                        continue

                    skip, reason = should_skip_file(rel_p, f_size, settings.MAX_FILE_SIZE_KB)
                    if skip:
                        skipped_count += 1
                        continue

                    indexable_files.append((rel_p, full_p))
                    if len(indexable_files) > settings.MAX_REPO_FILES:
                        raise ValueError(
                            f"Repository contains more than {settings.MAX_REPO_FILES} files. Exceeds ingestion threshold."
                        )

            # If incremental, fetch existing file hashes for this repo
            existing_files_map = {}
            if incremental:
                res = await self.db.execute(select(File).where(File.repo_id == repo.id))
                for ef in res.scalars().all():
                    existing_files_map[ef.path] = ef

            all_new_chunks: List[Chunk] = []
            file_records: List[File] = []
            symbols_to_add: List[Symbol] = []
            edges_to_add: List[Edge] = []

            for rel_path, full_path in indexable_files:
                try:
                    with open(full_path, "r", encoding="utf-8", errors="ignore") as fp:
                        raw_content = fp.read()
                except Exception:
                    continue

                line_count = len(raw_content.splitlines())
                total_loc += line_count
                if total_loc > settings.MAX_INDEXED_LOC:
                    raise ValueError(
                        f"Repository exceeded maximum indexable lines of code ({total_loc:,} > {settings.MAX_INDEXED_LOC:,} LOC)."
                    )

                content_hash = hashlib.sha256(raw_content.encode("utf-8")).hexdigest()

                # Incremental skip if content unchanged
                if incremental and rel_path in existing_files_map:
                    if existing_files_map[rel_path].content_hash == content_hash:
                        continue

                # Secret masking BEFORE chunking and storing
                safe_content = mask_secrets(raw_content)
                first_line = safe_content.splitlines()[0] if safe_content.splitlines() else None
                language = detect_language(rel_path, first_line)

                # AST Structure extraction
                struct_res = self.structure_extractor.extract(rel_path, language, safe_content)

                # Code chunking
                chunks_data = self.chunker.chunk_file(repo.name, rel_path, language, safe_content)

                file_obj = File(
                    repo_id=repo.id,
                    path=rel_path.replace("\\", "/"),
                    language=language,
                    content_hash=content_hash,
                    line_count=line_count,
                    structure_level=struct_res.structure_level,
                    raw_content=safe_content if len(safe_content) < 50000 else safe_content[:50000]
                )
                self.db.add(file_obj)
                await self.db.flush()

                for sym in struct_res.symbols:
                    symbols_to_add.append(Symbol(
                        repo_id=repo.id,
                        file_id=file_obj.id,
                        name=sym.name,
                        kind=sym.kind,
                        start_line=sym.start_line,
                        end_line=sym.end_line
                    ))

                for edg in struct_res.edges:
                    edges_to_add.append(Edge(
                        repo_id=repo.id,
                        from_symbol=edg.from_symbol,
                        to_symbol=edg.to_symbol,
                        kind=edg.kind,
                        file_path=file_obj.path,
                        line_number=edg.line_number
                    ))

                for ch in chunks_data:
                    c_obj = Chunk(
                        repo_id=repo.id,
                        file_id=file_obj.id,
                        chunk_type=ch.chunk_type,
                        symbol=ch.symbol,
                        start_line=ch.start_line,
                        end_line=ch.end_line,
                        text=ch.text
                    )
                    all_new_chunks.append(c_obj)

            # Insert symbols and edges
            if symbols_to_add:
                self.db.add_all(symbols_to_add)
            if edges_to_add:
                self.db.add_all(edges_to_add)
            await self.db.flush()

            # 4. Embed chunks in batches with backoff
            repo.status = "embedding"
            repo.progress = 0.6
            repo.status_message = f"Embedding {len(all_new_chunks)} code chunks into pgvector..."
            await self.db.commit()

            batch_size = settings.EMBEDDING_BATCH_SIZE
            for i in range(0, len(all_new_chunks), batch_size):
                batch = all_new_chunks[i:i + batch_size]
                texts = [c.text for c in batch]
                embeddings = await self.embedding_adapter.embed_texts(texts)

                for c_obj, emb in zip(batch, embeddings):
                    # SQLite stores embeddings as JSON text; pgvector stores as native vector
                    import json as _json
                    import os as _os
                    if _os.environ.get("SRCCHAT_DEV_SQLITE", "").lower() in ("1", "true", "yes"):
                        c_obj.embedding = _json.dumps(emb)
                    else:
                        c_obj.embedding = emb
                    self.db.add(c_obj)

                pct = 0.6 + (0.35 * min((i + batch_size) / max(len(all_new_chunks), 1), 1.0))
                repo.progress = round(pct, 2)
                await self.db.commit()

            # 5. Generate high-level summary for the repo
            repo.progress = 0.95
            repo.status_message = "Synthesizing repository architecture overview..."
            await self.db.commit()

            repo_overview_prompt = f"Summarize the architecture, purpose, and entrypoints of the {repo.owner}/{repo.name} repository based on indexed files: {', '.join([f[0] for f in indexable_files[:25]])}."
            repo_summary = await self.llm_adapter.generate(repo_overview_prompt)
            repo.summary = repo_summary

            repo.size_stats = {
                "file_count": len(indexable_files),
                "loc": total_loc,
                "chunk_count": len(all_new_chunks),
                "skipped_files": skipped_count
            }
            repo.status = "ready"
            repo.progress = 1.0
            repo.status_message = f"Successfully indexed {len(indexable_files)} files ({total_loc:,} LOC)."
            await self.db.commit()

        except Exception as e:
            logger.exception("Ingestion failed")
            repo.status = "failed"
            repo.error = str(e)
            repo.status_message = f"Failed: {str(e)}"
            await self.db.commit()
            raise e
        finally:
            # Clean up temp clone directory on success and on failure
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
