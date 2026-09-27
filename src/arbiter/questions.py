"""Typed questions. Invalid shapes are rejected with status 422."""

from __future__ import annotations

from dataclasses import dataclass

OTHER = "other"
MAX_CHOICE_OPTIONS = 255
MIN_SCORE_LEVELS = 2
MAX_SCORE_LEVELS = 10


class QuestionError(Exception):
    """A question would be rejected by the decision endpoint."""

    def __init__(self, problem: str, cause: str, fix: str, *, status_code: int = 422) -> None:
        self.problem = problem
        self.cause = cause
        self.fix = fix
        self.status_code = status_code
        super().__init__(f"Problem: {problem} Cause: {cause} Fix: {fix}")


@dataclass(frozen=True, slots=True)
class Criterion:
    """Contrastive description of one option."""

    what: str
    not_for: str
    examples: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Choice:
    prompt: str
    options: tuple[str, ...]
    criteria: tuple[Criterion, ...] = ()

    def validated(self) -> Choice:
        prompt = self.prompt.strip()
        if not prompt:
            raise QuestionError(
                "The choice question has no prompt.",
                "A choice needs a non-empty prompt.",
                "Set prompt to the question the engine should answer.",
            )
        options = tuple(self.options)
        if OTHER not in options:
            options = options + (OTHER,)
        if len(options) > MAX_CHOICE_OPTIONS:
            raise QuestionError(
                "The choice has more than 255 options.",
                "The choice endpoint rejects option lists longer than 255.",
                "Shrink the catalog or split the question.",
            )
        if len(set(options)) != len(options):
            raise QuestionError(
                "The choice lists the same option more than once.",
                "Option identity has to be unique.",
                "Drop the duplicate option.",
            )
        if self.criteria and len(self.criteria) not in {len(self.options), len(options)}:
            raise QuestionError(
                "Criteria do not line up with options.",
                "Each option needs its own what/not_for criterion, or none.",
                "Pass one criterion per option, or pass none.",
            )
        for criterion in self.criteria:
            if not criterion.what.strip() or not criterion.not_for.strip():
                raise QuestionError(
                    "A criterion is missing what it is for or what it is not for.",
                    "Contrastive criteria need both fields.",
                    "Fill in what and not_for for every criterion.",
                )
        return Choice(prompt, options, self.criteria)


@dataclass(frozen=True, slots=True)
class Score:
    prompt: str
    levels: tuple[str, ...]

    def validated(self) -> Score:
        prompt = self.prompt.strip()
        if not prompt:
            raise QuestionError(
                "The score question has no prompt.",
                "A score needs a non-empty prompt.",
                "Set prompt to the question the engine should answer.",
            )
        count = len(self.levels)
        if count < MIN_SCORE_LEVELS or count > MAX_SCORE_LEVELS:
            raise QuestionError(
                "The score does not have between 2 and 10 levels.",
                "The score endpoint rejects any other number of levels.",
                "Pass between 2 and 10 level labels.",
            )
        if any(not level.strip() for level in self.levels):
            raise QuestionError(
                "A score level is empty.",
                "Every level needs a label.",
                "Replace the empty level with a label.",
            )
        return Score(prompt, self.levels)


@dataclass(frozen=True, slots=True)
class Noul:
    statement: str

    def validated(self) -> Noul:
        statement = self.statement.strip()
        if not statement:
            raise QuestionError(
                "The noul question has no statement.",
                "A noul question is the probability that a statement is true.",
                "Set statement to the claim the engine should judge.",
            )
        return Noul(statement)


Question = Choice | Score | Noul
