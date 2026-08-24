from app.domain.analysis.alerts import (
    RuleSpec,
    ScoreSnapshot,
    evaluate_scores,
    previous_score,
)


def _rule(rid: str, dimension: str, operator: str, threshold: int, enabled: bool = True) -> RuleSpec:
    return RuleSpec(id=rid, dimension=dimension, operator=operator, threshold=threshold, enabled=enabled)


def test_no_rules_returns_empty():
    assert evaluate_scores([], [ScoreSnapshot("maintainability", 70, 0.9)]) == []


def test_lt_crossing_fires():
    rules = [_rule("r1", "maintainability", "lt", 50)]
    scores = [ScoreSnapshot("maintainability", 40, 0.9)]
    decisions = evaluate_scores(rules, scores, history={"maintainability": 65})
    assert len(decisions) == 1
    assert decisions[0].rule_id == "r1"
    assert decisions[0].new_value == 40
    assert decisions[0].old_value == 65


def test_gt_crossing_fires():
    rules = [_rule("r2", "technical_debt_risk", "gt", 70)]
    scores = [ScoreSnapshot("technical_debt_risk", 85, 0.9)]
    decisions = evaluate_scores(rules, scores, history={"technical_debt_risk": 60})
    assert len(decisions) == 1
    assert decisions[0].rule_id == "r2"
    assert decisions[0].old_value == 60


def test_boundary_not_crossed():
    rules = [_rule("r1", "maintainability", "lt", 50)]
    assert evaluate_scores(rules, [ScoreSnapshot("maintainability", 50, 0.9)], history={"maintainability": 65}) == []
    rules = [_rule("r2", "technical_debt_risk", "gt", 70)]
    assert evaluate_scores(rules, [ScoreSnapshot("technical_debt_risk", 70, 0.9)], history={"technical_debt_risk": 60}) == []


def test_disabled_rule_skipped():
    rules = [_rule("r1", "maintainability", "lt", 50, enabled=False)]
    assert evaluate_scores(rules, [ScoreSnapshot("maintainability", 10, 0.9)], history={"maintainability": 65}) == []


def test_withheld_score_skipped():
    rules = [_rule("r1", "maintainability", "lt", 50)]
    assert evaluate_scores(rules, [ScoreSnapshot("maintainability", 10, 0.2)], history={"maintainability": 65}) == []
    assert evaluate_scores(rules, [ScoreSnapshot("maintainability", None, 0.9)], history={"maintainability": 65}) == []


def test_no_history_no_fire():
    # A baseline is required to detect a regression; without history nothing fires.
    rules = [_rule("r1", "maintainability", "lt", 50)]
    assert evaluate_scores(rules, [ScoreSnapshot("maintainability", 30, 0.9)]) == []


def test_already_bad_no_refire():
    # Score stays below the threshold but did not move: no re-fire (not a crossing).
    rules = [_rule("r1", "maintainability", "lt", 50)]
    scores = [ScoreSnapshot("maintainability", 30, 0.9)]
    assert evaluate_scores(rules, scores, history={"maintainability": 35}) == []


def test_dedupe_per_rule():
    rules = [
        _rule("r1", "maintainability", "lt", 50),
        _rule("r1", "maintainability", "lt", 50),
    ]
    scores = [ScoreSnapshot("maintainability", 30, 0.9)]
    assert len(evaluate_scores(rules, scores, history={"maintainability": 65})) == 1


def test_previous_score_fills_old_value():
    rules = [_rule("r1", "maintainability", "lt", 50)]
    scores = [ScoreSnapshot("maintainability", 40, 0.9)]
    decisions = previous_score(rules, scores, {"maintainability": 65})
    assert decisions[0].old_value == 65
    assert decisions[0].new_value == 40