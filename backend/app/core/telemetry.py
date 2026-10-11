import time
import logging
from typing import Any, Dict, Optional, Callable, Awaitable
from dataclasses import dataclass, field

logger = logging.getLogger("llmtrack")

# In-memory store for tracking telemetry when external llmtrack library is not installed
_TELEMETRY_LOGS = []

@dataclass
class TrackedCallResult:
    response: Any
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    retries: int = 0
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class LLMTrackAdapter:
    """
    Adapter mirroring the llmtrack interface.
    Tracks tokens, cost estimates, latency, retries, and errors.
    TODO: If 'llmtrack' package is installed in environment, delegate to `import llmtrack`.
    """

    def __init__(self, pricing_per_1k_tokens: Optional[Dict[str, float]] = None):
        # Pricing approximations per 1K tokens: (prompt_rate, completion_rate)
        self.pricing = pricing_per_1k_tokens or {
            "gpt-4o-mini": (0.00015, 0.0006),
            "gpt-4o": (0.005, 0.015),
            "text-embedding-3-small": (0.00002, 0.0),
            "default": (0.001, 0.002)
        }

    def calculate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        rates = self.pricing.get(model, self.pricing["default"])
        prompt_cost = (prompt_tokens / 1000.0) * rates[0]
        comp_cost = (completion_tokens / 1000.0) * rates[1]
        return round(prompt_cost + comp_cost, 6)

    async def track_async(
        self,
        call_fn: Callable[[], Awaitable[Any]],
        call_type: str = "llm",
        model: str = "default",
        max_retries: int = 2,
        metadata: Optional[Dict[str, Any]] = None
    ) -> TrackedCallResult:
        start_time = time.perf_counter()
        retries = 0
        error_msg = None
        response = None

        for attempt in range(max_retries + 1):
            try:
                response = await call_fn()
                break
            except Exception as e:
                retries = attempt
                error_msg = str(e)
                if attempt == max_retries:
                    latency_ms = (time.perf_counter() - start_time) * 1000
                    record = TrackedCallResult(
                        response=None,
                        latency_ms=latency_ms,
                        retries=retries,
                        error=error_msg,
                        metadata=metadata or {}
                    )
                    self._record(call_type, model, record)
                    raise e
                time.sleep(0.5 * (2 ** attempt))

        latency_ms = (time.perf_counter() - start_time) * 1000
        
        # Token extraction heuristics
        prompt_tokens = getattr(response, "prompt_tokens", 0) if response else 0
        completion_tokens = getattr(response, "completion_tokens", 0) if response else 0
        if isinstance(response, dict):
            prompt_tokens = response.get("usage", {}).get("prompt_tokens", 0)
            completion_tokens = response.get("usage", {}).get("completion_tokens", 0)

        total_tokens = prompt_tokens + completion_tokens
        cost = self.calculate_cost(model, prompt_tokens, completion_tokens)

        result = TrackedCallResult(
            response=response,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost_usd=cost,
            latency_ms=latency_ms,
            retries=retries,
            error=error_msg,
            metadata=metadata or {}
        )
        self._record(call_type, model, result)
        return result

    def _record(self, call_type: str, model: str, result: TrackedCallResult):
        record_dict = {
            "timestamp": time.time(),
            "call_type": call_type,
            "model": model,
            "prompt_tokens": result.prompt_tokens,
            "completion_tokens": result.completion_tokens,
            "total_tokens": result.total_tokens,
            "cost_usd": result.cost_usd,
            "latency_ms": result.latency_ms,
            "retries": result.retries,
            "error": result.error,
            "metadata": result.metadata
        }
        _TELEMETRY_LOGS.append(record_dict)
        logger.info(f"[{call_type.upper()}] model={model} tokens={result.total_tokens} cost=${result.cost_usd:.6f} latency={result.latency_ms:.1f}ms")

    @classmethod
    def get_logs(cls):
        return list(_TELEMETRY_LOGS)

    @classmethod
    def get_aggregated_stats(cls):
        total_tokens = sum(r["total_tokens"] for r in _TELEMETRY_LOGS)
        total_cost = sum(r["cost_usd"] for r in _TELEMETRY_LOGS)
        avg_latency = (
            sum(r["latency_ms"] for r in _TELEMETRY_LOGS) / len(_TELEMETRY_LOGS)
            if _TELEMETRY_LOGS else 0.0
        )
        by_model = {}
        for r in _TELEMETRY_LOGS:
            m = r["model"]
            if m not in by_model:
                by_model[m] = {"calls": 0, "tokens": 0, "cost": 0.0, "latency_sum": 0.0}
            by_model[m]["calls"] += 1
            by_model[m]["tokens"] += r["total_tokens"]
            by_model[m]["cost"] += r["cost_usd"]
            by_model[m]["latency_sum"] += r["latency_ms"]
        
        return {
            "total_calls": len(_TELEMETRY_LOGS),
            "total_tokens": total_tokens,
            "total_cost_usd": round(total_cost, 6),
            "avg_latency_ms": round(avg_latency, 2),
            "by_model": by_model,
            "recent_calls": _TELEMETRY_LOGS[-50:]
        }

tracker = LLMTrackAdapter()
