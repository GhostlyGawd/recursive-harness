"""LangChain / LangGraph integration via a callback handler.

Drop ``AgentOpsCallbackHandler(recorder)`` into ``callbacks=[...]`` and every LLM
call and tool invocation in the chain/graph is recorded. Works whether or not
``langchain_core`` is installed — if it is, we subclass the real base handler so
LangChain recognises it; if not, this is a plain duck-typed handler.
"""
from __future__ import annotations

from typing import Any

try:  # pragma: no cover - exercised only when langchain is installed
    from langchain_core.callbacks import BaseCallbackHandler as _Base
except Exception:  # noqa: BLE001
    try:  # pragma: no cover
        from langchain.callbacks.base import BaseCallbackHandler as _Base
    except Exception:  # noqa: BLE001
        class _Base:  # minimal stand-in
            pass


class AgentOpsCallbackHandler(_Base):
    def __init__(self, recorder, provider: str = "langchain"):
        super().__init__()
        self.rec = recorder
        self.provider = provider
        self._prompts: Any = None
        self._tool_name = "tool"
        self._tool_input: Any = None

    # ---- LLM ----
    def on_llm_start(self, serialized, prompts, **kwargs):
        self._prompts = prompts

    def on_chat_model_start(self, serialized, messages, **kwargs):
        self._prompts = messages

    def on_llm_end(self, response, **kwargs):
        text, model, ti, to = "", "unknown", 0, 0
        try:
            gen = response.generations[0][0]
            text = getattr(gen, "text", "") or getattr(getattr(gen, "message", None), "content", "")
        except Exception:  # noqa: BLE001
            pass
        out = getattr(response, "llm_output", None) or {}
        model = out.get("model_name", out.get("model", "unknown"))
        usage = out.get("token_usage", out.get("usage", {})) or {}
        ti = usage.get("prompt_tokens", usage.get("input_tokens", 0)) or 0
        to = usage.get("completion_tokens", usage.get("output_tokens", 0)) or 0
        self.rec.model_call(self.provider, model, self._prompts, text, tokens_in=ti, tokens_out=to)

    def on_llm_error(self, error, **kwargs):
        self.rec.model_call(self.provider, "unknown", self._prompts, None, status="error", error=str(error))

    # ---- tools ----
    def on_tool_start(self, serialized, input_str, **kwargs):
        self._tool_name = (serialized or {}).get("name", "tool")
        self._tool_input = input_str

    def on_tool_end(self, output, **kwargs):
        self.rec.tool_call(self._tool_name, input=self._tool_input, output=str(output))

    def on_tool_error(self, error, **kwargs):
        self.rec.tool_call(self._tool_name, input=self._tool_input, status="error", error=str(error))
