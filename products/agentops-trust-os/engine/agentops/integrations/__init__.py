"""Framework + provider integrations.

Each integration is best-effort and guarded: importing it never requires the
third-party library to be installed. The model-agnostic core means adding a
provider is just another thin wrapper that calls ``recorder.model_call`` /
``recorder.tool_call``.
"""
from .anthropic import instrument_anthropic, record_anthropic_response
from .langchain import AgentOpsCallbackHandler
from .openai import instrument_openai, record_openai_response
from .slack import approval_blocks, post_approval

__all__ = [
    "instrument_openai", "record_openai_response",
    "instrument_anthropic", "record_anthropic_response",
    "AgentOpsCallbackHandler", "approval_blocks", "post_approval",
]
