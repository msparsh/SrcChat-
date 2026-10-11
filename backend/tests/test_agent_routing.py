import asyncio
from unittest.mock import AsyncMock, Mock

import pytest

from app.agent.tools import AgentToolRegistry
from app.core.config import settings
from app.llm.llm_adapter import (
    AnthropicLLMAdapter,
    DummyLLMAdapter,
    GeminiLLMAdapter,
    OpenAILLMAdapter,
    get_llm_adapter,
)


@pytest.mark.parametrize(
    ("provider", "expected_type"),
    [
        ("dummy", DummyLLMAdapter),
        ("openai", OpenAILLMAdapter),
        ("anthropic", AnthropicLLMAdapter),
        ("gemini", GeminiLLMAdapter),
    ],
)
def test_llm_provider_selects_matching_adapter(monkeypatch, provider, expected_type):
    monkeypatch.setattr(settings, "LLM_PROVIDER", provider)
    monkeypatch.setattr(settings, "LLM_API_KEY", "test-key")

    assert isinstance(get_llm_adapter(), expected_type)


def test_configured_cloud_provider_requires_api_key(monkeypatch):
    monkeypatch.setattr(settings, "LLM_PROVIDER", "gemini")
    monkeypatch.setattr(settings, "LLM_API_KEY", "")

    with pytest.raises(ValueError, match="LLM_API_KEY is required"):
        get_llm_adapter()


def test_search_for_unknown_repo_does_not_search_all_repositories():
    db = Mock()
    result = Mock()
    result.all.return_value = []
    db.execute = AsyncMock(return_value=result)
    tools = AgentToolRegistry(db)
    tools.retriever.search = AsyncMock()

    results = asyncio.run(tools.semantic_search(
        "find the handler", repos=["missing-repo"]))

    assert results == []
    tools.retriever.search.assert_not_awaited()
