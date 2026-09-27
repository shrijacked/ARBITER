"""Calibrators refuse thin data and do not treat a saturated 1.0 as a logit."""

import pytest

from arbiter.calibration import (
    MIN_SAMPLES,
    CalibrationError,
    auroc,
    brier_score,
    coverage,
    expected_calibration_error,
    fit_histogram,
    fit_isotonic,
    fit_temperature,
)


def _labeled(count: int) -> tuple[list[float], list[int]]:
    probabilities = [0.2] * (count // 2) + [0.9] * (count - count // 2)
    labels = [0] * (count // 2) + [1] * (count - count // 2)
    return probabilities, labels


def test_fit_refuses_fewer_than_200_labels() -> None:
    probabilities, labels = _labeled(MIN_SAMPLES - 1)
    with pytest.raises(CalibrationError) as raised:
        fit_isotonic(probabilities, labels)
    assert "Problem:" in str(raised.value)
    with pytest.raises(CalibrationError):
        fit_histogram(probabilities, labels)
    with pytest.raises(CalibrationError):
        fit_temperature([0.0] * (MIN_SAMPLES - 1), labels)


def test_temperature_requires_logits() -> None:
    _, labels = _labeled(MIN_SAMPLES)
    with pytest.raises(CalibrationError) as raised:
        fit_temperature(None, labels)
    text = str(raised.value)
    assert "logits" in text
    assert "histogram" in text


def test_saturated_probability_is_clipped() -> None:
    probabilities, labels = _labeled(MIN_SAMPLES)
    probabilities[0] = 1.0
    calibrator = fit_histogram(probabilities, labels)
    assert calibrator.predict(1.0) < 1.0
    fitted = fit_isotonic(probabilities, labels)
    assert fitted.predict(1.0) <= 1.0


def test_metrics_on_a_separated_sample() -> None:
    probabilities, labels = _labeled(MIN_SAMPLES)
    assert brier_score(probabilities, labels) < 0.1
    ece, floor = expected_calibration_error(probabilities, labels)
    assert ece >= 0.0
    assert floor > 0.0
    score = auroc(probabilities, labels)
    assert score is not None and score > 0.9
    assert coverage(probabilities, 0.5) == 0.5
    assert auroc([0.2, 0.9], [1, 1]) is None
