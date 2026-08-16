# Scoring Methodology — dna-core-1.0

Each snapshot produces a **Project DNA Profile**: 8 dimensions scored on
evidence available in the repository snapshot (files, commits, PRs, releases,
issues, manifests, CI config). Scores are explainable: every indicator stores
its raw value, normalized value, evidence quality, and the evidence IDs that
contributed.

## Formula

For dimension `d` with indicators `i` (weight `wᵢ`, normalized value `xᵢ`,
evidence quality `qᵢ`):

```
score(d)  = round(100 · Σ(wᵢ·qᵢ·xᵢ) / Σ(wᵢ·qᵢ))
coverage(d) = Σ(wᵢ·qᵢ) / Σ(wᵢ)
```

- **Withheld:** `score = null` when `coverage < 0.35`. Missing evidence never
  produces a 0 score.
- **Confidence:** `insufficient` (<0.35), `low` (<0.60), `moderate` (<0.80),
  `high` (≥0.80).

## Dimensions and indicators

### technical_complexity — *descriptive*

| indicator | weight | meaning |
|---|---|---|
| structural_breadth | 0.20 | distinct components/domains present |
| dependency_breadth | 0.20 | distinct runtime/dev dependency families |
| integration_breadth | 0.20 | number of integration surfaces (APIs, DB, cache, queues) |
| change_coupling | 0.20 | files frequently changed together |
| lang_config_heterogeneity | 0.20 | spread across languages and build/config systems |

### maintainability — *higher is better*

| indicator | weight | meaning |
|---|---|---|
| hotspot_dispersion | 0.25 | churn/fix concentration not locked into few files |
| file_size_health | 0.15 | reasonable file sizes |
| change_coupling_inverse | 0.20 | low coupling (inverted) |
| test_maturity | 0.20 | tests exist and are exercised |
| documentation_quality | 0.20 | docs for setup/architecture/API |

### testing_maturity — *higher is better*

| indicator | weight | meaning |
|---|---|---|
| test_file_ratio | 0.25 | tests relative to source files |
| ci_test_execution | 0.25 | CI workflows run tests |
| test_breadth | 0.20 | tests across domains (unit/integration/e2e) |
| test_recency | 0.15 | tests touched recently |
| trusted_coverage_artifact | 0.15 | coverage report artifact present |

### documentation_quality — *higher is better*

| indicator | weight | meaning |
|---|---|---|
| readme_completeness | 0.30 | README has purpose/setup/usage sections |
| setup_reproducibility | 0.20 | install/build commands documented |
| architecture_decision_docs | 0.20 | ADRs or equivalent |
| api_user_docs | 0.15 | API/usage docs |
| governance_docs | 0.15 | contributing/licensing/code of conduct |

### evolution_health — *higher is better*

| indicator | weight | meaning |
|---|---|---|
| traceable_change_units | 0.25 | commits reference issues/PRs/decisions |
| release_version_evidence | 0.20 | tags/releases with versions |
| controlled_change_size | 0.20 | commits/changes stay small |
| rationale_preservation | 0.20 | commit messages / decision records explain why |
| outcome_followup | 0.15 | decision outcomes reviewed later |

### delivery_readiness — *higher is better*

| indicator | weight | meaning |
|---|---|---|
| automated_checks | 0.25 | CI checks beyond build |
| env_config_separation | 0.20 | env/config separated from code |
| reproducible_dependency_state | 0.20 | lockfiles / pinned deps |
| deployment_definition | 0.20 | deploy pipeline/config present |
| release_rollback_evidence | 0.15 | releases + rollback signals |

### scalability_readiness — *higher is better*

| indicator | weight | meaning |
|---|---|---|
| separation_of_concerns | 0.25 | layered/modular structure |
| persistent_data_discipline | 0.20 | schema/migrations managed |
| stateless_configurable_services | 0.20 | services config-driven |
| async_cache_batch | 0.15 | async/queue/cache usage |
| observability_load_evidence | 0.20 | logging/metrics/tracing under load |

### technical_debt_risk — *lower is better*

| indicator | weight | meaning |
|---|---|---|
| hotspot_concentration | 0.25 | churn/fix burden concentrated |
| rework_revert_signal | 0.20 | reverted/redone work |
| test_gap | 0.20 | source files without tests |
| todo_fixme_density | 0.10 | unfinished markers |
| documentation_gap | 0.10 | code without docs |
| dependency_config_risk | 0.15 | risky deps/config |

## Similarity across snapshots

`weighted_distance(a, b)`:

- Only dimensions where **both** snapshots have `coverage ≥ 0.60` count.
- `lower_is_better` dimensions are inverted (`100 - score`) so orientation is
  consistent.
- `distance = Σ w·|aᵢ−bᵢ| / (100 · Σ w)`; `similarity = 100·(1−distance)`.

## Provenance & confidence

Every timeline event and indicator carries a provenance:

- `observed` — exact data (release, merged PR, closed issue).
- `rule-derived` — derived by transparent rules (commit clusters, dependency
  manifest changes).
- `suggested` — candidate events awaiting user confirmation.
- `user` / `user-confirmed` — knowledge the user added (decisions, experiments,
  outcome reviews).

## Limits

Scores are **signals about evidence in the snapshot**, not guarantees about the
running system. `technical_complexity` is descriptive; `scalability_readiness`
indicates readiness signals, not production capacity.