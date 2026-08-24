"""Pure alert-evaluation logic for the DNA trends & alerts feature.

This module is deterministic and side-effect free: given the scores produced
for a snapshot and the project's alert rules, it returns the crossings that
should be persisted. The worker (or any caller) owns the DB transaction and
idempotency via the (rule_id, snapshot_id) unique constraint.
"""

from __future__ import annotations

from typing import NamedTuple


class ScoreSnapshot(NamedTuple):
    """Minimal score shape needed for evaluation."""

    dimension: str
    score: int | None
    coverage: float


class RuleSpec(NamedTuple):
    """Minimal alert-rule shape needed for evaluation."""

    id: str
    dimension: str
    operator: str  # 'lt' | 'gt'
    threshold: int
    enabled: bool


class AlertDecision(NamedTuple):
    """A crossing to persist, or None if nothing should fire."""

    rule_id: str
    dimension: str
    old_value: int | None
    new_value: int | None


# Coverage below which a dimension is never scored (see ADR-001).
MIN_ALERT_COVERAGE: float = 0.35


def evaluate_scores(
    rules: list[RuleSpec],
    scores: list[ScoreSnapshot],
    history: dict[str, int] | None = None,
) -> list[AlertDecision]:
    """Return the rule crossings that fire for this snapshot.

    Regression-crossing semantics (see spec section 1.3): an alert fires only
    when a score **moves across** the threshold relative to the previous
    comparable score, so a dimension that stays bad does not re-fire on every
    snapshot.

    - Only enabled rules are considered.
    - Dimensions with `coverage < MIN_ALERT_COVERAGE` (or a null score) are
      skipped: we never alert on withheld scores.
    - `history` maps dimension -> previous comparable score. When it is absent
      (or the dimension has no previous score) nothing fires: a baseline is
      required to detect a regression.
    - `lt`: fires when the score **crosses below** the threshold — previous
      score at/above threshold and new score strictly below.
    - `gt`: fires when the score **crosses above** the threshold — previous
      score at/below threshold and new score strictly above.
    - A dimension already on the alert side that stays there is NOT a crossing
      and does not re-fire.
    - Each (rule, snapshot) pair produces at most one decision; dedupe on rule id.
    """
    history = history or {}
    score_by_dim = {s.dimension: s for s in scores if s.score is not None and s.coverage >= MIN_ALERT_COVERAGE}
    decisions: list[AlertDecision] = []
    seen_rules: set[str] = set()
    for rule in rules:
        if not rule.enabled or rule.id in seen_rules:
            continue
        score = score_by_dim.get(rule.dimension)
        if score is None or rule.dimension not in history:
            continue
        old = history[rule.dimension]
        new = score.score
        crossed = False
        if rule.operator == "lt":
            crossed = old >= rule.threshold and new < rule.threshold
        elif rule.operator == "gt":
            crossed = old <= rule.threshold and new > rule.threshold
        if crossed:
            decisions.append(
                AlertDecision(rule_id=rule.id, dimension=rule.dimension, old_value=old, new_value=new)
            )
            seen_rules.add(rule.id)
    return decisions


def previous_score(
    rules: list[RuleSpec], scores: list[ScoreSnapshot], history: dict[str, int]
) -> list[AlertDecision]:
    """Compatibility wrapper: evaluate crossing alerts with an explicit history."""
    return evaluate_scores(rules, scores, history)