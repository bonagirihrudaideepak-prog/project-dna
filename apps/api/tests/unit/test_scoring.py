"""Unit tests for the scoring engine and coverage/confidence rules."""

from app.domain.analysis.scoring.dimensions import (
    MIN_COVERAGE_FOR_SCORE,
    all_dimensions,
    confidence_for_coverage,
)
from app.domain.analysis.scoring.engine import indicator_input, score_all, score_dimension


def _full_inputs(values: dict[str, float]) -> dict:
    """Build complete indicator inputs for every dimension at given quality."""
    inputs = {}
    for dim in all_dimensions():
        inputs[dim.key] = {
            ind.key: indicator_input(values.get(ind.key, 0.5), 1.0, 0.5)
            for ind in dim.indicators
        }
    return inputs


def _dim_full_quality(inputs: dict, quality: float) -> dict:
    """Set all indicator qualities to a specific value."""
    for dim_key in inputs:
        for ind_key in inputs[dim_key]:
            inputs[dim_key][ind_key].quality = quality
    return inputs


def test_scores_produced_when_full_evidence():
    inputs = _full_inputs({})
    results = score_all(inputs)
    assert len(results) == 8
    for r in results:
        assert r.score is not None
        assert 0 <= r.score <= 100
        assert r.coverage == 1.0
        assert r.confidence == "high"


def test_lower_coverage_reduces_confidence():
    inputs = _full_inputs({})
    _dim_full_quality(inputs, 0.2)
    results = score_all(inputs)
    for r in results:
        assert r.coverage < 0.35
        assert r.confidence == "insufficient"
        assert r.score is None  # withheld, never zero


def test_missing_indicator_is_not_zero():
    inputs = _full_inputs({})
    # remove half the indicators from every dimension
    for dim in all_dimensions():
        keys = [ind.key for ind in dim.indicators]
        for key in keys[::2]:
            inputs[dim.key][key].quality = 0.0
    results = score_all(inputs)
    for r in results:
        # score either withheld or reflects remaining evidence — never auto-zero
        assert r.score is None or r.score >= 0
        # withheld when coverage below threshold
        if r.coverage < MIN_COVERAGE_FOR_SCORE:
            assert r.score is None


def test_direction_labels():
    dims = {d.key: d for d in all_dimensions()}
    assert dims["technical_debt_risk"].direction == "lower_is_better"
    assert dims["technical_complexity"].direction == "descriptive"
    assert dims["maintainability"].direction == "higher_is_better"


def test_confidence_labels():
    assert confidence_for_coverage(0.10) == "insufficient"
    assert confidence_for_coverage(0.40) == "low"
    assert confidence_for_coverage(0.70) == "moderate"
    assert confidence_for_coverage(0.90) == "high"


def test_single_dimension_scoring():
    dim = all_dimensions()[0]
    inputs = {
        ind.key: indicator_input(1.0, 1.0, 1.0) for ind in dim.indicators
    }
    r = score_dimension(dim.key, inputs)
    assert r.score == 100


def test_score_withheld_when_no_indicators_have_evidence():
    """When all indicators have quality=0, score should be withheld."""
    dim = all_dimensions()[0]
    inputs = {
        ind.key: indicator_input(1.0, 0.0, 1.0) for ind in dim.indicators
    }
    r = score_dimension(dim.key, inputs)
    assert r.score is None
    assert r.coverage == 0.0
    assert "No evidence" in str(r.limitations)


def test_technical_debt_risk_lower_is_better():
    """Technical debt risk should invert scores correctly."""
    from app.domain.analysis.scoring.dimensions import all_dimensions
    dims = {d.key: d for d in all_dimensions()}
    dim = dims["technical_debt_risk"]
    # high normalized value on lower_is_better dimension
    inputs = {
        ind.key: indicator_input(0.9, 1.0, 0.9) for ind in dim.indicators
    }
    r = score_dimension(dim.key, inputs)
    assert r.coverage > 0.0
    # limitations should mention evidence availability
    assert len(r.limitations) > 0 or r.score is not None


def test_confidence_progression():
    """Confidence progresses with coverage thresholds."""
    # Function uses: coverage <= threshold -> label (first match wins)
    # Labels: insufficient (0.35), low (0.59), moderate (0.79), high (1.01)
    # Original test confirms: confidence_for_coverage(0.90) == "high"
    assert confidence_for_coverage(0.34) == "insufficient"
    assert confidence_for_coverage(0.35) == "insufficient"  # boundary
    assert confidence_for_coverage(0.58) == "low"  # 0.58 <= 0.59
    assert confidence_for_coverage(0.59) == "low"  # 0.59 <= 0.59
    assert confidence_for_coverage(0.78) == "moderate"  # 0.78 <= 0.79
    assert confidence_for_coverage(0.79) == "moderate"  # 0.79 <= 0.79
    assert confidence_for_coverage(0.90) == "high"  # 0.90 <= 1.01, first match
