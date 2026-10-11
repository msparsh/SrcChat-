from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import httpx
from app.core.config import settings
from app.core.telemetry import tracker


class LLMAdapter(ABC):
    @abstractmethod
    async def generate(self, prompt: str, system_prompt: Optional[str] = None, max_tokens: int = 1500, temperature: float = 0.2) -> str:
        """Generate a single completion string."""
        pass

    @abstractmethod
    async def chat(self, messages: List[Dict[str, str]], max_tokens: int = 2000, temperature: float = 0.2) -> str:
        """Chat completion."""
        pass


class DummyLLMAdapter(LLMAdapter):
    """Fallback dummy adapter for testing, development, and offline mode without API keys."""

    async def generate(self, prompt: str, system_prompt: Optional[str] = None, max_tokens: int = 1500, temperature: float = 0.2) -> str:
        async def _call():
            import json
            p_lower = prompt.lower()
            if "json" in p_lower or "schema" in p_lower:
                if "flowstep" in p_lower or "flowexplanation" in p_lower:
                    payload = {
                        "flow_name": "Request Processing Lifecycle",
                        "overview": "Traces execution flow from entrypoint dispatch to response handler.",
                        "steps": [
                            {"step_number": 1, "file_path": "backend/app/main.py", "symbol_or_endpoint": "app", "description": "FastAPI initialization and middleware attachment."},
                            {"step_number": 2, "file_path": "backend/app/api/endpoints.py", "symbol_or_endpoint": "router", "description": "API route registration and handler resolution."}
                        ],
                        "caveats": "Flow mapped from static AST references."
                    }
                elif "impactanalysis" in p_lower or "impacteditem" in p_lower:
                    payload = {
                        "target": "target_symbol",
                        "suggested_change_order": ["backend/app/core/validator.py", "backend/app/api/endpoints.py"],
                        "impacted_items": [
                            {"file_path": "backend/app/api/endpoints.py", "symbol": "add_repo", "risk_level": "medium", "rationale": "Directly invokes the target function."}
                        ],
                        "static_analysis_caveat": "Static edge detection may miss dynamic reflections."
                    }
                elif "onboardingguide" in p_lower or "readingguideitem" in p_lower:
                    payload = {
                        "summary": "Onboarding walkthrough for indexed repository architecture.",
                        "where_to_start": [
                            {"order": 1, "file_path": "backend/app/main.py", "why_read": "Application entrypoint and dependency configuration."},
                            {"order": 2, "file_path": "backend/app/ingest/service.py", "why_read": "Core ingestion and chunking pipeline."}
                        ],
                        "key_concepts": ["Hybrid Retrieval", "AST Extraction", "Untrusted Data Boundaries"],
                        "development_workflow_notes": "Use SQLite dev mode for zero-setup local iteration."
                    }
                elif "repocomparison" in p_lower:
                    payload = {
                        "repo_a": "FastAPI",
                        "repo_b": "Gin",
                        "summary": "Comparative architectural overview of framework design.",
                        "aspects": [
                            {"topic": "Routing", "repo_a_approach": "Decorator and APIRouter based", "repo_b_approach": "Radix tree RouterGroup", "tradeoffs": "FastAPI optimizes developer DX and typing; Gin maximizes raw throughput."}
                        ]
                    }
                else:
                    payload = {
                        "system_overview": "SrcChat Codebase Intelligence Architecture",
                        "entry_points": ["backend/app/main.py"],
                        "components": [
                            {"name": "Ingestion Engine", "responsibilities": "Cloning, secret masking, AST parsing, and chunking", "key_files": ["backend/app/ingest/service.py"]},
                            {"name": "Hybrid Retriever", "responsibilities": "Vector search and full-text RRF fusion", "key_files": ["backend/app/retrieval/retriever.py"]}
                        ],
                        "data_stores": ["PostgreSQL + pgvector / SQLite fallback"],
                        "external_dependencies": ["FastAPI", "SQLAlchemy"]
                    }
                return {
                    "text": json.dumps(payload),
                    "usage": {"prompt_tokens": len(prompt) // 4, "completion_tokens": 80}
                }

            return {
                "text": f"Grounded architectural synthesis for: {prompt[:80]}",
                "usage": {"prompt_tokens": len(prompt) // 4, "completion_tokens": 50}
            }
        tracked = await tracker.track_async(_call, call_type="llm", model="dummy-llm")
        return tracked.response["text"]

    async def chat(self, messages: List[Dict[str, str]], max_tokens: int = 2000, temperature: float = 0.2) -> str:
        async def _call():
            last_msg = messages[-1]["content"] if messages else ""

            # Extract query and context if present
            query_line = "Codebase Query"
            if "User Question:" in last_msg:
                try:
                    query_line = last_msg.split("User Question:")[1].split(
                        "Target Repositories:")[0].strip()
                except Exception:
                    pass

            # Extract retrieved snippets and code blocks
            code_sections = []
            if "File: " in last_msg:
                parts = last_msg.split("File: ")
                for p in parts[1:5]:
                    file_header = p.split("\n")[0].strip()
                    code_block = ""
                    if "```" in p:
                        try:
                            code_block = p.split("```")[1].strip()
                        except Exception:
                            pass
                    code_sections.append((file_header, code_block))

            sections_md = []
            for hdr, blk in code_sections:
                entry = f"- **`{hdr}`**"
                if blk:
                    snippet_lines = blk.splitlines()[:6]
                    entry += "\n  ```\n  " + "\n  ".join(snippet_lines) + "\n  ```"
                sections_md.append(entry)

            snippets_md = "\n".join(sections_md) if sections_md else "- Index static call edges and symbols resolved."

            response_markdown = f"""### Codebase Investigation for: *"{query_line}"*

**Analysis & Grounded Code References:**
Based on structural symbol resolution and indexed code chunks, the relevant definitions are:

{snippets_md}

**Key Architecture Findings:**
- Identified relevant symbols and entrypoints matching query across indexed scope.
- References are grounded strictly in indexed files with verified line ranges.
"""
            return {
                "text": response_markdown,
                "usage": {"prompt_tokens": sum(len(m["content"]) for m in messages) // 4, "completion_tokens": 120}
            }
        tracked = await tracker.track_async(_call, call_type="llm", model="dummy-llm")
        return tracked.response["text"]


class OpenAILLMAdapter(LLMAdapter):
    def __init__(self, api_key: str, model: str = "gpt-4o-mini", base_url: Optional[str] = None):
        self.api_key = api_key or settings.LLM_API_KEY
        self.model = model or settings.LLM_MODEL
        self.base_url = base_url or settings.LLM_BASE_URL or "https://api.openai.com/v1"

    async def chat(self, messages: List[Dict[str, str]], max_tokens: int = 2000, temperature: float = 0.2) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }

        async def _call():
            async with httpx.AsyncClient(timeout=60.0) as client:
                res = await client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
                res.raise_for_status()
                data = res.json()
                return data

        tracked = await tracker.track_async(_call, call_type="llm", model=self.model)
        content = tracked.response["choices"][0]["message"]["content"]
        return content

    async def generate(self, prompt: str, system_prompt: Optional[str] = None, max_tokens: int = 1500, temperature: float = 0.2) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return await self.chat(messages, max_tokens=max_tokens, temperature=temperature)


class AnthropicLLMAdapter(LLMAdapter):
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    async def chat(self, messages: List[Dict[str, str]], max_tokens: int = 2000, temperature: float = 0.2) -> str:
        system = "\n\n".join(m["content"]
                             for m in messages if m["role"] == "system")
        conversation = [m for m in messages if m["role"] != "system"]
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": conversation,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if system:
            payload["system"] = system

        async def _call():
            async with httpx.AsyncClient(timeout=60.0) as client:
                res = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": self.api_key,
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                res.raise_for_status()
                return res.json()

        tracked = await tracker.track_async(_call, call_type="llm", model=self.model)
        return "".join(block.get("text", "") for block in tracked.response.get("content", []))

    async def generate(self, prompt: str, system_prompt: Optional[str] = None, max_tokens: int = 1500, temperature: float = 0.2) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return await self.chat(messages, max_tokens=max_tokens, temperature=temperature)


class GeminiLLMAdapter(LLMAdapter):
    def __init__(self, api_key: str, model: str, base_url: Optional[str] = None):
        self.api_key = api_key
        self.model = model
        self.base_url = (
            base_url or "https://generativelanguage.googleapis.com/v1beta").rstrip("/")

    async def chat(self, messages: List[Dict[str, str]], max_tokens: int = 2000, temperature: float = 0.2) -> str:
        system_parts = [m["content"]
                        for m in messages if m["role"] == "system"]
        contents = [
            {
                "role": "model" if message["role"] == "assistant" else "user",
                "parts": [{"text": message["content"]}],
            }
            for message in messages
            if message["role"] != "system"
        ]
        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {"maxOutputTokens": max_tokens, "temperature": temperature},
        }
        if system_parts:
            payload["systemInstruction"] = {
                "parts": [{"text": "\n\n".join(system_parts)}]}

        async def _call():
            async with httpx.AsyncClient(timeout=60.0) as client:
                res = await client.post(
                    f"{self.base_url}/models/{self.model}:generateContent",
                    headers={"x-goog-api-key": self.api_key,
                             "Content-Type": "application/json"},
                    json=payload,
                )
                res.raise_for_status()
                return res.json()

        tracked = await tracker.track_async(_call, call_type="llm", model=self.model)
        candidates = tracked.response.get("candidates", [])
        if not candidates:
            raise ValueError("Gemini returned no response candidates.")
        return "".join(part.get("text", "") for part in candidates[0].get("content", {}).get("parts", []))

    async def generate(self, prompt: str, system_prompt: Optional[str] = None, max_tokens: int = 1500, temperature: float = 0.2) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return await self.chat(messages, max_tokens=max_tokens, temperature=temperature)


def get_llm_adapter() -> LLMAdapter:
    provider = settings.LLM_PROVIDER
    if provider == "dummy":
        return DummyLLMAdapter()

    if provider == "ollama":
        base_url = settings.LLM_BASE_URL or "http://localhost:11434/v1"
        return OpenAILLMAdapter(api_key="ollama", model=settings.LLM_MODEL or "llama3.2", base_url=base_url)

    if not settings.LLM_API_KEY:
        raise ValueError(
            f"LLM_API_KEY is required when LLM_PROVIDER is '{provider}'.")
    if provider == "anthropic":
        return AnthropicLLMAdapter(api_key=settings.LLM_API_KEY, model=settings.LLM_MODEL)
    if provider == "gemini":
        return GeminiLLMAdapter(api_key=settings.LLM_API_KEY, model=settings.LLM_MODEL, base_url=settings.LLM_BASE_URL or None)
    return OpenAILLMAdapter(
        api_key=settings.LLM_API_KEY,
        model=settings.LLM_MODEL,
        base_url=settings.LLM_BASE_URL or None,
    )
