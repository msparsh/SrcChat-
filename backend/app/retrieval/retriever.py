from typing import List, Dict, Any, Optional
import uuid
import json
import math
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, text

from app.core.config import settings
from app.llm.embedding_adapter import get_embedding_adapter
from app.models.models import Chunk, File, Repo


@dataclass
class SearchResult:
    chunk_id: str
    repo_id: str
    repo_name: str
    file_path: str
    start_line: int
    end_line: int
    chunk_type: str
    symbol: Optional[str]
    text: str
    score: float


def _compute_cosine_distance(vec1: List[float], vec2: List[float]) -> float:
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 1.0
    dot = 0.0
    norm1 = 0.0
    norm2 = 0.0
    for a, b in zip(vec1, vec2):
        dot += a * b
        norm1 += a * a
        norm2 += b * b
    if norm1 <= 0.0 or norm2 <= 0.0:
        return 1.0
    sim = dot / (math.sqrt(norm1) * math.sqrt(norm2))
    return 1.0 - sim


def compute_rrf(rank_lists: List[List[Dict[str, Any]]], k: int = 60) -> List[Dict[str, Any]]:
    """
    Reciprocal Rank Fusion (RRF).
    RRF score = sum(1.0 / (k + rank)) across each ranked list.
    """
    scores: Dict[str, float] = {}
    item_map: Dict[str, Dict[str, Any]] = {}

    for ranked_list in rank_lists:
        for rank, item in enumerate(ranked_list, start=1):
            cid = item["chunk_id"]
            if cid not in scores:
                scores[cid] = 0.0
                item_map[cid] = item
            scores[cid] += 1.0 / (k + rank)

    sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
    results = []
    for cid in sorted_ids:
        merged = dict(item_map[cid])
        merged["score"] = round(scores[cid], 5)
        results.append(merged)
    return results


