import os, time
import litellm
from litellm import Cache

MODEL = os.getenv("LLM_MODEL", "gemini/gemini-2.0-flash")
KEYS = [k.strip() for k in os.getenv("LLM_API_KEYS", "").split(",") if k.strip()]

# LiteLLM's built-in local cache. Cache identity is based on model + request messages.
litellm.cache = Cache(type="local")
litellm.telemetry = False

class ProvidersUnavailable(Exception):
    pass

def _simulated_failures(header):
    failures = {}
    if not header:
        return failures
    for item in header.split(","):
        if "=" not in item:
            continue
        key_id, status = item.strip().split("=", 1)
        if status.strip() in {"429", "500", "502", "503"}:
            failures[key_id.strip()] = int(status.strip())
    return failures

def generate(messages, failure_header=None):
    if len(KEYS) < 2:
        raise RuntimeError("Configure at least two LLM_API_KEYS")
    failures = _simulated_failures(failure_header) if os.getenv("ENABLE_FAILURE_SIMULATION", "false").lower() == "true" else {}
    attempted = 0
    last_error = None
    for index, api_key in enumerate(KEYS):
        key_id = f"key_{index + 1}"
        if "*" in failures or key_id in failures:
            attempted += 1
            last_error = f"Simulated provider failure: {failures.get(key_id, failures.get('*'))}"
            continue
        started = time.perf_counter()
        try:
            response = litellm.completion(
                model=MODEL,
                messages=messages,
                api_key=api_key,
                caching=True,
                timeout=35,
            )
            latency_ms = int((time.perf_counter() - started) * 1000)
            usage = getattr(response, "usage", None)
            hidden = getattr(response, "_hidden_params", {}) or {}
            cache_hit = bool(hidden.get("cache_hit", False))
            # LiteLLM versions may expose cache status through response metadata.
            if not cache_hit:
                cache_hit = bool(hidden.get("cache_key") and hidden.get("cache_hit"))
            return {
                "reply": response.choices[0].message.content or "",
                "model": getattr(response, "model", MODEL) or MODEL,
                "latency_ms": latency_ms,
                "input_tokens": int(getattr(usage, "prompt_tokens", 0) or 0),
                "output_tokens": int(getattr(usage, "completion_tokens", 0) or 0),
                "key_id": None if cache_hit else key_id,
                "fallback_attempts": 0 if cache_hit else attempted,
                "resolution_source": "LLM_CACHE" if cache_hit else "LIVE_INFERENCE",
            }
        except Exception as exc:
            last_error = exc
            attempted += 1
            # Continue on rate limit, quota, provider/server errors and transient failures.
            continue
    raise ProvidersUnavailable("all providers unavailable") from last_error
