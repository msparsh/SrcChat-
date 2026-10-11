from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # General
    APP_NAME: str = "SrcChat"
    DEBUG: bool = False
    API_V1_STR: str = "/api/v1"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/srcchat"
    DATABASE_URL_SYNC: str = "postgresql://postgres:postgres@localhost:5432/srcchat"

    # Ingestion Limits
    MAX_REPO_SIZE_MB: int = 100
    MAX_REPO_FILES: int = 3000
    MAX_INDEXED_LOC: int = 200000
    MAX_FILE_SIZE_KB: int = 300
    MAX_REPOS_PER_WORKSPACE: int = 10
    MAX_CONCURRENT_INDEXING_JOBS: int = 2
    CLONE_TIMEOUT_SECONDS: int = 120

    # LLM & Embedding Adapter Configuration
    LLM_PROVIDER: Literal["openai", "anthropic", "gemini", "ollama", "dummy"] = "dummy"
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = ""

    EMBEDDING_PROVIDER: Literal["openai", "gemini", "dummy"] = "dummy"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_API_KEY: str = ""
    EMBEDDING_BASE_URL: str = ""
    EMBEDDING_DIMENSIONS: int = 1536
    EMBEDDING_BATCH_SIZE: int = 64

    # Search & Retrieval
    ENABLE_RERANK: bool = False
    RETRIEVAL_TOP_K: int = 15
    RRF_K: int = 60

    # Agent Limits
    AGENT_MAX_STEPS: int = 8
    AGENT_TOKEN_BUDGET: int = 16000


settings = Settings()
