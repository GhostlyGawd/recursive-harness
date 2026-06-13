"""Anthropic instrumentation. Wraps ``client.messages.create`` so every call is
recorded with tokens, cost, latency and status."""
from __future__ import annotations

import time
from typing import Any


def record_anthropic_response(recorder, response: Any, messages: Any = None,
                              model: str = None, latency_ms: int = 0, provider: str = "anthropic"):
    model = model or _get(response, "model", "unknown")
    usage = _get(response, "usage", None)
    ti = _get(usage, "input_tokens", 0) or 0
    to = _get(usage, "output_tokens", 0) or 0
    text = _content_text(response)
    return recorder.model_call(provider, model, messages, text, tokens_in=ti, tokens_out=to, latency_ms=latency_ms)


def instrument_anthropic(client: Any, recorder, provider: str = "anthropic"):
    """Monkeypatch ``client.messages.create`` on a live Anthropic client."""
    original = client.messages.create

    def wrapped(*args, **kwargs):
        start = time.perf_counter()
        try:
            resp = original(*args, **kwargs)
        except Exception as exc:
            recorder.model_call(provider, kwargs.get("model", "unknown"), kwargs.get("messages"),
                                None, status="error", error=str(exc),
                                latency_ms=int((time.perf_counter() - start) * 1000))
            raise
        record_anthropic_response(recorder, resp, messages=kwargs.get("messages"),
                                  model=kwargs.get("model"),
                                  latency_ms=int((time.perf_counter() - start) * 1000), provider=provider)
        return resp

    client.messages.create = wrapped
    return client


def _get(obj, attr, default=None):
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(attr, default)
    return getattr(obj, attr, default)


def _content_text(response) -> str:
    try:
        content = _get(response, "content") or []
        if content and _get(content[0], "text") is not None:
            return _get(content[0], "text")
        return str(content)
    except Exception:
        return str(response)
