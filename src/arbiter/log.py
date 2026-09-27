"""Append-only decision log.

Each line is one JSON object with this schema:

- ``decision_point`` (string): which decision this was, such as ``DP2``.
- ``inputs_hash`` (string): hash of the model-visible inputs. The hash rules
  live with the replay cache.
- ``options`` (list of strings): the choices that were offered, in order.
- ``probabilities`` (list of numbers, or null): one probability per option.
- ``confidence`` (number or null): the engine's confidence, when it has one.
- ``choice`` (string or null): the chosen option. Must be one of ``options``.
- ``latency_ms`` (number or null).
- ``cost_usd`` (number or null).
- ``model_version`` (string): the pinned model that answered.
- ``outcome`` (string or null): the later label, written once on the line.

Lines are only appended. A secret value in any field fails closed and is not written.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from arbiter.secrets import SecretStore, render_log

_FIELDS = (
    "decision_point",
    "inputs_hash",
    "options",
    "probabilities",
    "confidence",
    "choice",
    "latency_ms",
    "cost_usd",
    "model_version",
    "outcome",
)


class LogError(Exception):
    """A decision record does not match the log schema."""

    def __init__(self, problem: str, cause: str, fix: str) -> None:
        self.problem = problem
        self.cause = cause
        self.fix = fix
        super().__init__(f"Problem: {problem} Cause: {cause} Fix: {fix}")


@dataclass(frozen=True, slots=True)
class DecisionRecord:
    decision_point: str
    inputs_hash: str
    options: tuple[str, ...]
    probabilities: tuple[float, ...] | None
    confidence: float | None
    choice: str | None
    latency_ms: float | None
    cost_usd: float | None
    model_version: str
    outcome: str | None

    def to_dict(self) -> dict[str, Any]:
        probabilities = None if self.probabilities is None else list(self.probabilities)
        return {
            "decision_point": self.decision_point,
            "inputs_hash": self.inputs_hash,
            "options": list(self.options),
            "probabilities": probabilities,
            "confidence": self.confidence,
            "choice": self.choice,
            "latency_ms": self.latency_ms,
            "cost_usd": self.cost_usd,
            "model_version": self.model_version,
            "outcome": self.outcome,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> DecisionRecord:
        unknown = set(payload) - set(_FIELDS)
        missing = set(_FIELDS) - set(payload)
        if unknown or missing:
            unknown_fields = sorted(unknown) or ["none"]
            missing_fields = sorted(missing) or ["none"]
            raise LogError(
                "The decision record does not match the log schema.",
                f"Unknown fields: {unknown_fields}. Missing fields: {missing_fields}.",
                "Include every schema field, and no others.",
            )
        options = _strings(payload["options"], "options")
        probabilities = _optional_floats(payload["probabilities"], "probabilities")
        if probabilities is not None and len(probabilities) != len(options):
            raise LogError(
                "Probabilities do not line up with options.",
                "The probabilities list must have one number per option.",
                "Pass null, or one probability for each option in the same order.",
            )
        choice = _optional_str(payload["choice"], "choice")
        if choice is not None and choice not in options:
            raise LogError(
                "Choice is not one of the options.",
                "A decision can only record an option that was offered.",
                "Set choice to one of options, or to null.",
            )
        return cls(
            decision_point=_required_str(payload["decision_point"], "decision_point"),
            inputs_hash=_required_str(payload["inputs_hash"], "inputs_hash"),
            options=options,
            probabilities=probabilities,
            confidence=_optional_float(payload["confidence"], "confidence"),
            choice=choice,
            latency_ms=_optional_float(payload["latency_ms"], "latency_ms"),
            cost_usd=_optional_float(payload["cost_usd"], "cost_usd"),
            model_version=_required_str(payload["model_version"], "model_version"),
            outcome=_optional_str(payload["outcome"], "outcome"),
        )


class DecisionLog:
    """JSONL file. ``append`` adds one line. ``read`` returns every line, in order."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def append(self, record: DecisionRecord, store: SecretStore | None = None) -> None:
        line = render_log(record.to_dict(), store or SecretStore({}))
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")

    def read(self) -> tuple[DecisionRecord, ...]:
        if not self.path.exists():
            return ()
        records: list[DecisionRecord] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            payload = json.loads(line)
            if not isinstance(payload, dict):
                raise LogError(
                    "A log line is not a decision record.",
                    "Each line must be one JSON object.",
                    "Append records with DecisionLog.append.",
                )
            records.append(DecisionRecord.from_dict(payload))
        return tuple(records)


def _required_str(value: object, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise LogError(
            f"{field} is empty or not text.",
            f"{field} is required on every decision record.",
            f"Set {field} to a non-empty string.",
        )
    return value


def _optional_str(value: object, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise LogError(
            f"{field} is not text.",
            f"{field} must be a string or null.",
            f"Set {field} to a string or null.",
        )
    return value


def _strings(value: object, field: str) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)) or not all(isinstance(item, str) for item in value):
        raise LogError(
            f"{field} is not a list of strings.",
            f"{field} must list the offered options.",
            f"Set {field} to a list of strings.",
        )
    return tuple(item for item in value if isinstance(item, str))


def _optional_float(value: object, field: str) -> float | None:
    if value is None:
        return None
    return _float(value, field)


def _optional_floats(value: object, field: str) -> tuple[float, ...] | None:
    if value is None:
        return None
    if not isinstance(value, (list, tuple)):
        raise LogError(
            f"{field} is not a list of numbers.",
            f"{field} must be a list of numbers or null.",
            f"Set {field} to a list of numbers or null.",
        )
    return tuple(_float(item, field) for item in value)


def _float(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise LogError(
            f"{field} is not a number.",
            f"{field} must be a number or null.",
            f"Set {field} to a number or null.",
        )
    return float(value)
