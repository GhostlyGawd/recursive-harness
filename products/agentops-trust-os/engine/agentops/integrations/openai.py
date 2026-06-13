"""OpenAI instrumentation. Wraps ``client.chat.completions.create`` so every call
is recorded with tokens, cost, latency and status — no change to call sites."""
from __future__ import annotations

import time
from typing import Any


def record_openai_response(recorder, response: Any, messages: Any = None,
                           model: str = None, latency_ms: int = 0, provider: str = "openai"):
    """Record an already-obtained OpenAI response object (or dict)."""
    model = model or _get(response, "model", "unknown")
    usage = _get(response, "usage", None)
    ti = _get(usage, "prompt_tokens", 0) or _get(usage, "input_tokens", 0) or 0
    to = _get(usage, "completion_tokens", 0) or _get(usage, "output_tokens", 0) or 0
    text = _first_choice_text(response)
    return recorder.model_call(provider, model, messages, text, tokens_in=ti, tokens_out=to, latency_ms=latency_ms)


def instrument_openai(client: Any, recorder, provider: str = "openai"):
    """Monkeypatch ``client.chat.completions.create`` on a live OpenAI client."""
    original = client.chat.completions.create

    def wrapped(*args, **kwargs):
        start = time.perf_counter()
        try:
            resp = original(*args, **kwargs)
        except Exception as exc:  # record the failure too
            recorder.model_call(provider, kwargs.get("model", "unknown"), kwargs.get("messages"),
                                None, status="error", error=str(exc),
                                latency_ms=int((time.perf_counter() - start) * 1000))
            raise
        record_openai_response(recorder, resp, messages=kwargs.get("messages"),
                               model=kwargs.get("model"),
                               latency_ms=int((time.perf_counter() - start) * 1000), provider=provider)
        return resp

    client.chat.completions.create = wrapped
    return client


def _get(obj, attr, default=None):
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(attr, default)
    return getattr(obj, attr, default)


def _first_choice_text(response) -> str:
    try:
        choices = _get(response, "choices") or []
        msg = _get(choices[0], "message")
        return _get(msg, "content", "") or ""
    except Exception:
        return str(response)
