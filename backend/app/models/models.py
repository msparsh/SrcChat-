import os
import datetime
import uuid
from sqlalchemy import (
    Column, String, Text, Integer, Float, Boolean, DateTime, ForeignKey, Index, JSON
)
from sqlalchemy.orm import declarative_base, relationship
from app.core.config import settings

_dev_sqlite = (
    os.environ.get("SRCCHAT_DEV_SQLITE", "").lower() in ("1", "true", "yes")
    or "sqlite" in settings.DATABASE_URL
    or os.path.exists("srcchat_dev.db")
    or os.path.exists("backend/srcchat_dev.db")
)

if _dev_sqlite:
    # SQLite-compatible types
    UUIDType = lambda: String(36)
    JsonType = JSON
    def make_uuid_col(fk=None, **kwargs):
        if fk:
            return Column(String(36), ForeignKey(fk, **{k: v for k, v in kwargs.items() if k in ('ondelete',)}), **{k: v for k, v in kwargs.items() if k not in ('ondelete',)})
        return Column(String(36), **kwargs)
    EmbeddingType = Text
else:
    try:
        from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB as PG_JSONB
        UUIDType = lambda: PG_UUID(as_uuid=True)
        JsonType = PG_JSONB
        EmbeddingType = None  # Will use Vector below
    except ImportError:
        UUIDType = lambda: String(36)
        JsonType = JSON
        EmbeddingType = Text

    try:
        from pgvector.sqlalchemy import Vector
        if EmbeddingType is None:
            EmbeddingType = None  # marker: use Vector
    except ImportError:
        if EmbeddingType is None:
            EmbeddingType = Text

def _embedding_col(dims):
    if EmbeddingType is None:
        return Column(Vector(dims), nullable=True)
    return Column(EmbeddingType, nullable=True)

def _uuid_default():
    if _dev_sqlite:
        return lambda: str(uuid.uuid4())
    return uuid.uuid4

def _uuid_col(primary_key=False, fk_str=None, ondelete=None, nullable=False, index=False):
    """Helper to create a UUID column consistently across SQLite and PostgreSQL."""
    col_type = UUIDType()
    kwargs = dict(primary_key=primary_key, nullable=nullable, index=index)
    if primary_key:
        kwargs["default"] = _uuid_default()
    if fk_str:
        fk = ForeignKey(fk_str, ondelete=ondelete) if ondelete else ForeignKey(fk_str)
        return Column(col_type, fk, **kwargs)
    return Column(col_type, **kwargs)

Base = declarative_base()


class Workspace(Base):
    __tablename__ = "workspaces"

    id = _uuid_col(primary_key=True)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    repos = relationship("Repo", back_populates="workspace", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="workspace", cascade="all, delete-orphan")


class Repo(Base):
    __tablename__ = "repos"

    id = _uuid_col(primary_key=True)
    workspace_id = _uuid_col(fk_str="workspaces.id", ondelete="CASCADE", index=True)
    url = Column(String(512), nullable=False)
    owner = Column(String(128), nullable=False)
    name = Column(String(128), nullable=False)
    branch = Column(String(128), default="main", nullable=False)
    commit_sha = Column(String(64), nullable=True)
    status = Column(String(32), default="queued", nullable=False)
    progress = Column(Float, default=0.0, nullable=False)
    status_message = Column(String(512), nullable=True)
    size_stats = Column(JsonType, default=dict)
    summary = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)

    workspace = relationship("Workspace", back_populates="repos")
    files = relationship("File", back_populates="repo", cascade="all, delete-orphan")
    chunks = relationship("Chunk", back_populates="repo", cascade="all, delete-orphan")
    symbols = relationship("Symbol", back_populates="repo", cascade="all, delete-orphan")
    edges = relationship("Edge", back_populates="repo", cascade="all, delete-orphan")


class File(Base):
    __tablename__ = "files"

    id = _uuid_col(primary_key=True)
    repo_id = _uuid_col(fk_str="repos.id", ondelete="CASCADE", index=True)
    path = Column(String(1024), nullable=False)
    language = Column(String(64), nullable=False, default="text")
    content_hash = Column(String(64), nullable=False)
    line_count = Column(Integer, default=0, nullable=False)
    structure_level = Column(String(32), default="tree_sitter", nullable=False)
    summary = Column(Text, nullable=True)
    raw_content = Column(Text, nullable=True)

    repo = relationship("Repo", back_populates="files")
    chunks = relationship("Chunk", back_populates="file", cascade="all, delete-orphan")
    symbols = relationship("Symbol", back_populates="file", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_files_repo_id_path", "repo_id", "path", unique=True),
    )


class Chunk(Base):
    __tablename__ = "chunks"

    id = _uuid_col(primary_key=True)
    repo_id = _uuid_col(fk_str="repos.id", ondelete="CASCADE", index=True)
    file_id = _uuid_col(fk_str="files.id", ondelete="CASCADE", index=True)
    chunk_type = Column(String(32), default="code", nullable=False)
    symbol = Column(String(256), nullable=True)
    start_line = Column(Integer, nullable=False)
    end_line = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    tsv = Column(Text, nullable=True)
    embedding = _embedding_col(settings.EMBEDDING_DIMENSIONS)

    repo = relationship("Repo", back_populates="chunks")
    file = relationship("File", back_populates="chunks")

    __table_args__ = (
        Index("ix_chunks_repo_chunktype", "repo_id", "chunk_type"),
    )


class Symbol(Base):
    __tablename__ = "symbols"

    id = _uuid_col(primary_key=True)
    repo_id = _uuid_col(fk_str="repos.id", ondelete="CASCADE", index=True)
    file_id = _uuid_col(fk_str="files.id", ondelete="CASCADE", index=True)
    name = Column(String(256), nullable=False, index=True)
    kind = Column(String(64), nullable=False)
    start_line = Column(Integer, nullable=False)
    end_line = Column(Integer, nullable=False)

    repo = relationship("Repo", back_populates="symbols")
    file = relationship("File", back_populates="symbols")


class Edge(Base):
    __tablename__ = "edges"

    id = _uuid_col(primary_key=True)
    repo_id = _uuid_col(fk_str="repos.id", ondelete="CASCADE", index=True)
    from_symbol = Column(String(256), nullable=False, index=True)
    to_symbol = Column(String(256), nullable=False, index=True)
    kind = Column(String(32), nullable=False)
    file_path = Column(String(1024), nullable=False)
    line_number = Column(Integer, nullable=True)

    repo = relationship("Repo", back_populates="edges")


class Conversation(Base):
    __tablename__ = "conversations"

    id = _uuid_col(primary_key=True)
    workspace_id = _uuid_col(fk_str="workspaces.id", ondelete="CASCADE", index=True)
    title = Column(String(256), default="New Chat", nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    workspace = relationship("Workspace", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id = _uuid_col(primary_key=True)
    conversation_id = _uuid_col(fk_str="conversations.id", ondelete="CASCADE", index=True)
    role = Column(String(32), nullable=False)
    content = Column(Text, nullable=False)
    tool_calls = Column(JsonType, default=list)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    conversation = relationship("Conversation", back_populates="messages")


class LLMCallLog(Base):
    __tablename__ = "llm_calls"

    id = _uuid_col(primary_key=True)
    call_type = Column(String(32), nullable=False)
    model = Column(String(128), nullable=False)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    cost_usd = Column(Float, default=0.0)
    latency_ms = Column(Float, default=0.0)
    retries = Column(Integer, default=0)
    error = Column(Text, nullable=True)
    extra_data = Column(JsonType, default=dict)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
