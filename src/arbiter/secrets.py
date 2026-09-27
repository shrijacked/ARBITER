"""Secrets are allow-listed by name. Values are injected only at call time.

Projections and logs must go through ``render_projection`` and ``render_log``.
Those functions never receive secret values: a ``SecretRef`` becomes a name, and
a registered value found in model-visible state fails closed instead of being copied.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

DEFAULT_SECRET_NAMES = frozenset(
    {
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "TYPESAFE_API_KEY",
    }
)

_MIN_SUBSTRING = 8


class SecretLeak(Exception):
    """A secret value was blocked from model-visible state."""

    def __init__(self, problem: str, cause: str, fix: str) -> None:
        self.problem = problem
        self.cause = cause
        self.fix = fix
        super().__init__(f"Problem: {problem} Cause: {cause} Fix: {fix}")


@dataclass(frozen=True, slots=True)
class SecretRef:
    """A secret named for projections and logs. The value stays in the store."""

    name: str


class SecretStore:
    """Holds secret values. ``repr`` and names are safe; ``resolve`` is for the executor."""

    def __init__(self, values: Mapping[str, str]) -> None:
        self._values = {name: value for name, value in values.items() if value}

    def names(self) -> frozenset[str]:
        return frozenset(self._values)

    def resolve(self, name: str) -> str:
        try:
            return self._values[name]
        except KeyError:
            raise SecretLeak(
                f"No value is stored for secret {name!r}.",
                "The call names a secret that was not loaded.",
                "Add that name to the allow-list and set it in .env.",
            ) from None

    def __repr__(self) -> str:
        listed = ", ".join(sorted(self._values))
        return f"SecretStore(names=[{listed}])"

    def _forbidden(self) -> tuple[str, ...]:
        return tuple(self._values.values())


def load_secrets(environ: Mapping[str, str], allow: frozenset[str]) -> SecretStore:
    """Copy only allow-listed, non-empty names. Everything else stays out of the store."""
    values = {name: environ[name] for name in allow if environ.get(name)}
    return SecretStore(values)


def inject(value: object, store: SecretStore) -> object:
    """Replace secret references with values for the tool call. Do not log the result."""
    if isinstance(value, SecretRef):
        return store.resolve(value.name)
    if isinstance(value, Mapping):
        return {key: inject(item, store) for key, item in value.items()}
    if isinstance(value, list):
        return [inject(item, store) for item in value]
    if isinstance(value, tuple):
        return tuple(inject(item, store) for item in value)
    return value


def render_projection(state: object, store: SecretStore) -> str:
    return _dump(state, store)


def render_log(record: object, store: SecretStore) -> str:
    return _dump(record, store)


def _dump(value: object, store: SecretStore) -> str:
    return json.dumps(_public(value, store._forbidden()), sort_keys=True)


def _public(value: object, forbidden: tuple[str, ...]) -> Any:
    if isinstance(value, SecretRef):
        _reject(value.name, forbidden)
        return {"$secret": value.name}
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        _reject(value, forbidden)
        return value
    if isinstance(value, Mapping):
        rendered: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise SecretLeak(
                    "A mapping key cannot be shown to a model.",
                    "Projections only allow string keys.",
                    "Use a string key, or refer to a secret with SecretRef.",
                )
            _reject(key, forbidden)
            rendered[key] = _public(item, forbidden)
        return rendered
    if isinstance(value, (list, tuple)):
        return [_public(item, forbidden) for item in value]
    raise SecretLeak(
        "A value cannot be shown to a model.",
        "The state contained a type projections do not allow.",
        "Pass JSON values, or a SecretRef for anything secret.",
    )


def _reject(text: str, forbidden: tuple[str, ...]) -> None:
    for secret in forbidden:
        if not secret:
            continue
        matched = text == secret or (len(secret) >= _MIN_SUBSTRING and secret in text)
        if matched:
            raise SecretLeak(
                "A secret value was about to enter a projection or log.",
                "Model-visible state contained a registered secret value.",
                "Pass SecretRef(name) and let the executor inject the value at call time.",
            )
