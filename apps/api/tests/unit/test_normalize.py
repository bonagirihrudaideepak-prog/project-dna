"""Unit tests for normalization helpers."""

from app.analysis.scoring.normalize import (
    boolean,
    capped_ratio,
    clamp01,
    inverted,
    inverse_weighted,
    linear,
    log_scale,
)


def test_clamp01():
    assert clamp01(-1) == 0.0
    assert clamp01(0.5) == 0.5
    assert clamp01(2) == 1.0


def test_linear_mapping():
    assert linear(0, 0, 100) == 0.0
    assert linear(50, 0, 100) == 0.5
    assert linear(150, 0, 100) == 1.0
    assert linear(-10, 0, 100) == 0.0


def test_capped_ratio_zero_denominator():
    assert capped_ratio(5, 0) == 0.0
    assert capped_ratio(10, 20) == 0.5
    assert capped_ratio(30, 20) == 1.0


def test_log_scale():
    assert log_scale(0, 10) == 0.0
    assert 0 < log_scale(1, 10) < 1.0
    assert log_scale(10, 10) == 1.0


def test_inverted_and_boolean():
    assert inverted(0.2) == 0.8
    assert boolean(True) == 1.0
    assert boolean(False) == 0.0


def test_inverse_weighted():
    assert inverse_weighted(0, 10) == 1.0
    assert inverse_weighted(5, 10) == 0.5
    assert inverse_weighted(0, 0) == 1.0
