from agentops.policy import (
    Decision,
    PolicyEngine,
    default_policy,
    deny_data_tags,
    deny_tools,
    require_approval_for,
    task_budget,
)
from agentops.schema import Policy


def engine(*rules):
    return PolicyEngine([Policy(name="p", rules=list(rules))])


def test_default_allow_when_no_rule_matches():
    d = engine(deny_tools("shell:rm-rf")).evaluate({"tool": "read_file", "action": "read"})
    assert d.allowed and d.effect == "allow"


def test_deny_tool():
    d = engine(deny_tools("shell:rm-rf")).evaluate({"tool": "shell:rm-rf", "action": "x"})
    assert d.denied and "not permitted" in d.reason.lower()


def test_require_approval_for_action():
    d = engine(require_approval_for("merge_pull_request")).evaluate({"action": "merge_pull_request"})
    assert d.needs_approval


def test_budget_triggers_only_when_exceeded():
    e = engine(task_budget(5.0))
    assert e.evaluate({"action": "x", "task_cost_usd": 2.0}).allowed
    assert e.evaluate({"action": "x", "task_cost_usd": 6.0}).needs_approval


def test_data_tag_deny():
    d = engine(deny_data_tags("ssn")).evaluate({"action": "x", "data_tags": ["ssn", "name"]})
    assert d.denied


def test_precedence_deny_beats_approval_beats_allow():
    e = engine(
        require_approval_for("deploy"),
        deny_tools("danger"),
    )
    # action matches approval rule, tool matches deny rule -> deny wins
    d = e.evaluate({"action": "deploy", "tool": "danger"})
    assert d.denied


def test_default_policy_shape():
    pol = default_policy()
    e = PolicyEngine([pol])
    assert e.evaluate({"tool": "filesystem:delete_all", "action": "wipe"}).denied
    assert e.evaluate({"action": "merge_pull_request"}).needs_approval
    assert e.evaluate({"action": "noop"}).allowed
