"""Fallbacks fire on provider and payload failures and rebuild the full context."""

import pytest

from arbiter.engines import TypedAnswer
from arbiter.fallback import FallbackStats, RecordingEngine, run_decision
from arbiter.questions import Choice

QUESTION = Choice("Which tool?", ("search", "other"))
GOOD = TypedAnswer("search", None, None, (0.7, 0.3), 0.4, "fake")
PROJECTION = "projected state"
FULL = "full context that the baseline would see"


@pytest.mark.parametrize("failure", ["429", "529", "timeout", "malformed", "out-of-range"])
def test_fallback_rebuilds_full_context(failure: str) -> None:
    if failure == "out-of-range":
        primary = RecordingEngine(TypedAnswer("nope", None, None, None, None, "fake"))
    else:
        primary = RecordingEngine(GOOD, failure=failure)
    fallback = RecordingEngine(GOOD)
    stats = FallbackStats()
    result = run_decision(primary, fallback, PROJECTION, FULL, QUESTION, stats)
    assert result.used_fallback is True
    assert result.context == FULL
    assert fallback.seen == [FULL]
    assert stats.rate == 1.0


def test_success_does_not_count_as_fallback() -> None:
    primary = RecordingEngine(GOOD)
    fallback = RecordingEngine(GOOD)
    stats = FallbackStats()
    result = run_decision(primary, fallback, PROJECTION, FULL, QUESTION, stats)
    assert result.used_fallback is False
    assert result.context == PROJECTION
    assert fallback.seen == []
    assert stats.rate == 0.0
