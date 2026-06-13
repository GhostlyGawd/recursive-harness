import pytest

import agentops
from agentops import policy
from agentops.storage import Store


@pytest.fixture
def clock():
    """Deterministic millisecond clock (monotonic, +1 per call)."""
    state = {"t": 1000}

    def tick():
        state["t"] += 1
        return state["t"]

    return tick


@pytest.fixture
def store():
    s = Store(":memory:")
    yield s
    s.close()


@pytest.fixture
def rec(store, clock):
    return agentops.init(
        store=store, agent="tester", project="test", tenant="default",
        policy=[policy.default_policy()],
        on_approval=lambda a: agentops.approve(by="bot"),
        clock=clock,
    )
