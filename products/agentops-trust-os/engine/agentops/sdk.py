"""The Agent Flight Recorder SDK — the customer-facing instrumentation surface.

Design goals: instrument an existing agent in minutes, change no agent logic, and
capture every action with a timestamp, actor, tool, input, output, cost, model and
status. Sensitive data is redacted at this edge before anything is persisted.

Typical use::

    import agentops
    rec = agentops.init(db_path="agentops.db", agent="coding-agent", project="demo",
                        policy_engine=agentops.policy.PolicyEngine([agentops.policy.default_policy()]),
                        on_approval=lambda a: agentops.Decision_approve())  # or wire a real console

    with rec.task("Resolve issue #42", input=issue_text) as task:
        rec.model_call("anthropic", "claude-sonnet-4", prompt, reply, tokens_in=900, tokens_out=120)
        code = rec.tool("read_file", lambda: open(path).read(), input={"path": path})
        rec.file_touch(path, "edit", bytes=len(new_src))
        if rec.guard("merge_pull_request", payload={"pr": 7}, tool="github").allowed:
            ...
        task.succeed(output="PR #7 opened")
"""
from __future__ import annotations

import contextvars
import functools
import time
from dataclasses import dataclass
from typing import Any, Callable, List, Optional

from . import cost as cost_mod
from .policy import Decision, PolicyEngine
from .redaction import Redactor
from .schema import (
    ApprovalRequest,
    Event,
    EventType,
    Status,
    Task,
    TaskStatus,
    new_id,
    now_ms,
)
from .storage import Store

_current: "contextvars.ContextVar[Optional[TaskHandle]]" = contextvars.ContextVar("agentops_task", default=None)


@dataclass
class GuardResult:
    allowed: bool
    effect: str
    reason: str = ""
    approval_id: Optional[str] = None
    pending: bool = False
    edited_payload: Any = None

    def __bool__(self) -> bool:
        return self.allowed


class PolicyDenied(Exception):
    """Raised by ``guard(..., raise_on_deny=True)`` when an action is denied."""


class TaskHandle:
    """Live handle for an in-progress task. Tracks cumulative cost for budget rules."""

    def __init__(self, recorder: "Recorder", task: Task):
        self._rec = recorder
        self.task = task
        self.cost_usd = 0.0
        self._seq_hint = 0
        self._ended = False

    @property
    def id(self) -> str:
        return self.task.task_id

    def succeed(self, output: Any = None) -> None:
        self._finish(TaskStatus.SUCCEEDED.value, output=output, success=True)

    def fail(self, reason: str, output: Any = None) -> None:
        self._finish(TaskStatus.FAILED.value, output=output, success=False, failure_reason=reason)

    def block(self, reason: str) -> None:
        self._finish(TaskStatus.BLOCKED.value, success=False, failure_reason=reason)

    def _finish(self, status: str, output: Any = None, success: Optional[bool] = None,
                failure_reason: Optional[str] = None) -> None:
        if self._ended:
            return
        self.task.status = status
        self.task.ended_at = self._rec._clock()
        if output is not None:
            red, _ = self._rec.redactor.redact(output)
            self.task.output = red
        if success is not None:
            self.task.success = success
        if failure_reason:
            self.task.failure_reason = failure_reason
        self._rec.store.update_task(self.task)
        self._ended = True


