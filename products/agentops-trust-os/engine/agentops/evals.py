"""Agent evals — measure task quality, not just model quality.

An eval is a callable ``(task, events) -> EvalResult``. The built-ins below cover
the dimensions the product promises (success, cost, latency, tool misuse, policy
compliance, secret leakage, human-intervention). Customers register their own
workflow-specific evals with ``EvalSuite.add``.

``aggregate_metrics`` rolls per-task signals into the fleet-level numbers the
executive dashboard reports (success rate, p50/p95 latency, intervention rate,
retry rate, failure-mode histogram).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional, Tuple

from .redaction import contains_unredacted_secret
from .schema import Event, Task, TaskStatus


@dataclass
class EvalResult:
    name: str
    passed: bool
    score: float = 1.0          # 0..1
    detail: str = ""
    severity: str = "info"      # info|warn|fail

    def to_dict(self) -> dict:
        return {"name": self.name, "passed": self.passed, "score": round(self.score, 4),
                "detail": self.detail, "severity": self.severity}


Eval = Callable[[Task, List[Event]], EvalResult]


# ----------------------------------------------------------------- built-in evals
def task_succeeded(task: Task, events: List[Event]) -> EvalResult:
    ok = task.status == TaskStatus.SUCCEEDED.value
    return EvalResult("task_succeeded", ok, 1.0 if ok else 0.0,
                      f"status={task.status}", "info" if ok else "fail")


def cost_within_budget(max_usd: float) -> Eval:
    def _eval(task: Task, events: List[Event]) -> EvalResult:
        cost = round(sum(e.cost_usd for e in events), 6)
        ok = cost <= max_usd
        return EvalResult("cost_within_budget", ok, 1.0 if ok else max(0.0, 1 - (cost - max_usd) / max(max_usd, 1e-9)),
                          f"cost=${cost:.4f} budget=${max_usd:.2f}", "info" if ok else "warn")
    return _eval


def latency_within(max_ms: int) -> Eval:
    def _eval(task: Task, events: List[Event]) -> EvalResult:
        total = sum(e.latency_ms for e in events)
        ok = total <= max_ms
        return EvalResult("latency_within", ok, 1.0 if ok else max(0.0, max_ms / max(total, 1)),
                          f"latency={total}ms budget={max_ms}ms", "info" if ok else "warn")
    return _eval


def no_policy_violations(task: Task, events: List[Event]) -> EvalResult:
    denials = [e for e in events if e.type == "policy_check" and e.status == "blocked"]
    ok = not denials
    return EvalResult("no_policy_violations", ok, 1.0 if ok else 0.0,
                      f"{len(denials)} policy denial(s)", "info" if ok else "fail")


def no_unredacted_secrets(task: Task, events: List[Event]) -> EvalResult:
    leaks: List[str] = []
    for e in events:
        for v in (e.input, e.output, e.attributes, e.error, e.name):
            leaks += contains_unredacted_secret(v)
    ok = not leaks
    return EvalResult("no_unredacted_secrets", ok, 1.0 if ok else 0.0,
                      "clean" if ok else f"leaked: {sorted(set(leaks))}", "info" if ok else "fail")


def tool_error_rate(max_rate: float = 0.2) -> Eval:
    def _eval(task: Task, events: List[Event]) -> EvalResult:
        tools = [e for e in events if e.type == "tool_call"]
        errs = [e for e in tools if e.status == "error"]
        rate = (len(errs) / len(tools)) if tools else 0.0
        ok = rate <= max_rate
        return EvalResult("tool_error_rate", ok, 1.0 - rate,
                          f"{len(errs)}/{len(tools)} tool errors (rate={rate:.0%})", "info" if ok else "warn")
    return _eval


def required_approvals_present(task: Task, events: List[Event]) -> EvalResult:
    """If any action required approval, an approval decision must be recorded."""
    pending = [e for e in events if e.type == "policy_check" and e.status == "pending"]
    decided = [e for e in events if e.type == "approval"]
    ok = len(decided) >= len(pending)
    return EvalResult("required_approvals_present", ok, 1.0 if ok else 0.0,
                      f"{len(pending)} required, {len(decided)} decided", "info" if ok else "fail")


def default_suite(cost_budget: float = 5.0, latency_budget_ms: int = 120000) -> "EvalSuite":
    return EvalSuite([
        task_succeeded,
        cost_within_budget(cost_budget),
        latency_within(latency_budget_ms),
        no_policy_violations,
        no_unredacted_secrets,
        tool_error_rate(0.34),
        required_approvals_present,
    ])


# ---------------------------------------------------------------------- the suite
class EvalSuite:
    def __init__(self, evals: Optional[List[Eval]] = None):
        self.evals: List[Eval] = list(evals or [])

    def add(self, fn: Eval) -> "EvalSuite":
        self.evals.append(fn)
        return self

    def run(self, task: Task, events: List[Event]) -> dict:
        results = [fn(task, events) for fn in self.evals]
        passed = all(r.passed for r in results)
        score = round(sum(r.score for r in results) / len(results), 4) if results else 1.0
        return {
            "task_id": task.task_id,
            "passed": passed,
            "score": score,
            "fail_count": sum(1 for r in results if not r.passed),
            "results": [r.to_dict() for r in results],
        }


def _percentile(values: List[int], pct: float) -> int:
    if not values:
        return 0
    s = sorted(values)
    k = max(0, min(len(s) - 1, int(round((pct / 100.0) * (len(s) - 1)))))
    return s[k]


def aggregate_metrics(items: List[Tuple[Task, List[Event]]]) -> dict:
    """Fleet-level rollup over many (task, events) pairs for the exec dashboard."""
    n = len(items)
    if n == 0:
        return {"tasks": 0}
    succeeded = sum(1 for t, _ in items if t.status == TaskStatus.SUCCEEDED.value)
    costs = [round(sum(e.cost_usd for e in evs), 6) for _, evs in items]
    latencies = [sum(e.latency_ms for e in evs) for _, evs in items]
    interventions = sum(1 for _, evs in items if any(e.type == "approval" for e in evs))
    retries = sum(sum(1 for e in evs if e.status == "error" and e.type == "tool_call") for _, evs in items)
    failure_modes: dict = {}
    for t, _ in items:
        if t.status in (TaskStatus.FAILED.value, TaskStatus.BLOCKED.value) and t.failure_reason:
            failure_modes[t.failure_reason] = failure_modes.get(t.failure_reason, 0) + 1
    return {
        "tasks": n,
        "success_rate": round(succeeded / n, 4),
        "avg_cost_usd": round(sum(costs) / n, 6),
        "total_cost_usd": round(sum(costs), 4),
        "latency_p50_ms": _percentile(latencies, 50),
        "latency_p95_ms": _percentile(latencies, 95),
        "human_intervention_rate": round(interventions / n, 4),
        "tool_retries": retries,
        "failure_modes": failure_modes,
    }
