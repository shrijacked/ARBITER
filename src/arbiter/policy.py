"""Policy bands. Side effects execute only through the deterministic gate."""

from __future__ import annotations

from enum import Enum

from arbiter.engines import TypedAnswer


class Band(Enum):
    ACT = "act"
    NARROW = "narrow"
    ESCALATE = "escalate"


class DpOutput(Enum):
    """What a decision point is allowed to tell the runtime."""

    NARROW = "narrow"
    DENY = "deny"
    ESCALATE = "escalate"


class GatingStatistic(Enum):
    MAX_PROBABILITY = "max_probability"
    CONFIDENCE = "confidence"


class PolicyError(Exception):
    def __init__(self, problem: str, cause: str, fix: str) -> None:
        self.problem = problem
        self.cause = cause
        self.fix = fix
        super().__init__(f"Problem: {problem} Cause: {cause} Fix: {fix}")


class Policy:
    """Map a probability to a band. Both statistics exist; the caller picks one."""

    def __init__(
        self,
        statistic: GatingStatistic = GatingStatistic.MAX_PROBABILITY,
        *,
        act_at: float = 0.9,
        narrow_at: float = 0.5,
    ) -> None:
        if not 0.0 <= narrow_at <= act_at <= 1.0:
            raise PolicyError(
                "The policy bands are out of order.",
                "narrow_at has to be at most act_at, and both have to sit in 0 to 1.",
                "Set narrow_at <= act_at, both between 0 and 1.",
            )
        self.statistic = statistic
        self.act_at = act_at
        self.narrow_at = narrow_at

    def band(self, answer: TypedAnswer) -> Band:
        value = _statistic(answer, self.statistic)
        if value is None:
            return Band.ESCALATE
        if value >= self.act_at:
            return Band.ACT
        if value >= self.narrow_at:
            return Band.NARROW
        return Band.ESCALATE

    def output(self, answer: TypedAnswer) -> DpOutput:
        chosen = self.band(answer)
        if chosen is Band.ESCALATE:
            return DpOutput.ESCALATE
        return DpOutput.NARROW


def execute_allowed(*, side_effect: bool, deterministic_gate: bool, output: DpOutput) -> bool:
    """A side-effecting call runs only when deterministic code opens the gate.

    Decision-point output cannot allow or elevate. Escalate and deny never execute.
    """
    if not isinstance(output, DpOutput):
        raise PolicyError(
            "The decision output is not a known action.",
            "Only narrow, deny, and escalate are legal outputs.",
            "Map the engine answer through Policy.output.",
        )
    if output is not DpOutput.NARROW:
        return False
    if side_effect:
        return deterministic_gate
    return True


def _statistic(answer: TypedAnswer, statistic: GatingStatistic) -> float | None:
    if statistic is GatingStatistic.CONFIDENCE:
        return answer.confidence
    if answer.probabilities is None:
        return None
    return max(answer.probabilities)
