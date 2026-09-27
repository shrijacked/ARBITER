"""Decision records round-trip through an append-only JSONL log."""

import json
from pathlib import Path

import pytest

from arbiter.log import DecisionLog, DecisionRecord, LogError
from arbiter.secrets import SecretLeak, SecretStore

TOKEN = "smuggle-" + ("C3d4" * 8)


def _record(**overrides: object) -> DecisionRecord:
    fields: dict[str, object] = {
        "decision_point": "DP2",
        "inputs_hash": "abc123",
        "options": ("search", "none_of_the_above"),
        "probabilities": (0.7, 0.3),
        "confidence": 0.4,
        "choice": "search",
        "latency_ms": 12.5,
        "cost_usd": 0.0,
        "model_version": "fake-1",
        "outcome": None,
    }
    fields.update(overrides)
    return DecisionRecord.from_dict(fields)


def test_record_round_trips_through_json() -> None:
    record = _record()
    again = DecisionRecord.from_dict(json.loads(json.dumps(record.to_dict())))
    assert again == record


def test_log_appends_and_reads_every_line(tmp_path: Path) -> None:
    path = tmp_path / "decisions.jsonl"
    log = DecisionLog(path)
    first = _record(inputs_hash="one")
    second = _record(inputs_hash="two", outcome="correct")

    log.append(first)
    after_first = path.read_text(encoding="utf-8")
    log.append(second)

    text = path.read_text(encoding="utf-8")
    assert text.startswith(after_first)
    assert text.count("\n") == 2
    assert log.read() == (first, second)


def test_secret_value_is_not_written(tmp_path: Path) -> None:
    path = tmp_path / "decisions.jsonl"
    log = DecisionLog(path)
    store = SecretStore({"SMUGGLE": TOKEN})
    leaked = _record(
        options=("search", TOKEN),
        probabilities=(0.5, 0.5),
        choice=TOKEN,
    )

    with pytest.raises(SecretLeak) as raised:
        log.append(leaked, store)

    assert TOKEN not in str(raised.value)
    assert not path.exists()


def test_bad_record_states_problem_cause_and_fix() -> None:
    with pytest.raises(LogError) as raised:
        _record(choice="not-an-option")
    text = str(raised.value)
    assert "Problem:" in text
    assert "Cause:" in text
    assert "Fix:" in text
