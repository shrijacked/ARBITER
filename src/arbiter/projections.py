"""Token-budgeted projections. Same state always renders the same text."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from arbiter.secrets import SecretStore, render_projection

TOKEN_LIMIT = 32_000
_CHARS_PER_TOKEN = 4


@dataclass(frozen=True, slots=True)
class ToolSpec:
    tool_id: str
    description: str


@dataclass(frozen=True, slots=True)
class ActionRecord:
    tool_id: str
    arguments: dict[str, object]
    result: str


@dataclass(frozen=True, slots=True)
class AgentState:
    task: str
    acceptance: str
    actions: tuple[ActionRecord, ...]
    catalog: tuple[ToolSpec, ...] = ()


def estimate_tokens(text: str) -> int:
    """A ceiling of 1 token per 4 characters. This is a budget guard, not a measurement."""
    if not text:
        return 0
    return (len(text) + _CHARS_PER_TOKEN - 1) // _CHARS_PER_TOKEN


def build_dp2(state: AgentState, store: SecretStore | None = None) -> str:
    """Task, the last three actions, and the catalog sorted by tool id."""
    view: dict[str, Any] = {
        "decision_point": "DP2",
        "task": state.task,
        "recent_actions": [_action(item) for item in state.actions[-3:]],
        "catalog": [
            {"tool_id": tool.tool_id, "description": tool.description}
            for tool in sorted(state.catalog, key=lambda tool: tool.tool_id)
        ],
    }
    return _fit(view, store)


def build_dp4(state: AgentState, store: SecretStore | None = None, *, last_k: int = 5) -> str:
    """Task, acceptance criteria, and the last k actions."""
    view: dict[str, Any] = {
        "decision_point": "DP4",
        "task": state.task,
        "acceptance": state.acceptance,
        "recent_actions": [_action(item) for item in state.actions[-last_k:]],
    }
    return _fit(view, store)


def _action(record: ActionRecord) -> dict[str, object]:
    return {
        "tool_id": record.tool_id,
        "arguments": record.arguments,
        "result": record.result,
    }


def _fit(view: dict[str, Any], store: SecretStore | None) -> str:
    active = store or SecretStore({})
    raw_actions = view.get("recent_actions")
    actions: list[Any] = list(raw_actions) if isinstance(raw_actions, list) else []
    shrunk = dict(view)
    text = render_projection(shrunk, active)
    while estimate_tokens(text) > TOKEN_LIMIT and actions:
        actions = actions[1:]
        shrunk["recent_actions"] = actions
        text = render_projection(shrunk, active)
    if estimate_tokens(text) > TOKEN_LIMIT:
        encoded = json.loads(text)
        _truncate_strings(encoded, TOKEN_LIMIT * _CHARS_PER_TOKEN)
        text = render_projection(encoded, active)
    if estimate_tokens(text) > TOKEN_LIMIT:
        text = text[: TOKEN_LIMIT * _CHARS_PER_TOKEN]
    return text


def _truncate_strings(value: Any, budget: int) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if isinstance(item, str) and len(item) > budget:
                value[key] = item[:budget]
            else:
                _truncate_strings(item, budget)
    elif isinstance(value, list):
        for item in value:
            _truncate_strings(item, budget)
