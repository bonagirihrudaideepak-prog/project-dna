"""Evidence-weighted DNA scoring engine.

Takes computed metric raw values and maps them to the normalized indicator
inputs for each dimension, then applies the general formula.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .dimensions import (
    MIN_COVERAGE_FOR_SCORE,
    MODEL_VERSION,
    all_dimensions,
    confidence_for_coverage,
)
from .normalize import clamp01


@dataclass
class IndicatorInput:
    normalized_value: float
    quality: float
    raw: Any
    evidence_ids: list[str] = field(default_factory=list)


@dataclass
class ScoredDimension:
    dimension: str
    score: int | None
    coverage: float
    confidence: str
    direction: str
    model_version: str
    indicators: dict[str, IndicatorInput]
    limitations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension,
            "score": self.score,
            "coverage": round(self.coverage, 3),
            "confidence": self.confidence,
            "direction": self.direction,
            "model_version": self.model_version,
            "indicators": [
                {
                    "key": k,
                    "raw_value": v.raw,
                    "normalized_value": round(v.normalized_value, 3),
                    "quality": round(v.quality, 3),
                    "evidence_ids": v.evidence_ids[:20],
                }
                for k, v in self.indicators.items()
            ],
            "limitations": self.limitations,
        }


def _available(indicator_inputs: dict[str, IndicatorInput], key: str) -> bool:
    return key in indicator_inputs and indicator_inputs[key].quality > 0.001


def score_dimension(
    dimension_key: str,
    indicator_inputs: dict[str, IndicatorInput],
) -> ScoredDimension:
    from .dimensions import DIMENSIONS

    dim = DIMENSIONS[dimension_key]
    total_w = sum(ind.weight for ind in dim.indicators)
    total_wq = 0.0
    weighted_sum = 0.0
    available_count = 0
    for ind in dim.indicators:
        if _available(indicator_inputs, ind.key):
            inp = indicator_inputs[ind.key]
            wq = ind.weight * inp.quality
            total_wq += wq
            weighted_sum += wq * inp.normalized_value
            available_count += 1
    coverage = total_wq / total_w if total_w > 0 else 0.0
    score = (
        round(100 * weighted_sum / total_wq)
        if total_wq > 0 and coverage >= MIN_COVERAGE_FOR_SCORE
        else None
    )
    limitations = []
    for ind in dim.indicators:
        if not _available(indicator_inputs, ind.key):
            limitations.append(f"No evidence for indicator '{ind.key}'")
    # If no indicators have evidence, mark all as lacking evidence
    if available_count == 0 and total_w > 0:
        limitations = [f"No evidence for indicator '{ind.key}'" for ind in dim.indicators]
    return ScoredDimension(
        dimension=dimension_key,
        score=score,
        coverage=coverage,
        confidence=confidence_for_coverage(coverage),
        direction=dim.direction,
        model_version=MODEL_VERSION,
        indicators=indicator_inputs,
        limitations=limitations,
    )


def score_all(indicator_inputs: dict[str, dict[str, IndicatorInput]]) -> list[ScoredDimension]:
    return [score_dimension(dim.key, indicator_inputs[dim.key]) for dim in all_dimensions()]


def indicator_input(normalized_value: float, quality: float, raw: Any, evidence: list[str] | None = None) -> IndicatorInput:
    return IndicatorInput(
        normalized_value=clamp01(normalized_value),
        quality=clamp01(quality),
        raw=raw,
        evidence_ids=evidence or [],
    )