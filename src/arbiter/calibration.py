"""Post-hoc calibrators and the metrics that read them.

Temperature scaling is only fit when logits are supplied. A probability of 1.0
is clipped before a histogram or isotonic fit. Fewer than 200 labels is refused.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

MIN_SAMPLES = 200
_EPSILON = 1e-6


class CalibrationError(Exception):
    def __init__(self, problem: str, cause: str, fix: str) -> None:
        self.problem = problem
        self.cause = cause
        self.fix = fix
        super().__init__(f"Problem: {problem} Cause: {cause} Fix: {fix}")


@dataclass(frozen=True, slots=True)
class IsotonicCalibrator:
    thresholds: tuple[float, ...]
    values: tuple[float, ...]

    def predict(self, probability: float) -> float:
        clipped = _clip(probability)
        chosen = self.values[0]
        for threshold, value in zip(self.thresholds, self.values, strict=True):
            if clipped >= threshold:
                chosen = value
        return chosen


@dataclass(frozen=True, slots=True)
class HistogramCalibrator:
    edges: tuple[float, ...]
    rates: tuple[float, ...]

    def predict(self, probability: float) -> float:
        clipped = _clip(probability)
        for index, edge in enumerate(self.edges[1:]):
            if clipped <= edge or index == len(self.rates) - 1:
                return self.rates[index]
        return self.rates[-1]


@dataclass(frozen=True, slots=True)
class TemperatureCalibrator:
    temperature: float

    def predict_logit(self, logit: float) -> float:
        return _clip(_sigmoid(logit / self.temperature))


def fit_isotonic(
    probabilities: Sequence[float],
    labels: Sequence[int],
    *,
    min_samples: int = MIN_SAMPLES,
) -> IsotonicCalibrator:
    _require_samples(probabilities, labels, min_samples)
    pairs = sorted(
        (_clip(probability), float(label))
        for probability, label in zip(probabilities, labels, strict=True)
    )
    blocks: list[list[float]] = [[prob, label, 1.0] for prob, label in pairs]
    index = 0
    while index < len(blocks) - 1:
        if blocks[index][1] <= blocks[index + 1][1]:
            index += 1
            continue
        weight = blocks[index][2] + blocks[index + 1][2]
        merged = (
            blocks[index][1] * blocks[index][2] + blocks[index + 1][1] * blocks[index + 1][2]
        ) / weight
        blocks[index][1] = merged
        blocks[index][2] = weight
        del blocks[index + 1]
        if index:
            index -= 1
    return IsotonicCalibrator(
        thresholds=tuple(block[0] for block in blocks),
        values=tuple(block[1] for block in blocks),
    )


def fit_histogram(
    probabilities: Sequence[float],
    labels: Sequence[int],
    *,
    bins: int = 10,
    min_samples: int = MIN_SAMPLES,
) -> HistogramCalibrator:
    _require_samples(probabilities, labels, min_samples)
    if bins < 1:
        raise CalibrationError(
            "The histogram has no bins.",
            "A histogram calibrator needs at least one bin.",
            "Pass bins >= 1.",
        )
    counts = [0] * bins
    correct = [0.0] * bins
    width = 1.0 / bins
    for probability, label in zip(probabilities, labels, strict=True):
        clipped = _clip(probability)
        index = min(bins - 1, int(clipped / width))
        counts[index] += 1
        correct[index] += float(label)
    rates = tuple(
        (correct[index] / counts[index]) if counts[index] else 0.0 for index in range(bins)
    )
    edges = tuple(index * width for index in range(bins + 1))
    return HistogramCalibrator(edges=edges, rates=rates)


def fit_temperature(
    logits: Sequence[float] | None,
    labels: Sequence[int],
    *,
    min_samples: int = MIN_SAMPLES,
) -> TemperatureCalibrator:
    if logits is None:
        raise CalibrationError(
            "Temperature scaling was asked to fit without logits.",
            "The engine returned probabilities, not logits.",
            "Use the isotonic or histogram calibrator instead.",
        )
    _require_samples(logits, labels, min_samples)
    best_temperature = 1.0
    best_loss = math.inf
    for step in range(1, 100):
        temperature = step / 20
        loss = _nll(logits, labels, temperature)
        if loss < best_loss:
            best_loss = loss
            best_temperature = temperature
    return TemperatureCalibrator(best_temperature)


def brier_score(probabilities: Sequence[float], labels: Sequence[int]) -> float:
    pairs = list(zip(probabilities, labels, strict=True))
    if not pairs:
        raise CalibrationError(
            "Brier score needs at least one labeled probability.",
            "The label list is empty.",
            "Pass the probabilities and the 0/1 labels from the same decisions.",
        )
    total = sum((_clip(probability) - label) ** 2 for probability, label in pairs)
    return total / len(pairs)


def expected_calibration_error(
    probabilities: Sequence[float],
    labels: Sequence[int],
    *,
    bins: int = 10,
) -> tuple[float, float]:
    """Return ``(ece, noise_floor)``.

    The noise floor is ``1 / sqrt(n)``. It is this package's finite-sample
    reference, not a measured model result.
    """
    pairs = list(zip(probabilities, labels, strict=True))
    if not pairs:
        raise CalibrationError(
            "ECE needs at least one labeled probability.",
            "The label list is empty.",
            "Pass the probabilities and the 0/1 labels from the same decisions.",
        )
    calibrator = fit_histogram(probabilities, labels, bins=bins, min_samples=1)
    total = 0.0
    width = 1.0 / bins
    for index, rate in enumerate(calibrator.rates):
        members = [
            label
            for probability, label in pairs
            if index == min(bins - 1, int(_clip(probability) / width))
        ]
        if not members:
            continue
        confidence = (index + 0.5) * width
        total += (len(members) / len(pairs)) * abs(rate - confidence)
    return total, 1.0 / math.sqrt(len(pairs))


def auroc(probabilities: Sequence[float], labels: Sequence[int]) -> float | None:
    """Area under the ROC curve. ``None`` when the labels are all one class."""
    pairs = list(zip(probabilities, labels, strict=True))
    positives = [probability for probability, label in pairs if label == 1]
    negatives = [probability for probability, label in pairs if label == 0]
    if not positives or not negatives:
        return None
    favorable = 0.0
    for positive in positives:
        for negative in negatives:
            if positive > negative:
                favorable += 1.0
            elif positive == negative:
                favorable += 0.5
    return favorable / (len(positives) * len(negatives))


def coverage(probabilities: Sequence[float], threshold: float) -> float:
    if not probabilities:
        return 0.0
    kept = sum(1 for probability in probabilities if probability >= threshold)
    return kept / len(probabilities)


def _require_samples(values: Sequence[float], labels: Sequence[int], min_samples: int) -> None:
    if len(values) != len(labels):
        raise CalibrationError(
            "Probabilities and labels have different lengths.",
            "Each probability needs the label from the same decision.",
            "Pass one label per probability.",
        )
    if len(labels) < min_samples:
        raise CalibrationError(
            f"Refusing to fit a calibrator on {len(labels)} labels.",
            f"The minimum is {min_samples} labels.",
            "Collect more labeled decisions, or keep the escalate default.",
        )


def _clip(probability: float) -> float:
    if probability >= 1.0:
        return 1.0 - _EPSILON
    if probability <= 0.0:
        return _EPSILON
    return probability


def _sigmoid(value: float) -> float:
    if value >= 0:
        return 1.0 / (1.0 + math.exp(-value))
    exp_value = math.exp(value)
    return exp_value / (1.0 + exp_value)


def _nll(logits: Sequence[float], labels: Sequence[int], temperature: float) -> float:
    total = 0.0
    for logit, label in zip(logits, labels, strict=True):
        probability = _clip(_sigmoid(logit / temperature))
        total += -(label * math.log(probability) + (1 - label) * math.log(1 - probability))
    return total / len(labels)
