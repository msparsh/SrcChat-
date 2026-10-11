from abc import ABC, abstractmethod
from typing import List
import hashlib
import httpx
from app.core.config import settings
from app.core.telemetry import tracker


class EmbeddingAdapter(ABC):
    @abstractmethod
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Embed a batch of text chunks."""
        pass


class DummyEmbeddingAdapter(EmbeddingAdapter):
    """Deterministic pseudo-embeddings for testing, CI, and local dev without API keys."""
    def __init__(self, dimensions: int = 1536):
        self.dimensions = dimensions

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        async def _call():
            embeddings = []
            for text in texts:
                # Deterministic pseudo-vector from text hash
                h = hashlib.sha256(text.encode("utf-8")).digest()
                vector = []
                for i in range(self.dimensions):
                    byte_val = h[i % len(h)]
                    # Normalize around [-1.0, 1.0]
                    norm_val = ((byte_val / 255.0) * 2.0) - 1.0
                    vector.append(norm_val)
                embeddings.append(vector)
            return {
                "embeddings": embeddings,
                "usage": {"prompt_tokens": sum(len(t) // 4 for t in texts), "completion_tokens": 0}
            }

        tracked = await tracker.track_async(_call, call_type="embedding", model="dummy-embed")
        return tracked.response["embeddings"]


class OpenAIEmbeddingAdapter(EmbeddingAdapter):
    def __init__(self, api_key: str, model: str = "text-embedding-3-small", base_url: str = None):
        self.api_key = api_key or settings.EMBEDDING_API_KEY
        self.model = model or settings.EMBEDDING_MODEL
        self.base_url = base_url or settings.EMBEDDING_BASE_URL or "https://api.openai.com/v1"

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "input": texts
        }

        async def _call():
            async with httpx.AsyncClient(timeout=60.0) as client:
                res = await client.post(f"{self.base_url}/embeddings", headers=headers, json=payload)
                res.raise_for_status()
                return res.json()

        tracked = await tracker.track_async(_call, call_type="embedding", model=self.model)
        data = tracked.response.get("data", [])
        return [item["embedding"] for item in data]


def get_embedding_adapter() -> EmbeddingAdapter:
    if settings.EMBEDDING_PROVIDER == "openai" and settings.EMBEDDING_API_KEY:
        return OpenAIEmbeddingAdapter(api_key=settings.EMBEDDING_API_KEY, model=settings.EMBEDDING_MODEL)
    return DummyEmbeddingAdapter(dimensions=settings.EMBEDDING_DIMENSIONS)