class Recorder:
    def __init__(
        self,
        store: Store,
        agent: str = "agent",
        project: str = "default",
        tenant: str = "default",
        policy_engine: Optional[PolicyEngine] = None,
        redactor: Optional[Redactor] = None,
        on_approval: Optional[Callable[[ApprovalRequest], "ApprovalDecision"]] = None,
        clock: Optional[Callable[[], int]] = None,
    ):
        self.store = store
        self.agent = agent
        self.project = project
        self.tenant = tenant
        self.policy = policy_engine or PolicyEngine()
        self.redactor = redactor or Redactor()
        self.on_approval = on_approval
        self._clock = clock or now_ms

    # ------------------------------------------------------------- task scope
    def task(self, name: str, input: Any = None, tags: Optional[List[str]] = None,
             actor: Optional[str] = None, parent: Optional[str] = None) -> "_TaskContext":
        red_in, _ = self.redactor.redact(input)
        t = Task(name=name, actor=actor or self.agent, project=self.project, tenant=self.tenant,
                 input=red_in, tags=tags or [], started_at=self._clock(),
                 parent_task_id=parent or (_current.get().id if _current.get() else None))
        self.store.create_task(t)
        return _TaskContext(self, TaskHandle(self, t))

    def task_fn(self, name: Optional[str] = None, **task_kw):
        """Decorator: wrap a function so each call is a recorded task."""
        def deco(fn):
            @functools.wraps(fn)
            def wrapper(*a, **kw):
                with self.task(name or fn.__name__, **task_kw) as t:
                    out = fn(*a, **kw)
                    if not t._ended:
                        t.succeed(output=out)
                    return out
            return wrapper
        return deco

    def _handle(self) -> TaskHandle:
        h = _current.get()
        if h is None:
            raise RuntimeError("No active agentops task. Use `with recorder.task(...) as t:` first.")
        return h

    # ------------------------------------------------------------ event emit
    def _build_event(self, task_id: str, type_: str, name: str = "", actor: Optional[str] = None,
                     input: Any = None, output: Any = None, status: str = Status.OK.value,
                     model: Optional[str] = None, provider: Optional[str] = None, cost_usd: float = 0.0,
                     tokens_in: int = 0, tokens_out: int = 0, latency_ms: int = 0,
                     error: Optional[str] = None, attributes: Optional[dict] = None) -> Event:
        """Redact + persist one event for a task. Independent of the active context
        so approvals can be resolved out-of-band, after the task scope has exited."""
        red_in, r1 = self.redactor.redact(input)
        red_out, r2 = self.redactor.redact(output)
        red_attr, r3 = self.redactor.redact(attributes or {})
        ev = Event(
            type=type_, task_id=task_id, actor=actor or self.agent, name=name, status=status,
            ts=self._clock(), input=red_in, output=red_out, model=model, provider=provider,
            cost_usd=cost_usd, tokens_in=tokens_in, tokens_out=tokens_out, latency_ms=latency_ms,
            error=error, attributes=red_attr, redactions=sorted(set(r1) | set(r2) | set(r3)),
        )
        self.store.append_event(ev)
        return ev

    def _emit(self, type_: str, **kw) -> Event:
        """Emit within the active task scope (and accrue its cost to the handle)."""
        h = self._handle()
        ev = self._build_event(h.id, type_, **kw)
        h.cost_usd += kw.get("cost_usd", 0.0)
        return ev

    # ------------------------------------------------------- primitive events
    def log(self, message: str, level: str = "info") -> Event:
        return self._emit(EventType.LOG.value, name=level, output=message, attributes={"level": level})

    def decision(self, summary: str, rationale: str = "") -> Event:
        return self._emit(EventType.DECISION.value, name=summary, attributes={"rationale": rationale})

    def file_touch(self, path: str, operation: str = "read", bytes: int = 0, diff: Optional[str] = None) -> Event:
        attrs = {"operation": operation, "bytes": bytes}
        if diff is not None:
            attrs["diff"] = diff
        status = Status.OK.value
        return self._emit(EventType.FILE_TOUCH.value, name=path, status=status, attributes=attrs)

    def api_call(self, method: str, url: str, status_code: int = 200, latency_ms: int = 0,
                 request: Any = None, response: Any = None) -> Event:
        status = Status.OK.value if 200 <= status_code < 400 else Status.ERROR.value
        return self._emit(EventType.API_CALL.value, name=f"{method} {url}", status=status,
                          input=request, output=response, latency_ms=latency_ms,
                          error=None if status == Status.OK.value else f"HTTP {status_code}",
                          attributes={"method": method, "url": url, "status_code": status_code})

    def model_call(self, provider: str, model: str, prompt: Any, response: Any,
                   tokens_in: int = 0, tokens_out: int = 0, latency_ms: int = 0,
                   status: str = Status.OK.value, error: Optional[str] = None) -> Event:
        c = cost_mod.compute_cost(provider, model, tokens_in, tokens_out)
        return self._emit(EventType.MODEL_CALL.value, name=model, provider=provider, model=model,
                          input=prompt, output=response, cost_usd=c, tokens_in=tokens_in,
                          tokens_out=tokens_out, latency_ms=latency_ms, status=status, error=error)

    def tool_call(self, name: str, input: Any = None, output: Any = None,
                  status: str = Status.OK.value, latency_ms: int = 0, error: Optional[str] = None) -> Event:
        return self._emit(EventType.TOOL_CALL.value, name=name, input=input, output=output,
                          status=status, latency_ms=latency_ms, error=error)

    def tool(self, name: str, fn: Callable[[], Any], input: Any = None) -> Any:
        """Run ``fn`` as a recorded tool call: times it, captures output/errors, re-raises."""
        start = time.perf_counter()
        try:
            out = fn()
            self.tool_call(name, input=input, output=out,
                           latency_ms=int((time.perf_counter() - start) * 1000))
            return out
        except Exception as exc:  # noqa: BLE001 — we record then re-raise
            self.tool_call(name, input=input, status=Status.ERROR.value, error=f"{type(exc).__name__}: {exc}",
                           latency_ms=int((time.perf_counter() - start) * 1000))
            raise

    # -------------------------------------------------------------- the guard
    def guard(self, action: str, payload: Any = None, tool: Optional[str] = None,
              cost_usd: float = 0.0, data_tags: Optional[List[str]] = None,
              raise_on_deny: bool = False) -> GuardResult:
        """Policy gate. Allows, denies, or routes the action through human approval."""
        h = self._handle()
        ctx = {"type": "tool_call", "tool": tool, "action": action, "actor": self.agent,
               "cost_usd": cost_usd, "task_cost_usd": h.cost_usd, "data_tags": data_tags or [],
               "payload": payload}
        decision: Decision = self.policy.evaluate(ctx)

        if decision.allowed:
            # accrue the action's declared cost so per-task budgets accumulate guarded spend
            self._emit(EventType.POLICY_CHECK.value, name=action, status=Status.OK.value,
                       cost_usd=cost_usd,
                       attributes={"effect": decision.effect, "reason": decision.reason,
                                   "policy_id": decision.policy_id, "tool": tool})
            return GuardResult(True, decision.effect, decision.reason)

        if decision.denied:
            self._emit(EventType.POLICY_CHECK.value, name=action, status=Status.BLOCKED.value,
                       error=decision.reason, attributes={"effect": decision.effect,
                       "reason": decision.reason, "policy_id": decision.policy_id, "tool": tool})
            if raise_on_deny:
                raise PolicyDenied(decision.reason)
            return GuardResult(False, decision.effect, decision.reason)

        # require_approval
        red_payload, _ = self.redactor.redact(payload)
        appr = ApprovalRequest(action=action, task_id=h.id, tenant=self.tenant, tool=tool,
                               payload=red_payload, policy_id=decision.policy_id, reason=decision.reason,
                               requested_at=self._clock())
        self.store.create_approval(appr)
        self._emit(EventType.POLICY_CHECK.value, name=action, status=Status.PENDING.value,
                   attributes={"effect": decision.effect, "reason": decision.reason,
                               "approval_id": appr.approval_id, "tool": tool})
        if self.on_approval is None:
            return GuardResult(False, decision.effect, decision.reason, approval_id=appr.approval_id, pending=True)
        verdict = self.on_approval(appr)
        return self._apply_decision(appr, verdict)

    def resolve_approval(self, approval_id: str, decision: str, by: str = "human",
                         note: str = "", edited_payload: Any = None) -> GuardResult:
        """Apply a human decision recorded out-of-band (e.g. from the API/console)."""
        appr = self.store.get_approval(approval_id)
        if not appr:
            raise KeyError(approval_id)
        return self._apply_decision(appr, ApprovalDecision(decision, by, note, edited_payload))

    def _apply_decision(self, appr: ApprovalRequest, verdict: "ApprovalDecision") -> GuardResult:
        red_edit, _ = self.redactor.redact(verdict.edited_payload)
        appr.status = verdict.decision
        appr.decided_at = self._clock()
        appr.decided_by = verdict.by
        appr.decision_note = verdict.note
        appr.edited_payload = red_edit  # redact human-supplied edits before persisting
        self.store.update_approval(appr)
        approved = verdict.decision in ("approved", "edited")
        self._build_event(appr.task_id, EventType.APPROVAL.value, name=appr.action,
                          actor=f"human:{verdict.by}",
                          status=Status.APPROVED.value if approved else Status.DENIED.value,
                          input=appr.payload, output=verdict.edited_payload,
                          attributes={"decision": verdict.decision, "note": verdict.note,
                                      "approval_id": appr.approval_id})
        return GuardResult(approved, "require_approval", appr.reason, approval_id=appr.approval_id,
                           edited_payload=verdict.edited_payload)


@dataclass
class ApprovalDecision:
    decision: str               # approved | denied | edited | escalated
    by: str = "human"
    note: str = ""
    edited_payload: Any = None


# convenience constructors for on_approval callbacks
def approve(note: str = "auto-approved", by: str = "auto") -> ApprovalDecision:
    return ApprovalDecision("approved", by, note)


def deny(note: str = "auto-denied", by: str = "auto") -> ApprovalDecision:
    return ApprovalDecision("denied", by, note)


class _TaskContext:
    """Context manager returned by ``Recorder.task`` — sets the contextvar + auto-finalizes."""

    def __init__(self, recorder: Recorder, handle: TaskHandle):
        self._rec = recorder
        self._handle = handle
        self._token = None

    def __enter__(self) -> TaskHandle:
        self._token = _current.set(self._handle)
        return self._handle

    def __exit__(self, exc_type, exc, tb) -> bool:
        # Always reset the contextvar, even if finalization raises — otherwise the
        # task scope would leak into the next task on this thread.
        try:
            if exc is not None:
                self._handle.fail(reason=f"{exc_type.__name__}: {exc}")
            elif not self._handle._ended:
                self._handle.succeed()
        finally:
            _current.reset(self._token)
        return False  # never swallow exceptions
