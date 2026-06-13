"""Model cost accounting.

A small, model-agnostic price table maps (provider, model) -> per-1K-token USD
rates so the recorder can attach a cost to every model call. Prices are
approximate published list rates and are intentionally easy to override — the
point is that *every* model call carries a cost, not that the table is canonical.

Rates are USD per 1,000 tokens. Update via ``register_price`` or by editing
``PRICE_TABLE``. Unknown models fall back to ``DEFAULT_RATE`` so cost is never
silently zero.
"""
from __future__ import annotations

from typing import Optional, Tuple

# (input_per_1k, output_per_1k) in USD. Approximate list prices (early 2026); validate before billing.
PRICE_TABLE: dict = {
    # Anthropic
    ("anthropic", "claude-opus-4"): (0.015, 0.075),
    ("anthropic", "claude-sonnet-4"): (0.003, 0.015),
    ("anthropic", "claude-haiku-4"): (0.0008, 0.004),
    ("anthropic", "claude-3-5-sonnet"): (0.003, 0.015),
    # OpenAI
    ("openai", "gpt-4o"): (0.005, 0.015),
    ("openai", "gpt-4o-mini"): (0.00015, 0.0006),
    ("openai", "gpt-4.1"): (0.002, 0.008),
    ("openai", "o3"): (0.01, 0.04),
    # Google
    ("google", "gemini-2.5-pro"): (0.00125, 0.005),
    ("google", "gemini-2.5-flash"): (0.0003, 0.0025),
    # Mock provider used by the offline demo + tests
    ("mock", "mock-fast"): (0.0005, 0.0015),
    ("mock", "mock-smart"): (0.003, 0.015),
}

DEFAULT_RATE: Tuple[float, float] = (0.002, 0.008)


def register_price(provider: str, model: str, input_per_1k: float, output_per_1k: float) -> None:
    PRICE_TABLE[(provider.lower(), model)] = (input_per_1k, output_per_1k)


def rate_for(provider: Optional[str], model: Optional[str]) -> Tuple[float, float]:
    if provider is None or model is None:
        return DEFAULT_RATE
    return PRICE_TABLE.get((provider.lower(), model), DEFAULT_RATE)


def compute_cost(provider: Optional[str], model: Optional[str], tokens_in: int, tokens_out: int) -> float:
    """USD cost for a model call. Rounded to 6 dp (sub-cent fidelity)."""
    rin, rout = rate_for(provider, model)
    cost = (tokens_in / 1000.0) * rin + (tokens_out / 1000.0) * rout
    return round(cost, 6)
