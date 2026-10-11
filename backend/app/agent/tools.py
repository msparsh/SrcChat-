from typing import List, Dict, Any, Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from app.retrieval.retriever import HybridRetriever
from app.models.models import File, Chunk, Symbol, Edge, Repo


class AgentToolRegistry:
    """Read-only toolset over the indexed repository database. NEVER accesses the live filesystem."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.retriever = HybridRetriever(db)

    async def semantic_search(
        self,
        query: str,
        repos: Optional[List[str]] = None,
        language: Optional[str] = None,
        path_prefix: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Searches indexed code vectors and keyword index using hybrid search."""
        repo_ids = await self._resolve_repo_ids(repos)
        if repos and not repo_ids:
            return []
        results = await self.retriever.search(
            query=query,
            repo_ids=repo_ids,
            language=language,
            path_prefix=path_prefix,
            top_k=8
        )
        return [
            {
                "repo": r.repo_name,
                "file": r.file_path,
                "lines": f"{r.start_line}-{r.end_line}",
                "symbol": r.symbol,
                "content": r.text
            }
            for r in results
        ]

    async def keyword_search(self, pattern: str, repos: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Performs exact/trigram substring search across indexed chunks."""
        repo_ids = await self._resolve_repo_ids(repos)
        if repos and not repo_ids:
            return []
        stmt = (
            select(Repo.name, File.path, Chunk.start_line,
                   Chunk.end_line, Chunk.text)
            .join(File, Chunk.file_id == File.id)
            .join(Repo, Chunk.repo_id == Repo.id)
            .where(Chunk.text.ilike(f"%{pattern}%"))
        )
        if repo_ids:
            stmt = stmt.where(Chunk.repo_id.in_(repo_ids))
        stmt = stmt.limit(10)

        res = await self.db.execute(stmt)
        return [
            {
                "repo": r[0],
                "file": r[1],
                "lines": f"{r[2]}-{r[3]}",
                "content": r[4]
            }
            for r in res.all()
        ]

    async def read_file(
        self,
        repo: str,
        path: str,
        line_start: Optional[int] = None,
        line_end: Optional[int] = None
    ) -> Dict[str, Any]:
        """Reconstructs and reads a stored file text or line range."""
        clean_path = path.replace("\\", "/").lstrip("/")
        stmt = (
            select(File, Repo.name)
            .join(Repo, File.repo_id == Repo.id)
            .where(Repo.name.ilike(repo), File.path.ilike(clean_path))
        )
        res = await self.db.execute(stmt)
        row = res.first()
        if not row:
            return {"error": f"File '{path}' in repository '{repo}' not found in index."}

        file_obj, repo_name = row
        raw = file_obj.raw_content or ""
        lines = raw.splitlines()

        if line_start is not None and line_end is not None:
            selected_lines = lines[max(0, line_start - 1):line_end]
            content = "\n".join(selected_lines)
            return {
                "repo": repo_name,
                "path": file_obj.path,
                "line_range": f"{line_start}-{line_end}",
                "total_lines": len(lines),
                "content": content
            }

        return {
            "repo": repo_name,
            "path": file_obj.path,
            "total_lines": len(lines),
            "content": raw[:20000]  # Safe cap
        }

    async def list_tree(self, repo: str, path_prefix: Optional[str] = None) -> List[str]:
        """Lists directory tree from indexed file paths."""
        stmt = select(File.path).join(Repo, File.repo_id ==
                                      Repo.id).where(Repo.name.ilike(repo))
        if path_prefix:
            stmt = stmt.where(File.path.startswith(path_prefix.lstrip("/")))
        stmt = stmt.order_by(File.path).limit(100)
        res = await self.db.execute(stmt)
        return [r[0] for r in res.all()]

    async def find_symbol(self, name: str, repos: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Finds symbol declarations across indexed repos."""
        repo_ids = await self._resolve_repo_ids(repos)
        if repos and not repo_ids:
            return []
        stmt = (
            select(Repo.name, File.path, Symbol.name, Symbol.kind,
                   Symbol.start_line, Symbol.end_line)
            .join(File, Symbol.file_id == File.id)
            .join(Repo, Symbol.repo_id == Repo.id)
            .where(Symbol.name.ilike(name))
        )
        if repo_ids:
            stmt = stmt.where(Symbol.repo_id.in_(repo_ids))
        stmt = stmt.limit(20)

        res = await self.db.execute(stmt)
        return [
            {
                "repo": r[0],
                "file": r[1],
                "symbol": r[2],
                "kind": r[3],
                "lines": f"{r[4]}-{r[5]}"
            }
            for r in res.all()
        ]

    async def find_references(self, symbol: str, repos: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Finds incoming call and import edges to the given symbol."""
        repo_ids = await self._resolve_repo_ids(repos)
        if repos and not repo_ids:
            return []
        stmt = (
            select(Repo.name, Edge.file_path, Edge.from_symbol,
                   Edge.to_symbol, Edge.kind, Edge.line_number)
            .join(Repo, Edge.repo_id == Repo.id)
            .where(Edge.to_symbol.ilike(f"%{symbol}%"))
        )
        if repo_ids:
            stmt = stmt.where(Edge.repo_id.in_(repo_ids))
        stmt = stmt.limit(25)

        res = await self.db.execute(stmt)
        return [
            {
                "repo": r[0],
                "file": r[1],
                "caller": r[2],
                "callee": r[3],
                "edge_kind": r[4],
                "line": r[5]
            }
            for r in res.all()
        ]

    async def get_repo_overview(self, repo: str) -> Dict[str, Any]:
        """Returns the stored repo summary and top-level statistics."""
        stmt = select(Repo).where(Repo.name.ilike(repo)).order_by(Repo.created_at.desc())
        res = await self.db.execute(stmt)
        repo_obj = res.scalars().first()
        if not repo_obj:
            return {"error": f"Repository '{repo}' not found."}

        return {
            "name": repo_obj.name,
            "owner": repo_obj.owner,
            "url": repo_obj.url,
            "branch": repo_obj.branch,
            "commit_sha": repo_obj.commit_sha,
            "stats": repo_obj.size_stats,
            "summary": repo_obj.summary
        }

    async def _resolve_repo_ids(self, repo_names: Optional[List[str]]) -> Optional[List[uuid.UUID]]:
        if not repo_names:
            return None
        stmt = select(Repo.id).where(
            or_(*[Repo.name.ilike(n) for n in repo_names]))
        res = await self.db.execute(stmt)
        return [r[0] for r in res.all()]
