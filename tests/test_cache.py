"""Record/replay cache hashes ignore clocks, counters, and float text."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

from arbiter.cache import ReplayCache, calibration_key, request_hash
from arbiter.secrets import SecretLeak, SecretRef, SecretStore

TOKEN = "smuggle-" + ("E5f6" * 8)


def test_hash_ignores_clock_counter_and_floats() -> None:
    base = {
        "model": "jev-1.13.0",
        "options": ["search", "other"],
        "temperature": 0.2,
        "wall_clock": 10,
        "counter": 1,
    }
    moved = {
        "model": "jev-1.13.0",
        "options": ["search", "other"],
        "temperature": 0.9,
        "wall_clock": 99999,
        "counter": 40,
    }
    assert request_hash(base) == request_hash(moved)
    changed = dict(moved)
    changed["model"] = "other-model"
    assert request_hash(base) != request_hash(changed)


def test_option_order_changes_the_hash() -> None:
    forward = request_hash({"options": ["a", "b"]})
    backward = request_hash({"options": ["b", "a"]})
    assert forward != backward


def test_set_order_does_not_change_the_hash() -> None:
    assert request_hash({"tools": {"zeta", "alpha"}}) == request_hash({"tools": {"alpha", "zeta"}})


def test_hash_stable_across_processes() -> None:
    script = (
        "from arbiter.cache import request_hash\n"
        "payload = {\n"
        "    'tools': {'zeta', 'alpha', 'mu'},\n"
        "    'nested': {'b': 1, 'a': 'x'},\n"
        "    'temperature': 0.7,\n"
        "    'wall_clock': 5,\n"
        "}\n"
        "print(request_hash(payload))\n"
    )
    hashes: list[str] = []
    for seed in ("0", "1", "12345"):
        env = os.environ.copy()
        env["PYTHONHASHSEED"] = seed
        result = subprocess.run(
            [sys.executable, "-c", script],
            check=True,
            capture_output=True,
            text=True,
            env=env,
        )
        hashes.append(result.stdout.strip())
    assert len(hashes) == 3
    assert len(set(hashes)) == 1


def test_replay_returns_the_stored_response_and_miss_is_empty(tmp_path: Path) -> None:
    cache = ReplayCache(tmp_path)
    request = {"model": "jev-1.13.0", "prompt": "which tool", "options": ["search", "other"]}
    cache.put(
        request,
        {"choice": "search"},
        model_version="jev-1.13.0",
        latency_ms=12.0,
        tokens=30,
        cost_usd=0.0,
    )
    hit = cache.get(request)
    assert hit is not None
    assert hit.response == {"choice": "search"}
    assert hit.model_version == "jev-1.13.0"
    assert cache.get({"model": "jev-1.13.0", "prompt": "missing"}) is None


def test_first_record_wins(tmp_path: Path) -> None:
    cache = ReplayCache(tmp_path)
    request = {"prompt": "same"}
    cache.put(request, {"choice": "a"}, model_version="m", latency_ms=1, tokens=1, cost_usd=0)
    cache.put(request, {"choice": "b"}, model_version="m", latency_ms=9, tokens=9, cost_usd=1)
    hit = cache.get(request)
    assert hit is not None
    assert hit.response == {"choice": "a"}


def test_secret_value_is_not_cached(tmp_path: Path) -> None:
    cache = ReplayCache(tmp_path)
    store = SecretStore({"SMUGGLE": TOKEN})
    request = {"prompt": TOKEN, "api_key": SecretRef("SMUGGLE")}
    with pytest.raises(SecretLeak) as raised:
        cache.put(
            request,
            {"ok": True},
            model_version="m",
            latency_ms=1,
            tokens=1,
            cost_usd=0,
            store=store,
        )
    assert TOKEN not in str(raised.value)
    assert list(tmp_path.glob("*.json")) == []


def test_calibration_key_tracks_template_order_and_model() -> None:
    first = calibration_key("task:{task}", ["search", "other"], "jev-1.13.0")
    reordered = calibration_key("task:{task}", ["other", "search"], "jev-1.13.0")
    other_model = calibration_key("task:{task}", ["search", "other"], "jev-9")
    assert first != reordered
    assert first != other_model
    assert first == calibration_key("task:{task}", ["search", "other"], "jev-1.13.0")
