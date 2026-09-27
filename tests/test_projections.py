"""Projections stay inside the token budget and do not copy secret values."""

from arbiter.projections import (
    TOKEN_LIMIT,
    ActionRecord,
    AgentState,
    ToolSpec,
    build_dp2,
    build_dp4,
    estimate_tokens,
)
from arbiter.secrets import SecretRef, SecretStore

TOKEN = "smuggle-" + ("G7h8" * 8)


def _state(result: str = "ok") -> AgentState:
    actions = tuple(
        ActionRecord(f"tool-{index}", {"q": index}, result) for index in range(8)
    )
    catalog = (
        ToolSpec("zeta", "last"),
        ToolSpec("alpha", "first"),
    )
    return AgentState("book a flight", "ticket purchased", actions, catalog)


def test_same_state_renders_the_same_projection() -> None:
    state = _state()
    assert build_dp2(state) == build_dp2(state)
    assert build_dp4(state) == build_dp4(state)


def test_catalog_is_sorted_by_tool_id() -> None:
    text = build_dp2(_state())
    assert text.index("alpha") < text.index("zeta")


def test_token_budget_holds_for_a_huge_result() -> None:
    state = _state(result="x" * 500_000)
    for text in (build_dp2(state), build_dp4(state)):
        assert estimate_tokens(text) <= TOKEN_LIMIT


def test_secret_value_does_not_appear_in_a_projection() -> None:
    store = SecretStore({"SMUGGLE": TOKEN})
    state = AgentState(
        "book a flight",
        "ticket purchased",
        (ActionRecord("search", {"api_key": SecretRef("SMUGGLE")}, "done"),),
        (ToolSpec("search", "find flights"),),
    )
    assert TOKEN not in build_dp2(state, store)
    assert TOKEN not in build_dp4(state, store)
    leaked = AgentState("book a flight", TOKEN, (), ())
    try:
        text = build_dp4(leaked, store)
    except Exception as exc:  # noqa: BLE001 - absence is the assertion
        text = str(exc)
    assert TOKEN not in text
