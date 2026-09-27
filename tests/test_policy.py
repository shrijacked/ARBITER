"""Side effects stay closed unless the deterministic gate opens them."""

from arbiter.engines import TypedAnswer
from arbiter.policy import Band, DpOutput, GatingStatistic, Policy, execute_allowed


def _answer(probabilities: tuple[float, ...] | None, confidence: float | None) -> TypedAnswer:
    return TypedAnswer("search", None, None, probabilities, confidence, "fake")


def test_both_statistics_cover_every_band() -> None:
    high = _answer((0.95, 0.05), 0.95)
    mid = _answer((0.6, 0.4), 0.6)
    low = _answer((0.2, 0.1), 0.2)
    missing = _answer(None, None)
    for statistic in GatingStatistic:
        policy = Policy(statistic)
        assert policy.band(high) is Band.ACT
        assert policy.band(mid) is Band.NARROW
        assert policy.band(low) is Band.ESCALATE
        assert policy.band(missing) is Band.ESCALATE


def test_outputs_are_only_narrow_deny_or_escalate() -> None:
    assert {item.value for item in DpOutput} == {"narrow", "deny", "escalate"}


def test_side_effect_never_executes_without_the_deterministic_gate() -> None:
    for side_effect in (True, False):
        for gate in (True, False):
            for output in DpOutput:
                allowed = execute_allowed(
                    side_effect=side_effect,
                    deterministic_gate=gate,
                    output=output,
                )
                if side_effect and not gate:
                    assert allowed is False
                if output is not DpOutput.NARROW:
                    assert allowed is False
