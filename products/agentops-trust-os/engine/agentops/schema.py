"""Canonical trace data model for the Agent Flight Recorder.

This module is the KEYSTONE contract every other component depends on. It is
deliberately dependency-free (stdlib only) so the SDK can be imported into any
customer process with zero install friction.

Every recorded action is an ``Event`` belonging to a ``Task``. Events carry the
universal fields the product guarantees — timestamp, actor, tool, input, output,
cost, model, status — plus a per-event ``attributes`` bag for type-specific data.

Audit integrity is provided by a SHA-256 hash chain: each event's ``hash`` is
computed over its canonical content plus the previous event's hash, so any later
tampering with a stored event is detectable (see ``compute_hash`` / storage).
"""
from __future__ import annotations

import dataclasses
import enum
import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

SCHEMA_VERSION = "0.1.0"


def new_id(prefix: str) -> str:
    """A short, prefixed, sortable-enough unique id (e.g. ``task_3f9c...``)."""
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


def now_ms() -> int:
    """Wall-clock epoch milliseconds. Inject a clock in tests for determinism."""
    return int(time.time() * 1000)


def canonical_json(obj: Any) -> str:
    """Stable JSON used for hashing — sorted keys, compact, non-ASCII preserved."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


class EventType(str, enum.Enum):
    MODEL_CALL = "model_call"      # an LLM/model invocation
    TOOL_CALL = "tool_call"        # any tool/function the agent invoked
    FILE_TOUCH = "file_touch"      # read/write/edit/delete of a file
    API_CALL = "api_call"          # outbound HTTP/API request
    DECISION = "decision"          # an explicit agent decision + rationale
    POLICY_CHECK = "policy_check"  # a policy-engine evaluation
    APPROVAL = "approval"          # a human approval decision
    INCIDENT = "incident"          # a detected failure/anomaly
    LOG = "log"                    # free-form log line


class Status(str, enum.Enum):
    OK = "ok"
    ERROR = "error"
    BLOCKED = "blocked"      # denied by policy
    PENDING = "pending"      # awaiting approval
    APPROVED = "approved"
    DENIED = "denied"


class TaskStatus(str, enum.Enum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    BLOCKED = "blocked"      # halted awaiting a human / denied


class PolicyEffect(str, enum.Enum):
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"


@dataclass
class Event:
    """One recorded action inside a task's flight."""

    type: str                                   # EventType value
    actor: str                                  # who performed it: agent name, "human:alice", tool
    task_id: str = ""
    event_id: str = field(default_factory=lambda: new_id("evt"))
    seq: int = 0                                # monotonic order within the task
    ts: int = field(default_factory=now_ms)     # epoch ms
    name: str = ""                              # tool/model name or short label
    status: str = Status.OK.value
    input: Any = None
    output: Any = None
    model: Optional[str] = None
    provider: Optional[str] = None
    cost_usd: float = 0.0
    tokens_in: int = 0
    tokens_out: int = 0
    latency_ms: int = 0
    error: Optional[str] = None
    attributes: dict = field(default_factory=dict)
    redactions: list = field(default_factory=list)   # names/types of fields redacted at the SDK edge
    prev_hash: Optional[str] = None
    hash: Optional[str] = None

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Event":
        known = {f.name for f in dataclasses.fields(cls)}
        return cls(**{k: v for k, v in d.items() if k in known})

    def hashable_content(self) -> dict:
        """The event content the hash chain commits to (excludes ``hash`` itself)."""
        d = self.to_dict()
        d.pop("hash", None)
        return d


def compute_hash(event: Event, prev_hash: Optional[str]) -> str:
    """SHA-256 over (prev_hash || canonical(event-without-hash)). Tamper-evident."""
    payload = (prev_hash or "") + "|" + canonical_json(event.hashable_content())
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass
class Task:
    """A top-level agent task — one 'flight' in the recorder."""

    name: str
    actor: str                                  # primary agent identity
    task_id: str = field(default_factory=lambda: new_id("task"))
    status: str = TaskStatus.RUNNING.value
    started_at: int = field(default_factory=now_ms)
    ended_at: Optional[int] = None
    project: str = "default"
    tenant: str = "default"
    input: Any = None
    output: Any = None
    tags: list = field(default_factory=list)
    parent_task_id: Optional[str] = None
    success: Optional[bool] = None              # eval/outcome label
    failure_reason: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Task":
        known = {f.name for f in dataclasses.fields(cls)}
        return cls(**{k: v for k, v in d.items() if k in known})


@dataclass
class ApprovalRequest:
    """A risky action paused for a human decision (the approval console queue)."""

    action: str                                 # human-readable description of the action
    task_id: str
    approval_id: str = field(default_factory=lambda: new_id("apr"))
    tenant: str = "default"
    tool: Optional[str] = None
    payload: Any = None
    policy_id: Optional[str] = None
    reason: str = ""
    status: str = "pending"                     # pending|approved|denied|edited|escalated
    requested_at: int = field(default_factory=now_ms)
    decided_at: Optional[int] = None
    decided_by: Optional[str] = None
    decision_note: str = ""
    edited_payload: Any = None

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "ApprovalRequest":
        known = {f.name for f in dataclasses.fields(cls)}
        return cls(**{k: v for k, v in d.items() if k in known})


@dataclass
class Policy:
    """A named set of rules governing what agents may do."""

    name: str
    policy_id: str = field(default_factory=lambda: new_id("pol"))
    tenant: str = "default"
    description: str = ""
    rules: list = field(default_factory=list)   # list of rule dicts (see policy.py)
    enabled: bool = True

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Policy":
        known = {f.name for f in dataclasses.fields(cls)}
        return cls(**{k: v for k, v in d.items() if k in known})


@dataclass
class Incident:
    """A detected failure or suspicious action, with root cause + remediation."""

    task_id: str
    category: str                               # e.g. task_failure, policy_violation, secret_leak
    severity: str                               # low|medium|high|critical
    description: str
    incident_id: str = field(default_factory=lambda: new_id("inc"))
    tenant: str = "default"
    detected_at: int = field(default_factory=now_ms)
    root_cause: str = ""
    remediation: str = ""
    rollback_hint: str = ""
    evidence_event_ids: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Incident":
        known = {f.name for f in dataclasses.fields(cls)}
        return cls(**{k: v for k, v in d.items() if k in known})
