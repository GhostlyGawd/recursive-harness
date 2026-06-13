"""SDK-edge redaction.

Sensitive data (API keys, tokens, private keys, emails, etc.) is redacted *in the
customer's process*, before any event leaves the SDK — so secrets never reach our
ingestion API or storage. This is the core privacy control referenced by the
security model and the compliance evidence packs.

Redaction is deep (walks dicts/lists/strings) and reports *what* it redacted (the
field name or pattern type) without recording the secret value itself, so an
auditor can see that redaction occurred.
"""
from __future__ import annotations

import re
from typing import Any, List, Tuple

# Field names whose *values* are always masked, regardless of content.
DEFAULT_SENSITIVE_KEYS = frozenset({
    "password", "passwd", "secret", "api_key", "apikey", "token", "access_token",
    "refresh_token", "authorization", "auth", "private_key", "client_secret",
    "session", "cookie", "ssn", "credit_card", "card_number",
})

# Value patterns masked anywhere they appear in a string.
DEFAULT_PATTERNS: List[Tuple[str, "re.Pattern"]] = [
    ("openai_key", re.compile(r"sk-[A-Za-z0-9_\-]{20,}")),
    ("anthropic_key", re.compile(r"sk-ant-[A-Za-z0-9_\-]{20,}")),
    ("aws_key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("github_token", re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}")),
    ("bearer", re.compile(r"Bearer\s+[A-Za-z0-9._\-]{16,}")),
    ("private_key_block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("email", re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")),
    ("jwt", re.compile(r"eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}")),
]

MASK = "***REDACTED***"


class Redactor:
    """Configurable deep redactor applied at the SDK edge."""

    def __init__(
        self,
        sensitive_keys=None,
        patterns=None,
        mask: str = MASK,
        max_string: int = 20000,
        enabled: bool = True,
    ):
        self.sensitive_keys = frozenset(k.lower() for k in (sensitive_keys or DEFAULT_SENSITIVE_KEYS))
        self.patterns = patterns if patterns is not None else DEFAULT_PATTERNS
        self.mask = mask
        self.max_string = max_string
        self.enabled = enabled

    def redact(self, value: Any) -> Tuple[Any, List[str]]:
        """Return (redacted_value, sorted list of redaction tags applied)."""
        if not self.enabled:
            return value, []
        found: set = set()
        out = self._walk(value, found, key=None)
        return out, sorted(found)

    def _walk(self, value: Any, found: set, key) -> Any:
        if key is not None and isinstance(key, str) and key.lower() in self.sensitive_keys:
            if value not in (None, ""):
                found.add(f"key:{key.lower()}")
                return self.mask
        if isinstance(value, dict):
            return {k: self._walk(v, found, key=k) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [self._walk(v, found, key=None) for v in value]
        if isinstance(value, str):
            return self._scrub_str(value, found)
        return value

    def _scrub_str(self, s: str, found: set) -> str:
        if len(s) > self.max_string:
            found.add("truncated")
            s = s[: self.max_string] + "...[truncated]"
        for tag, pat in self.patterns:
            if pat.search(s):
                found.add(f"pattern:{tag}")
                s = pat.sub(self.mask, s)
        return s


def contains_unredacted_secret(value: Any, patterns=None) -> List[str]:
    """Scan a value for secret patterns — used by evals/incidents to detect leaks."""
    patterns = patterns if patterns is not None else DEFAULT_PATTERNS
    hits: set = set()
    _scan(value, patterns, hits)
    return sorted(hits)


def _scan(value: Any, patterns, hits: set) -> None:
    if isinstance(value, dict):
        for v in value.values():
            _scan(v, patterns, hits)
    elif isinstance(value, (list, tuple)):
        for v in value:
            _scan(v, patterns, hits)
    elif isinstance(value, str):
        for tag, pat in patterns:
            # 'email' alone is PII, not necessarily a leaked credential; flag the credential-like ones.
            if tag != "email" and pat.search(value):
                hits.add(tag)
