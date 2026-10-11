# SrcChat

A modern codebase assistant for understanding public GitHub repositories through semantic search, static structure analysis, and agentic reasoning.

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white" />
  <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-0.115%2B-009688?logo=fastapi&logoColor=white" />
  <img alt="React" src="https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=white" />
  <img alt="PostgreSQL" src="https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white" />
</p>

SrcChat helps you add public repositories, index them safely, and ask meaningful questions about architecture, dependencies, data flow, and change impact without running the codebase itself.

## Why teams use it

- Explore multiple repositories from a single workspace
- Ask architecture and onboarding questions grounded in real code
- Trace request flow and system boundaries across files and repos
- Combine vector retrieval with AST-aware repository metadata
- Keep sensitive content isolated in a safe, read-only indexing workflow

## Features

- Multi-repo workspace management with scope filtering
- GitHub repository ingestion with validation and safety limits
- Code understanding via semantic search, repo metadata, and symbol structure
- Agent-driven answers for flow tracing, impact analysis, and architecture summaries
- Web UI with quick actions, repo explorer, telemetry, and structured output cards

## Screenshots

### Workspace overview

![SrcChat workspace overview](docs/screenshots/workspace-overview.png)

### Add repository flow

![Add repository dialog](docs/screenshots/add-repository.png)

## What it solves

SrcChat is built for code understanding at scale. You can index a repository, narrow the search to specific repos, and ask questions like:

- Where does the request lifecycle begin and end?
- Which modules are most tightly coupled to this change?
- What should a new engineer read first?
- What would be affected if this API contract changes?

The app reads repository content in a controlled way, extracts structure and metadata, stores embeddings, and uses an agent to synthesize answers grounded in the indexed code.

## Tech stack

- Backend: Python, FastAPI, SQLAlchemy, PostgreSQL + pgvector
- Frontend: React, TypeScript, Vite, Tailwind CSS
- Retrieval: semantic search, static metadata, hybrid reasoning
- Infrastructure: Docker and Docker Compose

## Quick start

### 1) Configure environment

```bash
cp .env.example .env
```

Update the values for your selected LLM and embedding provider. The default configuration is suitable for local smoke testing.

### 2) Run the stack

```bash
docker compose up --build
```

Then open:

- Frontend: http://localhost:5173
- API docs: http://localhost:8000/docs
- PostgreSQL: localhost:5432

## Local development

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Project structure

```text
.
├── .env.example
├── docker-compose.yml
├── LICENSE
├── README.md
├── backend/
│   ├── app/
│   │   ├── agent/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── ingest/
│   │   ├── llm/
│   │   ├── models/
│   │   ├── retrieval/
│   │   └── schemas/
│   ├── tests/
│   └── requirements.txt
├── docs/
│   ├── DECISIONS.md
│   └── screenshots/
│       ├── add-repository.png
│       ├── code-explorer.png
│       └── workspace-overview.png
├── frontend/
│   ├── src/
│   ├── package.json
│   ├── vite.config.ts
│   └── ...
└── .gitignore
```

## Safety model

SrcChat treats repository contents as untrusted input and keeps execution isolated.

- No live code execution or build/test runs against user repositories
- Strict validation of GitHub repository URLs
- Secret masking before indexing and embedding
- Guardrails for repo size, file count, and file size
- Concurrency limits for ingestion jobs

## Limits

| Metric | Value |
| :--- | :--- |
| Max repo size | 100 MB |
| Max files per repo | 3,000 |
| Max LOC per repo | 200,000 |
| Max file size | 300 KB |
| Max repos per workspace | 10 |
| Concurrent indexing jobs | 2 |

## Testing

```bash
cd backend
pytest -q tests/
```

## License

MIT. See [LICENSE](LICENSE) for details.
