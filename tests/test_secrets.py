"""EF-15: projections and logs carry secret names, never values."""

import json
from pathlib import Path

import pytest

from arbiter.secrets import (
    DEFAULT_SECRET_NAMES,
    SecretLeak,
    SecretRef,
    SecretStore,
    inject,
    load_secrets,
    render_log,
    render_projection,
)

TOKEN = "smuggle-" + ("A1b2" * 8)
ROOT = Path(__file__).resolve().parents[1]


def _shapes(token: str) -> list[object]:
    ref = SecretRef("SMUGGLE")
    return [
        {"task": "book a flight", "api_key": ref},
        {"nested": {"args": [ref, "plain"], "note": "ok"}},
        {"tool": "search", "arguments": {"key": ref, "q": "flights"}},
        token,
        {"observation": f"header Authorization: Bearer {token}"},
        {"items": ["ok", token, {"inner": token}]},
        {"key_smuggle": {token: "value"}},
        [{"mixed": ref}, token],
    ]


def test_projection_and_log_keep_the_name_and_drop_the_value() -> None:
    store = SecretStore({"SMUGGLE": TOKEN})
    state = {"task": "book a flight", "api_key": SecretRef("SMUGGLE")}

    projection = render_projection(state, store)
    log = render_log({"event": "decision", "state": state}, store)

    assert "SMUGGLE" in projection
    assert "SMUGGLE" in log
    assert TOKEN not in projection
    assert TOKEN not in log
    assert json.loads(projection)["api_key"] == {"$secret": "SMUGGLE"}


def test_executor_injects_the_value_only_at_call_time() -> None:
    store = SecretStore({"SMUGGLE": TOKEN})
    arguments = {"api_key": SecretRef("SMUGGLE"), "q": "flights"}

    bound = inject(arguments, store)

    assert isinstance(bound, dict)
    assert bound["api_key"] == TOKEN
    assert TOKEN not in render_projection(arguments, store)
    assert TOKEN not in render_log(arguments, store)


def test_smuggled_token_never_appears_in_projection_or_log() -> None:
    store = SecretStore({"SMUGGLE": TOKEN})
    for shape in _shapes(TOKEN):
        for render in (render_projection, render_log):
            try:
                text = render(shape, store)
            except SecretLeak as exc:
                text = str(exc)
                assert "Problem:" in text
                assert "Cause:" in text
                assert "Fix:" in text
            assert TOKEN not in text


def test_store_repr_and_unknown_name_hide_the_value() -> None:
    store = SecretStore({"SMUGGLE": TOKEN})
    assert TOKEN not in repr(store)
    with pytest.raises(SecretLeak) as raised:
        inject({"api_key": SecretRef("MISSING")}, store)
    assert TOKEN not in str(raised.value)
    assert "Problem:" in str(raised.value)


def test_loader_keeps_only_allow_listed_names() -> None:
    environ = {
        "TYPESAFE_API_KEY": TOKEN,
        "OTHER_SECRET": "not-allow-listed-value",
        "OPENAI_API_KEY": "",
    }
    store = load_secrets(environ, DEFAULT_SECRET_NAMES)
    assert store.names() == frozenset({"TYPESAFE_API_KEY"})
    assert "not-allow-listed-value" not in render_projection({"note": "clean"}, store)


def test_env_example_lists_the_allow_list_and_no_values() -> None:
    example = (ROOT / ".env.example").read_text(encoding="utf-8")
    names = {
        line.split("=", 1)[0]
        for line in example.splitlines()
        if line and not line.startswith("#") and "=" in line
    }
    assert names == DEFAULT_SECRET_NAMES
    for line in example.splitlines():
        if "=" in line and not line.startswith("#"):
            assert line.endswith("=")
