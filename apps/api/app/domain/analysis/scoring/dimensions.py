"""Explainable DNA dimension definitions.

Each dimension is composed of named indicators with fixed weights. Indicators
are fed normalized values in [0,1] plus an evidence-quality factor in [0,1].
The score and coverage follow the blueprint's general formula:

    score(d) = round(100 * sum(w*q*x) / sum(w*q))
    coverage(d) = sum(w*q) / sum(w)
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ....config.constants import (
    COVERAGE_HIGH,
    COVERAGE_INSUFFICIENT,
    COVERAGE_LOW,
    COVERAGE_MODERATE,
)

MODEL_VERSION = "dna-core-1.0"
MIN_COVERAGE_FOR_SCORE = COVERAGE_INSUFFICIENT

# Single source of truth for band boundaries lives in config/constants and is
# what /api/methodology serves. Semantics are "below the threshold", matching
# the methodology contract: coverage exactly 0.35 is scorable and therefore
# "low", not "insufficient".
COVERAGE_LABELS = [
    (COVERAGE_INSUFFICIENT, "insufficient"),
    (COVERAGE_LOW, "low"),
    (COVERAGE_MODERATE, "moderate"),
    (COVERAGE_HIGH, "high"),
]


def confidence_for_coverage(coverage: float) -> str:
    for threshold, label in COVERAGE_LABELS:
        if coverage < threshold:
            return label
    return "high"


@dataclass(frozen=True)
class Indicator:
    key: str
    weight: float
    direction: str = "higher_is_better"  # or lower_is_better


@dataclass(frozen=True)
class DimensionDef:
    key: str
    name: str
    direction: str
    description: str
    indicators: list[Indicator] = field(default_factory=list)

    @property
    def weights(self) -> dict[str, float]:
        return {i.key: i.weight for i in self.indicators}


DIMENSIONS: dict[str, DimensionDef] = {}


def _dim(d: DimensionDef) -> None:
    DIMENSIONS[d.key] = d


_dim(DimensionDef(
    key="technical_complexity",
    name="Technical Complexity",
    direction="descriptive",
    description="The number and interaction of technical elements. Descriptive, not a quality judgement.",
    indicators=[
        Indicator("structural_breadth", 0.20),
        Indicator("dependency_breadth", 0.20),
        Indicator("integration_breadth", 0.20),
        Indicator("change_coupling", 0.20),
        Indicator("lang_config_heterogeneity", 0.20),
    ],
))

_dim(DimensionDef(
    key="maintainability",
    name="Maintainability",
    direction="higher_is_better",
    description="Ease of understanding and changing the codebase safely.",
    indicators=[
        Indicator("hotspot_dispersion", 0.25),
        Indicator("file_size_health", 0.15),
        Indicator("change_coupling_inverse", 0.20),
        Indicator("test_maturity", 0.20),
        Indicator("documentation_quality", 0.20),
    ],
))

_dim(DimensionDef(
    key="testing_maturity",
    name="Testing Maturity",
    direction="higher_is_better",
    description="Presence of tests, CI test execution, and test breadth. Not a claim about actual coverage.",
    indicators=[
        Indicator("test_file_ratio", 0.25),
        Indicator("ci_test_execution", 0.25),
        Indicator("test_breadth", 0.20),
        Indicator("test_recency", 0.15),
        Indicator("trusted_coverage_artifact", 0.15),
    ],
))

_dim(DimensionDef(
    key="documentation_quality",
    name="Documentation Quality",
    direction="higher_is_better",
    description="Quality of README, setup, architecture, API, and governance documentation.",
    indicators=[
        Indicator("readme_completeness", 0.30),
        Indicator("setup_reproducibility", 0.20),
        Indicator("architecture_decision_docs", 0.20),
        Indicator("api_user_docs", 0.15),
        Indicator("governance_docs", 0.15),
    ],
))

_dim(DimensionDef(
    key="evolution_health",
    name="Evolution Health",
    direction="higher_is_better",
    description="Quality of project history: traceable change units, releases, controlled change size, rationale, and follow-up.",
    indicators=[
        Indicator("traceable_change_units", 0.25),
        Indicator("release_version_evidence", 0.20),
        Indicator("controlled_change_size", 0.20),
        Indicator("rationale_preservation", 0.20),
        Indicator("outcome_followup", 0.15),
    ],
))

_dim(DimensionDef(
    key="delivery_readiness",
    name="Delivery Readiness",
    direction="higher_is_better",
    description="Signals for automated checks, environment separation, reproducible dependencies, deployment, and release/rollback.",
    indicators=[
        Indicator("automated_checks", 0.25),
        Indicator("env_config_separation", 0.20),
        Indicator("reproducible_dependency_state", 0.20),
        Indicator("deployment_definition", 0.20),
        Indicator("release_rollback_evidence", 0.15),
    ],
))

_dim(DimensionDef(
    key="scalability_readiness",
    name="Scalability Readiness",
    direction="higher_is_better",
    description="Readiness signals for separation of concerns, data discipline, statelessness, async mechanisms, and observability. Not a production-capacity claim.",
    indicators=[
        Indicator("separation_of_concerns", 0.25),
        Indicator("persistent_data_discipline", 0.20),
        Indicator("stateless_configurable_services", 0.20),
        Indicator("async_cache_batch", 0.15),
        Indicator("observability_load_evidence", 0.20),
    ],
))

_dim(DimensionDef(
    key="technical_debt_risk",
    name="Technical Debt Risk",
    direction="lower_is_better",
    description="Risk signals from hotspots, rework, test gaps, debt markers, doc gaps, and dependency/config risk.",
    indicators=[
        Indicator("hotspot_concentration", 0.25),
        Indicator("rework_revert_signal", 0.20),
        Indicator("test_gap", 0.20),
        Indicator("todo_fixme_density", 0.10),
        Indicator("documentation_gap", 0.10),
        Indicator("dependency_config_risk", 0.15),
    ],
))

DIMENSION_ORDER = [
    "technical_complexity",
    "maintainability",
    "testing_maturity",
    "documentation_quality",
    "evolution_health",
    "delivery_readiness",
    "scalability_readiness",
    "technical_debt_risk",
]


def dimension(key: str) -> DimensionDef:
    return DIMENSIONS[key]


def all_dimensions() -> list[DimensionDef]:
    return [DIMENSIONS[k] for k in DIMENSION_ORDER]