class HybridRetriever:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.embedding_adapter = get_embedding_adapter()

    async def search(
        self,
        query: str,
        repo_ids: Optional[List[uuid.UUID]] = None,
        language: Optional[str] = None,
        path_prefix: Optional[str] = None,
        chunk_type: Optional[str] = None,
        top_k: int = 15
    ) -> List[SearchResult]:
        if not query.strip():
            return []

        # 1. Vector Search
        query_embeddings = await self.embedding_adapter.embed_texts([query])
        query_vec = query_embeddings[0] if query_embeddings else None

        vector_results = []
        if query_vec is not None:
            vector_results = await self._vector_search(query_vec, repo_ids, language, path_prefix, chunk_type, limit=top_k * 2)

        # 2. Full-text / Keyword Search
        keyword_results = await self._keyword_search(query, repo_ids, language, path_prefix, chunk_type, limit=top_k * 2)

        # 3. Fuse via RRF
        fused = compute_rrf([vector_results, keyword_results], k=settings.RRF_K)

        final_results = []
        for item in fused[:top_k]:
            final_results.append(SearchResult(
                chunk_id=str(item["chunk_id"]),
                repo_id=str(item["repo_id"]),
                repo_name=item["repo_name"],
                file_path=item["file_path"],
                start_line=item["start_line"],
                end_line=item["end_line"],
                chunk_type=item["chunk_type"],
                symbol=item.get("symbol"),
                text=item["text"],
                score=item["score"]
            ))

        return final_results

    async def _vector_search(
        self,
        query_vec: List[float],
        repo_ids: Optional[List[uuid.UUID]],
        language: Optional[str],
        path_prefix: Optional[str],
        chunk_type: Optional[str],
        limit: int = 30
    ) -> List[Dict[str, Any]]:
        # 1. Try native pgvector cosine distance if supported on model column
        if hasattr(Chunk.embedding, "cosine_distance"):
            try:
                stmt = (
                    select(
                        Chunk.id,
                        Chunk.repo_id,
                        Repo.name.label("repo_name"),
                        File.path.label("file_path"),
                        Chunk.start_line,
                        Chunk.end_line,
                        Chunk.chunk_type,
                        Chunk.symbol,
                        Chunk.text,
                        Chunk.embedding.cosine_distance(query_vec).label("distance")
                    )
                    .join(File, Chunk.file_id == File.id)
                    .join(Repo, Chunk.repo_id == Repo.id)
                )

                conditions = []
                if repo_ids:
                    conditions.append(Chunk.repo_id.in_(repo_ids))
                if language:
                    conditions.append(File.language == language)
                if path_prefix:
                    conditions.append(File.path.startswith(path_prefix))
                if chunk_type:
                    conditions.append(Chunk.chunk_type == chunk_type)

                if conditions:
                    stmt = stmt.where(and_(*conditions))

                stmt = stmt.order_by("distance").limit(limit)

                res = await self.db.execute(stmt)
                rows = res.all()
                return [
                    {
                        "chunk_id": str(r.id),
                        "repo_id": str(r.repo_id),
                        "repo_name": r.repo_name,
                        "file_path": r.file_path,
                        "start_line": r.start_line,
                        "end_line": r.end_line,
                        "chunk_type": r.chunk_type,
                        "symbol": r.symbol,
                        "text": r.text,
                    }
                    for r in rows
                ]
            except Exception:
                pass

        # 2. In-memory cosine distance fallback (e.g. SQLite dev mode or text-stored embeddings)
        try:
            stmt = (
                select(
                    Chunk.id,
                    Chunk.repo_id,
                    Repo.name.label("repo_name"),
                    File.path.label("file_path"),
                    Chunk.start_line,
                    Chunk.end_line,
                    Chunk.chunk_type,
                    Chunk.symbol,
                    Chunk.text,
                    Chunk.embedding
                )
                .join(File, Chunk.file_id == File.id)
                .join(Repo, Chunk.repo_id == Repo.id)
            )

            conditions = []
            if repo_ids:
                conditions.append(Chunk.repo_id.in_(repo_ids))
            if language:
                conditions.append(File.language == language)
            if path_prefix:
                conditions.append(File.path.startswith(path_prefix))
            if chunk_type:
                conditions.append(Chunk.chunk_type == chunk_type)

            if conditions:
                stmt = stmt.where(and_(*conditions))

            res = await self.db.execute(stmt)
            rows = res.all()

            scored = []
            for r in rows:
                if not r.embedding:
                    continue
                try:
                    if isinstance(r.embedding, str):
                        emb = json.loads(r.embedding)
                    elif isinstance(r.embedding, list):
                        emb = r.embedding
                    else:
                        continue
                    dist = _compute_cosine_distance(query_vec, emb)
                    scored.append((dist, r))
                except Exception:
                    continue

            scored.sort(key=lambda x: x[0])
            top_rows = scored[:limit]

            return [
                {
                    "chunk_id": str(r.id),
                    "repo_id": str(r.repo_id),
                    "repo_name": r.repo_name,
                    "file_path": r.file_path,
                    "start_line": r.start_line,
                    "end_line": r.end_line,
                    "chunk_type": r.chunk_type,
                    "symbol": r.symbol,
                    "text": r.text,
                }
                for dist, r in top_rows
            ]
        except Exception:
            return []

    async def _keyword_search(
        self,
        query: str,
        repo_ids: Optional[List[uuid.UUID]],
        language: Optional[str],
        path_prefix: Optional[str],
        chunk_type: Optional[str],
        limit: int = 30
    ) -> List[Dict[str, Any]]:
        # ILIKE / fulltext search
        search_terms = [f"%{term.strip()}%" for term in query.split() if len(term.strip()) > 1][:4]
        
        stmt = (
            select(
                Chunk.id,
                Chunk.repo_id,
                Repo.name.label("repo_name"),
                File.path.label("file_path"),
                Chunk.start_line,
                Chunk.end_line,
                Chunk.chunk_type,
                Chunk.symbol,
                Chunk.text
            )
            .join(File, Chunk.file_id == File.id)
            .join(Repo, Chunk.repo_id == Repo.id)
        )

        conditions = []
        if repo_ids:
            conditions.append(Chunk.repo_id.in_(repo_ids))
        if language:
            conditions.append(File.language == language)
        if path_prefix:
            conditions.append(File.path.startswith(path_prefix))
        if chunk_type:
            conditions.append(Chunk.chunk_type == chunk_type)

        if search_terms:
            text_conditions = [Chunk.text.ilike(t) for t in search_terms]
            conditions.append(or_(*text_conditions))

        if conditions:
            stmt = stmt.where(and_(*conditions))

        stmt = stmt.limit(limit)

        try:
            res = await self.db.execute(stmt)
            rows = res.all()
            return [
                {
                    "chunk_id": str(r.id),
                    "repo_id": str(r.repo_id),
                    "repo_name": r.repo_name,
                    "file_path": r.file_path,
                    "start_line": r.start_line,
                    "end_line": r.end_line,
                    "chunk_type": r.chunk_type,
                    "symbol": r.symbol,
                    "text": r.text,
                }
                for r in rows
            ]
        except Exception:
            return []
