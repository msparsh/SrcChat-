# Design Decisions & Assumptions

## 1. Stack & Architecture
- **Backend**: FastAPI with async SQLAlchemy 2.0 and asyncpg, communicating with PostgreSQL with `pgvector` extension.
- **Worker**: Background ingestion worker running via asyncio queue / background tasks or standalone process for ingestion jobs, ensuring non-blocking request handling.
- **Frontend**: Vite + React 18 + TypeScript + Tailwind CSS with Lucide icons for a sleek, Linear/Vercel-inspired dark/light developer aesthetic.
- **LLM / Embedding Provider Abstraction**: Configurable via `LLM_PROVIDER` (`openai`, `anthropic`, `gemini`, `ollama`, `dummy`) and `EMBEDDING_PROVIDER` (`openai`, `gemini`, `huggingface`, `dummy`).
- **llmtrack Adapter**: Provides a clean telemetry wrapper tracking tokens, cost, latency, retries, and errors, with an in-memory/database persistence fallback if `llmtrack` is not installed as an external package.
- **Parser & Structural Extraction**: Best-effort AST analysis using `tree-sitter` bindings where available, gracefully falling back to standard linguistic text chunking (`structure_level = "text_only"`).
- **Execution Guard**: Strict zero-code-execution policy: repositories are treated exclusively as untrusted text datasets. No subprocess code execution, no build tools, no package installation.
