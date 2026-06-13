"""Incident detection, root-cause, rollback hints and reports.

Given a finished task's events, the detector surfaces failed or suspicious agent
behaviour — task failures, policy violations, tool-error loops, leaked secrets,
cost overruns, halted actions — each with a best-effort root cause, a remediation
suggestion and a rollback hint (e.g. which file writes to revert). This is what
turns "the agent broke something" into an investigable, reversible incident.
"""
from __future__ import annotations

from typing import List, Optional

from .redaction import contains_unredacted_secret
from .schema import Event, Incident, Task, TaskStatus


class IncidentDetector:
    def __init__(self, cost_threshold_usd: float = 10.0, tool_error_loop: int = 2):
        self.cost_threshold_usd = cost_threshold_usd
        self.tool_error_loop = tool_error_loop

    def detect(self, task: Task, events: List[Event]) -> List[Incident]:
        out: List[Incident] = []
        out += self._task_failure(task, events)
        out += self._policy_violations(task, events)
        out += self._tool_error_loops(task, events)
        out += self._secret_leaks(task, events)
        out += self._cost_overrun(task, events)
        return out

    # -- individual detectors -------------------------------------------------
    def _task_failure(self, task: Task, events: List[Event]) -> List[Incident]:
        if task.status != TaskStatus.FAILED.value:
            return []
        last_err = next((e for e in reversed(events) if e.status == "error"), None)
        writes = [e for e in events if e.type == "file_touch"
                  and (e.attributes or {}).get("operation") in ("write", "edit", "delete")]
        rollback = ("Revert file changes: " + ", ".join(
            f"{(e.attributes or {}).get('operation')} {e.name}" for e in writes)) if writes else \
            "No file mutations recorded; no rollback required."
        return [Incident(
            task_id=task.task_id, tenant=task.tenant, category="task_failure", severity="high",
            description=f"Task '{task.name}' failed: {task.failure_reason or 'unspecified'}",
            root_cause=(f"{last_err.type} '{last_err.name}' errored: {last_err.error}"
                        if last_err else (task.failure_reason or "unknown")),
            remediation="Inspect the failing step in replay; fix the tool/input and re-run from the last good event.",
            rollback_hint=rollback,
            evidence_event_ids=[last_err.event_id] if last_err else [],
        )]

    def _policy_violations(self, task: Task, events: List[Event]) -> List[Incident]:
        denials = [e for e in events if e.type == "policy_check" and e.status == "blocked"]
        if not denials:
            return []
        return [Incident(
            task_id=task.task_id, tenant=task.tenant, category="policy_violation", severity="medium",
            description=f"{len(denials)} action(s) blocked by policy.",
            root_cause="; ".join(f"{e.name}: {e.error or (e.attributes or {}).get('reason', '')}" for e in denials),
            remediation="Confirm the policy is correct; if the action is legitimate, route it through approval.",
            rollback_hint="Blocked actions did not execute — no rollback needed.",
            evidence_event_ids=[e.event_id for e in denials],
        )]

    def _tool_error_loops(self, task: Task, events: List[Event]) -> List[Incident]:
        counts: dict = {}
        for e in events:
            if e.type == "tool_call" and e.status == "error":
                counts.setdefault(e.name, []).append(e)
        out = []
        for tool, errs in counts.items():
            if len(errs) >= self.tool_error_loop:
                out.append(Incident(
                    task_id=task.task_id, tenant=task.tenant, category="tool_error_loop", severity="medium",
                    description=f"Tool '{tool}' failed {len(errs)} times — likely a retry loop.",
                    root_cause=errs[-1].error or "repeated tool error",
                    remediation="Add backoff / a retry cap; verify tool inputs and upstream availability.",
                    rollback_hint="None — failed tool calls had no committed effect.",
                    evidence_event_ids=[e.event_id for e in errs],
                ))
        return out

    def _secret_leaks(self, task: Task, events: List[Event]) -> List[Incident]:
        leaking = []
        for e in events:
            for v in (e.input, e.output, e.attributes, e.error, e.name):
                if contains_unredacted_secret(v):
                    leaking.append(e)
                    break
        if not leaking:
            return []
        return [Incident(
            task_id=task.task_id, tenant=task.tenant, category="secret_leak", severity="critical",
            description=f"Unredacted credential-like material detected in {len(leaking)} event(s).",
            root_cause="Sensitive value reached a recorded field without redaction.",
            remediation="Rotate the exposed credential immediately; tighten Redactor keys/patterns at the SDK edge.",
            rollback_hint="Purge affected events and rotate secrets; review downstream systems that saw the value.",
            evidence_event_ids=[e.event_id for e in leaking],
        )]

    def _cost_overrun(self, task: Task, events: List[Event]) -> List[Incident]:
        cost = round(sum(e.cost_usd for e in events), 6)
        if cost <= self.cost_threshold_usd:
            return []
        return [Incident(
            task_id=task.task_id, tenant=task.tenant, category="cost_overrun", severity="medium",
            description=f"Task cost ${cost:.4f} exceeded ${self.cost_threshold_usd:.2f} threshold.",
            root_cause="High token usage / excessive model calls or retries.",
            remediation="Add a task budget policy; cache, shrink prompts, or downgrade model for cheap steps.",
            rollback_hint="N/A — cost is already incurred; cap future spend with a budget policy.",
            evidence_event_ids=[e.event_id for e in events if e.type == "model_call"][:5],
        )]


def render_incident_report(incident: Incident, task: Optional[Task] = None) -> str:
    """A human-readable incident report (the 'incident report generator')."""
    sev = incident.severity.upper()
    lines = [
        f"# Incident Report — {incident.category} [{sev}]",
        "",
        f"- **Incident ID:** `{incident.incident_id}`",
        f"- **Task:** `{incident.task_id}`" + (f" — {task.name}" if task else ""),
        f"- **Detected:** {incident.detected_at} (epoch ms)",
        f"- **Severity:** {sev}",
        "",
        "## What happened",
        incident.description,
        "",
        "## Root cause",
        incident.root_cause or "_undetermined_",
        "",
        "## Remediation",
        incident.remediation or "_n/a_",
        "",
        "## Rollback",
        incident.rollback_hint or "_n/a_",
        "",
        "## Evidence",
        ("\n".join(f"- `{eid}`" for eid in incident.evidence_event_ids) or "_none_"),
    ]
    return "\n".join(lines)
