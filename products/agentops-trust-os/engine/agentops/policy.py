"""Policy engine — what agents are allowed to do.

A policy is a named list of rules. Each rule *matches* on action/tool/type/actor
and, when matched (and any threshold condition is breached), contributes an
effect: ``allow``, ``deny`` or ``require_approval``. Effects combine with a strict
precedence — a single ``deny`` wins, otherwise any ``require_approval`` wins,
otherwise ``allow``. With no contributing rule the engine falls back to
``default_effect`` (allow), so policies are additive guardrails, not allowlists.

Rule shape (a plain dict, so policies are data and can be stored/edited/shared)::

    {
      "id": "no-merge-without-approval",
      "match": {"action": "merge_pull_request"},   # any of tool/action/type/actor; omit = any
      "effect": "require_approval",
      "reason": "Merges to main require a human approver",
      # optional threshold conditions (OR-combined); rule only fires if one breaches:
      "max_cost_usd": 1.0,          # this single call costs more than $1
      "task_budget_usd": 5.0,       # task cumulative cost exceeds $5
      "deny_data_tags": ["pii"],    # payload carries a forbidden data tag
    }
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from .schema import Policy, PolicyEffect, new_id

_PRECEDENCE = {PolicyEffect.DENY.value: 3, PolicyEffect.REQUIRE_APPROVAL.value: 2, PolicyEffect.ALLOW.value: 1}


@dataclass
class Decision:
    effect: str                       # allow | deny | require_approval
    reason: str = ""
    policy_id: Optional[str] = None
    rule_id: Optional[str] = None

    @property
    def allowed(self) -> bool:
        return self.effect == PolicyEffect.ALLOW.value

    @property
    def needs_approval(self) -> bool:
        return self.effect == PolicyEffect.REQUIRE_APPROVAL.value

    @property
    def denied(self) -> bool:
        return self.effect == PolicyEffect.DENY.value


class PolicyEngine:
    def __init__(self, policies: Optional[List[Policy]] = None, default_effect: str = PolicyEffect.ALLOW.value):
        self.policies = policies or []
        self.default_effect = default_effect

    @classmethod
    def from_store(cls, store, tenant: str = "default", **kw) -> "PolicyEngine":
        return cls([p for p in store.list_policies(tenant=tenant) if p.enabled], **kw)

    def evaluate(self, context: dict) -> Decision:
        """Evaluate an action context against all enabled policies."""
        best: Optional[Decision] = None
        for policy in self.policies:
            if not policy.enabled:
                continue
            for rule in policy.rules:
                if not _matches(rule.get("match", {}), context):
                    continue
                if not _triggered(rule, context):
                    continue
                effect = rule.get("effect", PolicyEffect.ALLOW.value)
                if effect not in _PRECEDENCE:
                    effect = PolicyEffect.DENY.value  # fail closed on a misconfigured/typo'd effect
                cand = Decision(effect, rule.get("reason", ""), policy.policy_id, rule.get("id"))
                if best is None or _PRECEDENCE[effect] > _PRECEDENCE[best.effect]:
                    best = cand
        return best or Decision(self.default_effect, "no matching policy rule")


def _matches(match: dict, ctx: dict) -> bool:
    # Iterate EVERY key in the rule's match (not just known ones) so a typo'd key
    # doesn't silently collapse an intended-narrow rule into match-everything.
    for key, want in match.items():
        if want is None or want == "*":
            continue
        got = ctx.get(key)
        if isinstance(want, (list, tuple, set)):
            if got not in want:
                return False
        elif got != want:
            return False
    return True


def _triggered(rule: dict, ctx: dict) -> bool:
    conds = [k for k in ("max_cost_usd", "task_budget_usd", "deny_data_tags") if k in rule]
    if not conds:
        return True  # pure match rule fires whenever it matches
    if "max_cost_usd" in rule and float(ctx.get("cost_usd") or 0.0) > float(rule["max_cost_usd"]):
        return True
    if "task_budget_usd" in rule and float(ctx.get("task_cost_usd") or 0.0) > float(rule["task_budget_usd"]):
        return True
    if "deny_data_tags" in rule:
        tags = ctx.get("data_tags") or []
        if isinstance(tags, str):  # a bare string would otherwise iterate by character
            tags = [tags]
        if set(tags) & set(rule["deny_data_tags"]):
            return True
    return False


# --------------------------------------------------------------- rule builders
def require_approval_for(*actions: str, reason: str = "Risky action requires approval") -> dict:
    return {"id": "require-approval", "match": {"action": list(actions)}, "effect": "require_approval", "reason": reason}


def deny_tools(*tools: str, reason: str = "Tool is not permitted") -> dict:
    return {"id": "deny-tools", "match": {"tool": list(tools)}, "effect": "deny", "reason": reason}


def task_budget(limit_usd: float, reason: str = "Task budget exceeded") -> dict:
    return {"id": "task-budget", "match": {}, "effect": "require_approval", "task_budget_usd": limit_usd, "reason": reason}


def deny_data_tags(*tags: str, reason: str = "Forbidden data class in payload") -> dict:
    return {"id": "deny-data", "match": {}, "effect": "deny", "deny_data_tags": list(tags), "reason": reason}


def default_policy(tenant: str = "default") -> Policy:
    """A sensible starter policy used by the demo and as a template for customers."""
    return Policy(
        name="Default agent guardrails",
        tenant=tenant,
        description="Block destructive shell, gate code merges + production writes, cap spend, block PII egress.",
        rules=[
            deny_tools("shell:rm-rf", "filesystem:delete_all", reason="Destructive operations are blocked outright"),
            require_approval_for("merge_pull_request", "deploy", "delete_resource", "send_external_email",
                                 reason="Production-affecting actions require a human approver"),
            task_budget(5.0, reason="Task exceeded its $5 budget; approve to continue"),
            deny_data_tags("ssn", "card_number", reason="Regulated PII must not leave the workflow"),
        ],
    )
