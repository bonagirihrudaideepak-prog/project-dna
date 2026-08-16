# ADR-001: DNA Core Model — Evidence-Weighted 8-Dimension Scoring

Status: Accepted (MVP)

Date: 2026-08-14

## Context

We need a way to summarize a repository's qualities into a compact, explainable
profile without overclaiming. Repos vary wildly in size and activity, so any
score must be honest about how much evidence it is based on.

## Decision

Adopt the **dna-core-1.0** model: eight named dimensions, each composed of
weighted indicators.

- Each indicator receives a normalized value `x ∈ [0,1]` and an evidence
  quality factor `q ∈ [0,1]`.
- Per dimension `d`:

  ```
  score(d)  = round(100 · Σ(wᵢ·qᵢ·xᵢ) / Σ(wᵢ·qᵢ))
  coverage(d) = Σ(wᵢ·qᵢ) / Σ(wᵢ)
  ```

- A dimension score is **withheld (null)** when `coverage < 0.35` — never
  reported as zero. Confidence label from coverage:
  `insufficient < 0.35`, `low < 0.60`, `moderate < 0.80`, `high ≥ 0.80`.
- Direction semantics: `higher_is_better`, `lower_is_better`
  (e.g. `technical_debt_risk`), `descriptive` (e.g. `technical_complexity`).

## Why

1. **Explainability.** Every score decomposes into named indicators with
   weights, raw values, and evidence IDs.
2. **Honesty.** Coverage + confidence prevent a thin snapshot from looking
   authoritative.
3. **Comparability.** Cross-snapshot similarity only uses dimensions where both
   sides reach `coverage ≥ 0.60` (`MIN_COMPARABLE_COVERAGE`).

## Alternatives considered

- Single weighted sum of ~40 raw metrics — loses explainability, overclaims.
- Full Bayesian model — overkill for the MVP data volume.
- LLM-judged scores — not reproducible, not grounded in evidence.

## Consequences

- Users see null scores for evidence-thin repos (a feature, not a bug).
- Adding a dimension requires updating `dimensions.py`, the pipeline mapping,
  and the UI label map (`DIMENSION_LABELS` in the web app).
- The model version string is stored on every snapshot, enabling model
  migrations and guarded cross-version comparisons.