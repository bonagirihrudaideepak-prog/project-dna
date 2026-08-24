"""Unit tests for project similarity."""

from app.application.similarity import model_compatible, weighted_distance


def _scores(coverage=0.8):
    keys = [
        "technical_complexity", "maintainability", "testing_maturity",
        "documentation_quality", "evolution_health", "delivery_readiness",
        "scalability_readiness", "technical_debt_risk",
    ]
    return {k: {"score": 50, "coverage": coverage, "confidence": "moderate"} for k in keys}


def test_identical_snapshots_high_similarity():
    a = _scores()
    b = _scores()
    r = weighted_distance(a, b)
    assert r["similarity"] == 100
    assert r["distance"] == 0.0
    assert len(r["used_dimensions"]) == 8


def test_low_coverage_excluded():
    a = _scores(0.8)
    b = _scores(0.4)  # below threshold
    r = weighted_distance(a, b)
    assert r["similarity"] is None
    assert len(r["used_dimensions"]) == 0
    assert len(r["excluded_dimensions"]) == 8


def test_adverse_dimension_inverted_consistently():
    # identical raw scores on an adverse dim must yield equal inverted values
    a = _scores()
    b = _scores()
    a["technical_debt_risk"] = {"score": 20, "coverage": 0.9, "confidence": "high"}
    b["technical_debt_risk"] = {"score": 20, "coverage": 0.9, "confidence": "high"}
    r = weighted_distance(a, b)
    assert r["similarity"] == 100


def test_adverse_dimension_difference_reduces_similarity():
    a = _scores()
    b = _scores()
    a["technical_debt_risk"] = {"score": 20, "coverage": 0.9, "confidence": "high"}
    b["technical_debt_risk"] = {"score": 80, "coverage": 0.9, "confidence": "high"}
    r = weighted_distance(a, b)
    assert r["similarity"] == 92  # 1 of 8 dims differs by 60 after inversion: 100*(1-0.075)
    debt = next(d for d in r["per_dimension"] if d["dimension"] == "technical_debt_risk")
    assert debt["a"] == 80
    assert debt["b"] == 20


def test_model_compatibility():
    assert model_compatible("dna-core-1.0", "dna-core-1.0")
    assert not model_compatible("dna-core-1.0", "dna-core-2.0")
