import json
import uuid
import os
import asyncio
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.models import Workspace, Repo, Conversation, Message, File
from app.core.validator import validate_and_normalize_github_url
from app.core.config import settings
from app.core.telemetry import tracker
from app.ingest.service import IngestionService
from app.agent.agent import AgentLoop

router = APIRouter()

_DEV_SQLITE = os.environ.get("SRCCHAT_DEV_SQLITE", "").lower() in ("1", "true", "yes")

def _id(val) -> str:
    """Always coerce UUID-like values to string for SQLite compatibility."""
    return str(val)

# Global semaphore limiting concurrent ingestion jobs
indexing_semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_INDEXING_JOBS)


# ─── Pydantic Request Schemas ────────────────────────────────────────────────

class WorkspaceCreate(BaseModel):
    name: str = "Default Workspace"

class AddRepoRequest(BaseModel):
    workspace_id: str  # Accept as str to avoid UUID binding issues
    url: str
    branch: Optional[str] = "main"

class ChatRequest(BaseModel):
    conversation_id: Optional[str] = None
    workspace_id: str
    query: str
    repos: List[str] = []
    output_mode: Optional[str] = None

class StructuredActionRequest(BaseModel):
    mode: str
    query: str
    repos: List[str]


# ─── Workspaces ──────────────────────────────────────────────────────────────

@router.get("/workspaces")
async def list_workspaces(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Workspace))
    workspaces = res.scalars().all()
    if not workspaces:
        ws = Workspace(name="Main Workspace")
        db.add(ws)
        await db.commit()
        await db.refresh(ws)
        return [ws]
    return workspaces

@router.post("/workspaces")
async def create_workspace(body: WorkspaceCreate, db: AsyncSession = Depends(get_db)):
    ws = Workspace(name=body.name)
    db.add(ws)
    await db.commit()
    await db.refresh(ws)
    return ws


# ─── Repositories ────────────────────────────────────────────────────────────

@router.get("/workspaces/{workspace_id}/repos")
async def list_repos(workspace_id: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(
        select(Repo).where(Repo.workspace_id == workspace_id).order_by(Repo.created_at.desc())
    )
    return res.scalars().all()

@router.get("/repos/{repo_id}/tree")
async def get_repo_tree(repo_id: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(File).where(File.repo_id == repo_id).order_by(File.path))
    files = res.scalars().all()
    return [
        {"id": str(f.id), "path": f.path, "language": f.language, "lines": f.line_count, "summary": f.summary}
        for f in files
    ]

async def _run_indexing_background(repo_id: str, incremental: bool = False):
    from app.db.session import AsyncSessionLocal
    async with indexing_semaphore:
        async with AsyncSessionLocal() as session:
            repo = await session.get(Repo, repo_id)
            if not repo:
                return
            service = IngestionService(session)
            try:
                await service.index_repository(repo, incremental=incremental)
            except Exception:
                pass  # Errors are logged and persisted inside IngestionService

@router.post("/repos")
async def add_repo(body: AddRepoRequest, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    # Enforce workspace repo count limit
    count_res = await db.execute(select(Repo).where(Repo.workspace_id == body.workspace_id))
    existing_repos = count_res.scalars().all()
    if len(existing_repos) >= settings.MAX_REPOS_PER_WORKSPACE:
        raise HTTPException(
            status_code=400,
            detail=f"Workspace repository limit reached ({settings.MAX_REPOS_PER_WORKSPACE} max). Remove an existing repo first."
        )

    # Validate GitHub URL (SSRF protection)
    try:
        norm_url, owner, name = validate_and_normalize_github_url(body.url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Reject duplicate repos in this workspace
    for r in existing_repos:
        if r.owner.lower() == owner.lower() and r.name.lower() == name.lower():
            raise HTTPException(status_code=400, detail=f"Repository '{owner}/{name}' is already in this workspace.")

    repo = Repo(
        workspace_id=body.workspace_id,
        url=norm_url,
        owner=owner,
        name=name,
        branch=body.branch or "main",
        status="queued",
        progress=0.0,
        status_message="Queued for indexing worker..."
    )
    db.add(repo)
    await db.commit()
    await db.refresh(repo)

    background_tasks.add_task(_run_indexing_background, str(repo.id))
    return repo

@router.post("/repos/{repo_id}/sync")
async def resync_repo(repo_id: str, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    repo = await db.get(Repo, repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repo not found")
    repo.status = "queued"
    repo.progress = 0.0
    repo.status_message = "Re-sync queued..."
    await db.commit()
    background_tasks.add_task(_run_indexing_background, repo_id, True)
    return {"message": "Incremental re-sync triggered."}

@router.delete("/repos/{repo_id}")
async def delete_repo(repo_id: str, db: AsyncSession = Depends(get_db)):
    repo = await db.get(Repo, repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repo not found")
    await db.delete(repo)
    await db.commit()
    return {"message": "Repository and all associated index data removed."}


# ─── Agent Chat (SSE Streaming) ──────────────────────────────────────────────

@router.post("/chat/stream")
async def chat_stream(body: ChatRequest, db: AsyncSession = Depends(get_db)):
    loop = AgentLoop(db)

    async def event_generator():
        try:
            async for event in loop.run_stream(body.query, body.repos, body.output_mode):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ─── Structured Quick Actions ─────────────────────────────────────────────────

@router.post("/actions/structured")
async def structured_action(body: StructuredActionRequest, db: AsyncSession = Depends(get_db)):
    loop = AgentLoop(db)
    result = await loop.generate_structured_output(body.mode, body.query, body.repos)
    return result


# ─── Telemetry & System Info ──────────────────────────────────────────────────

@router.get("/usage/telemetry")
async def get_usage_telemetry():
    return tracker.get_aggregated_stats()

@router.get("/info/limits")
async def get_system_limits():
    return {
        "max_repo_size_mb": settings.MAX_REPO_SIZE_MB,
        "max_repo_files": settings.MAX_REPO_FILES,
        "max_indexed_loc": settings.MAX_INDEXED_LOC,
        "max_file_size_kb": settings.MAX_FILE_SIZE_KB,
        "max_repos_per_workspace": settings.MAX_REPOS_PER_WORKSPACE,
        "max_concurrent_jobs": settings.MAX_CONCURRENT_INDEXING_JOBS
    }
