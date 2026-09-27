"""Every engine returns the same shape, including 'confidence unavailable'."""

from arbiter.engines import FakeEngine, OracleEngine, RandomEngine, TypedAnswer, unavailable_answer
from arbiter.questions import Choice

QUESTION = Choice("Which tool?", ("search", "other"))


def test_engines_share_one_return_shape() -> None:
    unavailable = unavailable_answer("llm-adapter")
    engines = (
        FakeEngine(TypedAnswer("search", None, None, (0.8, 0.2), 0.6, "fake")),
        OracleEngine("search"),
        RandomEngine(seed=1),
        FakeEngine(unavailable),
    )
    for engine in engines:
        answer = engine.decide("projection", QUESTION)
        assert isinstance(answer, TypedAnswer)
        assert isinstance(answer.model_version, str) and answer.model_version


def test_confidence_unavailable_is_a_normal_return() -> None:
    answer = FakeEngine(unavailable_answer("llm-adapter")).decide("projection", QUESTION)
    assert answer.confidence_unavailable is True
    assert answer.probabilities is None
    assert answer.confidence is None


def test_oracle_and_random_are_repeatable() -> None:
    assert OracleEngine("search").decide("p", QUESTION).choice == "search"
    first = RandomEngine(seed=2).decide("p", QUESTION)
    second = RandomEngine(seed=2).decide("p", QUESTION)
    assert first == second
    assert first.probabilities is not None
    assert abs(sum(first.probabilities) - 1.0) < 1e-9
