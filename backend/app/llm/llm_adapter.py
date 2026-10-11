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
    """Fallback dummy adapter for testing, development, and offline mode."""
    async def generate(self, prompt: str, system_prompt: Optional[str] = None, max_tokens: int = 1500, temperature: float = 0.2) -> str:
        async def _call():
            return {
                "text": f"[Dummy Summary/Response for prompt length {len(prompt)}]",
                "usage": {"prompt_tokens": len(prompt) // 4, "completion_tokens": 50}
            }
        tracked = await tracker.track_async(_call, call_type="llm", model="dummy-llm")
        return tracked.response["text"]

    async def chat(self, messages: List[Dict[str, str]], max_tokens: int = 2000, temperature: float = 0.2) -> str:
        async def _call():
            last_msg = messages[-1]["content"] if messages else ""
            return {
                "text": f"Here is the synthesized analysis of the repository:\n\n- Analyzed query: `{last_msg[:80]}`\n- Codebase static analysis confirms entry points and dependencies.\n- Please see the retrieved files and symbols for details.",
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


def get_llm_adapter() -> LLMAdapter:
    if settings.LLM_PROVIDER == "openai" and settings.LLM_API_KEY:
        return OpenAILLMAdapter(api_key=settings.LLM_API_KEY, model=settings.LLM_MODEL)
    return DummyLLMAdapter()
