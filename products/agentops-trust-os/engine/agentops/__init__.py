"""AgentOps — the Agent Flight Recorder SDK.

Record, govern, and prove what your AI agents do. Zero required runtime
dependencies; works with any model provider or agent framework.

Quickstart::

    import agentops
    rec = agentops.init(db_path="agentops.db", agent="my-agent", project="prod")
    with rec.task("do the thing", input="...") as task:
        rec.model_call("openai", "gpt-4o", prompt, reply, tokens_in=500, tokens_out=80)
        if rec.guard("deploy", tool="ci").allowed:
            ...
        task.succeed(output="done")
"""
from __future__ import annotations

from typing import Callable, List, Optional, Union

from . import compliance, cost, evals, incidents, policy, redaction, schema, storage
from .compliance import EvidenceExporter
from .evals import EvalSuite, aggregate_metrics, default_suite
from .incidents import IncidentDetector, render_incident_report
from .policy import Decision, PolicyEngine, default_policy
from .redaction import Redactor
from .schema import (
    ApprovalRequest,
    Event,
    EventType,
    Incident,
    Policy,
    PolicyEffect,
    Status,
    Task,
    TaskStatus,
)
from .sdk import (
    ApprovalDecision,
    GuardResult,
    PolicyDenied,
    Recorder,
    TaskHandle,
    approve,
    deny,
)
from .storage import Store

__version__ = "0.1.0"

__all__ = [
    "init", "Recorder", "Store", "TaskHandle", "GuardResult", "ApprovalDecision",
    "approve", "deny", "PolicyDenied", "PolicyEngine", "Decision", "default_policy",
    "Redactor", "EvidenceExporter", "IncidentDetector", "render_incident_report",
    "EvalSuite", "default_suite", "aggregate_metrics",
    "Task", "Event", "Policy", "Incident", "ApprovalRequest",
    "EventType", "Status", "TaskStatus", "PolicyEffect",
    "schema", "cost", "redaction", "policy", "evals", "incidents", "compliance", "storage",
    "__version__",
]


def init(
    db_path: str = ":memory:",
    agent: str = "agent",
    project: str = "default",
    tenant: str = "default",
    policy: "Optional[Union[PolicyEngine, List[Policy]]]" = None,
    redactor: Optional[Redactor] = None,
    on_approval: Optional[Callable[[ApprovalRequest], ApprovalDecision]] = None,
    clock: Optional[Callable[[], int]] = None,
    store: Optional[Store] = None,
) -> Recorder:
    """Build a ready-to-use :class:`Recorder` backed by a SQLite store.

    ``policy`` may be a :class:`PolicyEngine` or a list of :class:`Policy` objects.
    """
    store = store or Store(db_path)
    if isinstance(policy, PolicyEngine):
        engine = policy
    elif policy:
        engine = PolicyEngine(list(policy))
    else:
        engine = PolicyEngine()
    return Recorder(store=store, agent=agent, project=project, tenant=tenant,
                    policy_engine=engine, redactor=redactor, on_approval=on_approval, clock=clock)
