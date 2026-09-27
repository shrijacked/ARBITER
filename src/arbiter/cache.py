"""Content-hashed record/replay cache.

The request hash is a SHA-256 of canonical JSON. Keys are sorted. Sets are
sorted before they are hashed, so ``PYTHONHASHSEED`` cannot change the hash.
Wall-clock fields, counter fields, and float values are left out of the hash.
They are still stored on the record. A cache miss returns ``None`` so the
caller can fall back; it does not gate.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from arbiter.secrets import SecretStore, render_log, render_projection

_EXCLUDED_KEYS = frozenset(
    {
        "wall_clock",
        "wallclock",
        "timestamp",
        "created_at",
        "updated_at",
        "time",
        "latency_ms",
        "latency",
        "started_at",
        "finished_at",
        "counter",
        "counters",
        "call_index",
        "request_index",
        "seq",
        "sequence",
    }
)


class CacheError(Exception):
    """A cache record cannot be stored or read."""

    def __init__(self, problem: str, cause: str, fix: str) -> None:
        self.problem = problem
        self.cause = cause
        self.fix = fix
        super().__init__(f"Problem: {problem} Cause: {cause} Fix: {fix}")


@dataclass(frozen=True, slots=True)
class CacheHit:
    request_hash: str
    model_version: str
    latency_ms: float | None
    tokens: int | None
    cost_usd: float | None
    response: object


def request_hash(request: object, store: SecretStore | None = None) -> str:
    """Hash the model-visible request. Volatile fields and floats are ignored."""
    rendered = json.loads(render_projection(_for_hash(request), store or SecretStore({})))
    blob = json.dumps(rendered, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def calibration_key(
    projection_template: object,
    option_order: list[str] | tuple[str, ...],
    model_version: str,
) -> str:
    """Content hash of the projection template, option order, and model version."""
    return request_hash(
        {
            "projection_template": projection_template,
            "option_order": list(option_order),
            "model_version": model_version,
        }
    )


class ReplayCache:
    """One JSON file per request hash. The first stored response is the one replayed."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory

    def put(
        self,
        request: object,
        response: object,
        *,
        model_version: str,
        latency_ms: float | None,
        tokens: int | None,
        cost_usd: float | None,
        store: SecretStore | None = None,
    ) -> str:
        if not model_version:
            raise CacheError(
                "The cache record has no model version.",
                "Replay is only valid for a pinned model.",
                "Pass the model version that produced the response.",
            )
        active = store or SecretStore({})
        digest = request_hash(request, active)
        path = self._path(digest)
        if path.exists():
            return digest
        envelope = {
            "request_hash": digest,
            "model_version": model_version,
            "latency_ms": latency_ms,
            "tokens": tokens,
            "cost_usd": cost_usd,
            "response": response,
        }
        line = render_log(envelope, active)
        self.directory.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(line, encoding="utf-8")
        temporary.replace(path)
        return digest

    def get(self, request: object, store: SecretStore | None = None) -> CacheHit | None:
        digest = request_hash(request, store)
        path = self._path(digest)
        if not path.exists():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise CacheError(
                "A cache file is not a record.",
                "The file does not contain a JSON object.",
                "Delete that file and record the call again.",
            )
        return CacheHit(
            request_hash=str(payload["request_hash"]),
            model_version=str(payload["model_version"]),
            latency_ms=_optional_float(payload.get("latency_ms")),
            tokens=_optional_int(payload.get("tokens")),
            cost_usd=_optional_float(payload.get("cost_usd")),
            response=payload.get("response"),
        )

    def _path(self, digest: str) -> Path:
        return self.directory / f"{digest}.json"


def _for_hash(value: object) -> Any:
    """Drop values that must not affect the hash, before secret rendering."""
    if isinstance(value, bool) or value is None or isinstance(value, (str, int)):
        return value
    if isinstance(value, float):
        return None
    if isinstance(value, set):
        prepared = [_for_hash(item) for item in value]
        prepared.sort(key=_sort_key)
        return prepared
    if isinstance(value, (list, tuple)):
        return [_for_hash(item) for item in value]
    if isinstance(value, dict):
        kept: dict[str, Any] = {}
        for key in sorted(value):
            if not isinstance(key, str) or key in _EXCLUDED_KEYS:
                continue
            item = value[key]
            if isinstance(item, float) and not isinstance(item, bool):
                continue
            kept[key] = _for_hash(item)
        return kept
    return value


def _sort_key(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _optional_float(value: object) -> float | None:
    if value is None or isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _optional_int(value: object) -> int | None:
    if value is None or isinstance(value, bool) or not isinstance(value, int):
        return None
    return value
