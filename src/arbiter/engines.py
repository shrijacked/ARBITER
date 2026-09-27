"""Engine contract. Missing probabilities are a real answer, not an error."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Protocol

from arbiter.questions import Choice, Noul, Question, Score


@dataclass(frozen=True, slots=True)
class TypedAnswer:
    """One engine return. ``probabilities is None`` means confidence is unavailable."""

    choice: str | None
    score: str | None
    noul: float | None
    probabilities: tuple[float, ...] | None
    confidence: float | None
    model_version: str

    @property
    def confidence_unavailable(self) -> bool:
        return self.probabilities is None


class Engine(Protocol):
    def decide(self, projection: str, question: Question) -> TypedAnswer:
        """Answer one typed question about a projection."""


@dataclass(frozen=True, slots=True)
class FakeEngine:
    """Returns a scripted answer. Used when a test needs a fixed result."""

    answer: TypedAnswer

    def decide(self, projection: str, question: Question) -> TypedAnswer:
        del projection, question
        return self.answer


@dataclass(frozen=True, slots=True)
class OracleEngine:
    """Returns the known choice with a one-hot probability."""

    truth: str
    model_version: str = "oracle"

    def decide(self, projection: str, question: Question) -> TypedAnswer:
        del projection
        if not isinstance(question, Choice):
            raise TypeError("OracleEngine answers Choice questions.")
        options = question.validated().options
        probabilities = tuple(1.0 if option == self.truth else 0.0 for option in options)
        return TypedAnswer(
            choice=self.truth,
            score=None,
            noul=None,
            probabilities=probabilities,
            confidence=1.0,
            model_version=self.model_version,
        )


@dataclass(frozen=True, slots=True)
class RandomEngine:
    """Uniform choice over the validated options. The seed makes it repeatable."""

    seed: int
    model_version: str = "random"

    def decide(self, projection: str, question: Question) -> TypedAnswer:
        del projection
        if not isinstance(question, Choice):
            raise TypeError("RandomEngine answers Choice questions.")
        options = question.validated().options
        picked = random.Random(self.seed).choice(options)
        share = 1.0 / len(options)
        return TypedAnswer(
            choice=picked,
            score=None,
            noul=None,
            probabilities=tuple(share for _ in options),
            confidence=share,
            model_version=self.model_version,
        )


def unavailable_answer(model_version: str) -> TypedAnswer:
    """A legal return for an engine that has no probabilities."""
    return TypedAnswer(
        choice=None,
        score=None,
        noul=None,
        probabilities=None,
        confidence=None,
        model_version=model_version,
    )


def answer_for(question: Question, *, choice: str | None = None) -> TypedAnswer:
    """Build a confident answer of the same kind as the question."""
    if isinstance(question, Choice):
        return TypedAnswer(choice, None, None, (1.0,), 1.0, "fake")
    if isinstance(question, Score):
        return TypedAnswer(None, question.levels[0], None, (1.0,), 1.0, "fake")
    if isinstance(question, Noul):
        return TypedAnswer(None, None, 0.5, (0.5,), 0.5, "fake")
    raise TypeError("Unsupported question.")
