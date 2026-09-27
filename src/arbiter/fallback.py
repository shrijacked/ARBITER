"""On engine failure, the fallback sees the full context, not the projection."""

from __future__ import annotations

from dataclasses import dataclass, field

from arbiter.engines import TypedAnswer
from arbiter.questions import Choice, Question


class EngineCallError(Exception):
    def __init__(self, status_code: int | None, problem: str, cause: str, fix: str) -> None:
        self.status_code = status_code
        self.problem = problem
        self.cause = cause
        self.fix = fix
        super().__init__(f"Problem: {problem} Cause: {cause} Fix: {fix}")


@dataclass
class FallbackStats:
    calls: int = 0
    fallbacks: int = 0

    @property
    def rate(self) -> float:
        if self.calls == 0:
            return 0.0
        return self.fallbacks / self.calls


@dataclass
class FallbackResult:
    answer: TypedAnswer
    used_fallback: bool
    context: str


@dataclass
class RecordingEngine:
    """Test double. ``failure`` makes ``decide`` raise or return a bad answer."""

    answer: TypedAnswer
    failure: str | None = None
    seen: list[str] = field(default_factory=list)

    def decide(self, projection: str, question: Question) -> TypedAnswer:
        del question
        self.seen.append(projection)
        if self.failure == "429":
            raise EngineCallError(
                429,
                "The engine was rate limited.",
                "The provider returned 429.",
                "Fall back and retry later.",
            )
        if self.failure == "529":
            raise EngineCallError(
                529,
                "The engine is overloaded.",
                "The provider returned 529.",
                "Fall back.",
            )
        if self.failure == "timeout":
            raise EngineCallError(
                None,
                "The engine timed out.",
                "The call exceeded its deadline.",
                "Fall back.",
            )
        if self.failure == "malformed":
            raise EngineCallError(
                None,
                "The engine returned a malformed answer.",
                "The payload was not a typed answer.",
                "Fall back.",
            )
        return self.answer


def run_decision(
    primary: RecordingEngine,
    fallback: RecordingEngine,
    projection: str,
    full_context: str,
    question: Question,
    stats: FallbackStats,
) -> FallbackResult:
    stats.calls += 1
    try:
        answer = primary.decide(projection, question)
        _check_in_range(answer, question)
    except EngineCallError:
        stats.fallbacks += 1
        answer = fallback.decide(full_context, question)
        return FallbackResult(answer, True, full_context)
    return FallbackResult(answer, False, projection)


def _check_in_range(answer: TypedAnswer, question: Question) -> None:
    if isinstance(question, Choice):
        options = question.validated().options
        if answer.choice not in options:
            raise EngineCallError(
                None,
                "The choice is outside the option list.",
                "The engine returned an option that was not offered.",
                "Fall back and ask again over the full context.",
            )
