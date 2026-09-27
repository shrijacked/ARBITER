"""Choice, score, and noul questions reject a 422 shape, and choice keeps other."""

import pytest

from arbiter.questions import OTHER, Choice, Criterion, Noul, QuestionError, Score


def test_choice_always_includes_other() -> None:
    question = Choice("Which tool?", ("search",)).validated()
    assert question.options[-1] == OTHER
    again = Choice("Which tool?", ("search", OTHER)).validated()
    assert again.options.count(OTHER) == 1


def test_choice_rejects_more_than_255_options() -> None:
    options = tuple(f"tool-{index}" for index in range(255))
    with pytest.raises(QuestionError) as raised:
        Choice("Which tool?", options).validated()
    assert raised.value.status_code == 422


def test_score_rejects_out_of_range_levels() -> None:
    with pytest.raises(QuestionError) as raised:
        Score("How done?", ("only",)).validated()
    assert raised.value.status_code == 422
    with pytest.raises(QuestionError):
        Score("How done?", tuple(f"L{index}" for index in range(11))).validated()
    assert Score("How done?", ("low", "high")).validated().levels == ("low", "high")


def test_noul_rejects_an_empty_statement() -> None:
    with pytest.raises(QuestionError) as raised:
        Noul("  ").validated()
    assert raised.value.status_code == 422
    assert "Problem:" in str(raised.value)


def test_criterion_must_say_what_and_not_for() -> None:
    with pytest.raises(QuestionError):
        Choice(
            "Which tool?",
            ("search",),
            (Criterion("", "not browsing"),),
        ).validated()
