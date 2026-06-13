"""Slack approval notifications.

When the policy engine routes an action to human approval, post it to Slack with
Approve / Deny buttons (Block Kit). Uses stdlib ``urllib`` so there is no Slack
SDK dependency. ``approval_blocks`` is pure (no I/O) so it is easy to test.
"""
from __future__ import annotations

import json
import urllib.request
from typing import Any

from ..schema import ApprovalRequest


def approval_blocks(approval: ApprovalRequest, dashboard_url: str = "") -> dict:
    """Build a Slack Block Kit message for a pending approval."""
    link = f"{dashboard_url}/#/approvals/{approval.approval_id}" if dashboard_url else ""
    return {
        "text": f"Approval required: {approval.action}",
        "blocks": [
            {"type": "header", "text": {"type": "plain_text", "text": "🔐 Agent approval required"}},
            {"type": "section", "text": {"type": "mrkdwn",
                "text": f"*Action:* {approval.action}\n*Reason:* {approval.reason or '—'}\n"
                        f"*Tool:* {approval.tool or '—'}\n*Task:* `{approval.task_id}`"}},
            {"type": "section", "text": {"type": "mrkdwn",
                "text": f"```{json.dumps(approval.payload, indent=2)[:2500]}```"}},
            {"type": "actions", "elements": [
                {"type": "button", "style": "primary", "text": {"type": "plain_text", "text": "Approve"},
                 "value": approval.approval_id, "action_id": "agentops_approve"},
                {"type": "button", "style": "danger", "text": {"type": "plain_text", "text": "Deny"},
                 "value": approval.approval_id, "action_id": "agentops_deny"},
            ] + ([{"type": "button", "text": {"type": "plain_text", "text": "Open console"}, "url": link}] if link else [])},
        ],
    }


def post_approval(webhook_url: str, approval: ApprovalRequest, dashboard_url: str = "", timeout: float = 5.0) -> int:
    """POST an approval request to a Slack incoming webhook. Returns HTTP status."""
    payload = json.dumps(approval_blocks(approval, dashboard_url)).encode("utf-8")
    req = urllib.request.Request(webhook_url, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - caller supplies trusted webhook
        return resp.status
