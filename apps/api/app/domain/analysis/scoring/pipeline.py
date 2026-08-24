"""Analysis pipeline: converts inspection + artifact data into indicators and
scores for all eight dimensions. Deterministic and reproducible.

Structure: ``build_indicator_inputs`` computes raw metric signals once, then
delegates to one private builder per dimension. Normalization thresholds are
named constants below so the scoring model stays auditable (ADR-001).
"""

from __future__ import annotations

from typing import Any

from ..extractors import metrics  # noqa: F401 - re-exported for callers/tests
from ..inspector import InspectionResult
from .engine import indicator_input, score_all

# ── Normalization thresholds (indicator raw value -> [0,1]) ────────────────
_DIRS_FOR_FULL_BREADTH = 40.0
_DEPS_FOR_FULL_BREADTH = 80.0
_INTEGRATIONS_FOR_FULL_BREADTH = 25.0
_MAX_COUPLING_FOR_FULL_BREADTH = 30.0
_LANGS_FOR_FULL_BREADTH = 15.0
_REPO_FILES_FOR_FULL_RICHNESS = 50.0

_TEST_RATIO_FULL_CREDIT = 3.0  # ratio * 3 -> 1.0 (one test file per three source files)
_TEST_BREADTH_KINDS = 3.0
_README_SECTIONS_FULL = 5.0
_ADRS_FULL = 3.0
_SETUP_SIGNALS_FULL = 3.0
_LOCKFILES_FULL = 2.0
_ENV_TEMPLATES_FULL = 2.0
_CONCERNS_FULL = 4.0
_MIGRATIONS_FULL = 5.0
_ASYNC_FILES_FULL = 5.0
_OBS_FILES_FULL = 3.0
_DOCS_FILES_FOR_NO_GAP = 8.0
_TODO_MARKERS_CAP = 30.0
_LARGE_CHANGE_LINES = 1000
_CHANGE_FRACTION_TOLERATED = 0.1
_RELEASES_FOR_VERSION_EVIDENCE = 2
_DECISIONS_FULL_CREDIT = 5.0
_FOLLOWUPS_FULL_CREDIT = 5.0

# Placeholder indicators: not computable from current evidence sources.
# Per the coverage-honesty rule they carry ZERO evidence-quality, so they add
# nothing to the weighted score until a real signal exists. Replacing them
# with measured signals must go through ADR review because it changes scores.
_PLACEHOLDER_TEST_RECENCY = (0.0, 0.0)
_PLACEHOLDER_ROLLBACK = (0.5, None)  # value grounded in release evidence; quality computed
_PLACEHOLDER_REWORK = (0.0, 0.0)
_PLACEHOLDER_DEP_CONFIG = (0.0, 0.0)

_QF_COUNT_BASE = 0.7
_QF_COUNT_SPAN = 0.3
_QF_COUNT_SATURATION = 10.0
_QF_RICHNESS_BASE = 0.7
_QF_RICHNESS_SPAN = 0.3


def _links_issue(commit: dict, issue_numbers: set[Any]) -> bool:
    """True when a commit message references any known issue number."""
    body = (commit.get("metadata") or {}).get("message", "")[:200]
    return any(f"#{num}" in body for num in issue_numbers)


def _qf(repo_rich: float, evidence_count: float) -> float:
    """Evidence-quality factor: how much can we trust this indicator.

    Driven primarily by the presence of retrieved evidence; repository size
    only nudges the confidence slightly so small but well-documented repos are
    not unfairly withheld.
    """
    if evidence_count <= 0:
        return 0.0
    count_factor = min(1.0, _QF_COUNT_BASE + _QF_COUNT_SPAN * evidence_count / _QF_COUNT_SATURATION)
    richness = min(1.0, _QF_RICHNESS_BASE + _QF_RICHNESS_SPAN * repo_rich)
    return count_factor * richness


def _test_score(tests: dict) -> float:
    return min(
        1.0,
        min(1.0, tests.get("test_file_ratio", 0.0) * _TEST_RATIO_FULL_CREDIT) * 0.4
        + (1.0 if tests.get("has_ci_test") else 0.0) * 0.3
        + min(1.0, len(tests.get("test_breadth", set())) / _TEST_BREADTH_KINDS) * 0.3,
    )


def _doc_score(docs: dict) -> float:
    return min(1.0, docs.get("readme_sections", 0) / _README_SECTIONS_FULL)


def _complexity_inputs(ctx: dict[str, Any]) -> dict[str, Any]:
    structural, deps, integration = ctx["structural"], ctx["deps"], ctx["integration"]
    coupling, heterogeneity, repo_rich = ctx["coupling"], ctx["heterogeneity"], ctx["repo_rich"]
    return {
        "structural_breadth": indicator_input(
            min(1.0, structural["dirs"] / _DIRS_FOR_FULL_BREADTH), _qf(repo_rich, structural["dirs"]),
            structural["raw_value"], structural["evidence"],
        ),
        "dependency_breadth": indicator_input(
            min(1.0, deps["dependencies"] / _DEPS_FOR_FULL_BREADTH), _qf(repo_rich, deps["dependencies"]),
            deps["raw_value"], deps["evidence"],
        ),
        "integration_breadth": indicator_input(
            min(1.0, integration["raw_value"] / _INTEGRATIONS_FOR_FULL_BREADTH), _qf(repo_rich, integration["raw_value"]),
            integration["raw_value"], integration["evidence"],
        ),
        "change_coupling": indicator_input(
            min(1.0, coupling["max_coupling"] / _MAX_COUPLING_FOR_FULL_BREADTH), _qf(repo_rich, coupling["max_coupling"]),
            coupling["raw_value"], coupling["evidence"],
        ),
        "lang_config_heterogeneity": indicator_input(
            min(1.0, heterogeneity["raw_value"] / _LANGS_FOR_FULL_BREADTH), _qf(repo_rich, heterogeneity["raw_value"]),
            heterogeneity["raw_value"], heterogeneity["evidence"],
        ),
    }


def _maintainability_inputs(ctx: dict[str, Any]) -> dict[str, Any]:
    churn, coupling, file_size = ctx["churn"], ctx["coupling"], ctx["file_size"]
    tests, docs, repo_rich = ctx["tests"], ctx["docs"], ctx["repo_rich"]
    hotspot_dispersion = 1.0 - (churn["concentration"] if churn else 0.0)
    coupling_inverse = (
        1.0 - min(1.0, coupling["avg_coupling"] / max(1, coupling["max_coupling"]))
        if coupling.get("max_coupling") else 1.0
    )
    return {
        "hotspot_dispersion": indicator_input(
            hotspot_dispersion, _qf(repo_rich, churn.get("total_churn", 0)),
            churn.get("concentration", 0.0), churn.get("evidence", []),
        ),
        "file_size_health": indicator_input(
            file_size["raw_value"], _qf(repo_rich, file_size.get("total", 0)),
            file_size["raw_value"], file_size.get("evidence", []),
        ),
        "change_coupling_inverse": indicator_input(
            coupling_inverse, _qf(repo_rich, coupling.get("max_coupling", 0)),
            coupling.get("avg_coupling", 0.0), coupling.get("evidence", []),
        ),
        "test_maturity": indicator_input(
            _test_score(tests), _qf(repo_rich, tests.get("test_files", 0)),
            tests.get("test_file_ratio", 0.0), tests.get("evidence", []),
        ),
        "documentation_quality": indicator_input(
            _doc_score(docs), _qf(repo_rich, docs.get("docs_files", 0)),
            docs.get("readme_sections", 0), docs.get("evidence", []),
        ),
    }


def _testing_inputs(ctx: dict[str, Any]) -> dict[str, Any]:
    tests, repo_rich = ctx["tests"], ctx["repo_rich"]
    value, quality = _PLACEHOLDER_TEST_RECENCY
    return {
        "test_file_ratio": indicator_input(
            min(1.0, tests["test_file_ratio"] * _TEST_RATIO_FULL_CREDIT), _qf(repo_rich, tests.get("test_files", 0)),
            tests.get("test_file_ratio", 0.0), tests.get("evidence", []),
        ),
        "ci_test_execution": indicator_input(
            1.0 if tests.get("has_ci_test") else 0.0, _qf(repo_rich, len(tests.get("evidence", []))),
            tests.get("has_ci_test"), tests.get("evidence", []),
        ),
        "test_breadth": indicator_input(
            min(1.0, len(tests.get("test_breadth", set())) / _TEST_BREADTH_KINDS), _qf(repo_rich, len(tests.get("test_breadth", set()))),
            list(tests.get("test_breadth", set())), tests.get("evidence", []),
        ),
        "test_recency": indicator_input(value, quality, "not computed", []),
        "trusted_coverage_artifact": indicator_input(0.0, 0.0, "none", []),
    }


def _documentation_inputs(ctx: dict[str, Any]) -> dict[str, Any]:
    docs, setup, repo_rich = ctx["docs"], ctx["setup"], ctx["repo_rich"]
    return {
        "readme_completeness": indicator_input(
            min(1.0, docs["readme_sections"] / _README_SECTIONS_FULL), _qf(repo_rich, docs.get("docs_files", 0)),
            docs.get("readme_sections", 0), docs.get("evidence", []),
        ),
        "setup_reproducibility": indicator_input(
            min(1.0, (setup["lockfiles"] + setup["env_templates"]) / _SETUP_SIGNALS_FULL), _qf(repo_rich, len(setup["evidence"])),
            {"lockfiles": setup["lockfiles"], "env_templates": setup["env_templates"]}, setup["evidence"],
        ),
        "architecture_decision_docs": indicator_input(
            min(1.0, docs["adrs"] / _ADRS_FULL), _qf(repo_rich, docs["adrs"]),
            docs["adrs"], docs["evidence"],
        ),
        "api_user_docs": indicator_input(0.0, 0.0, "not detected", []),
        "governance_docs": indicator_input(
            1.0 if setup["readme_present"] else 0.0,
            _qf(repo_rich, 1 if setup["readme_present"] else 0),
            setup["readme_present"], ["file:README" if setup["readme_present"] else ""],
        ),
    }


def _evolution_inputs(ctx: dict[str, Any]) -> dict[str, Any]:
    repo_rich = ctx["repo_rich"]
    traced, total_commits = ctx["traced"], ctx["total_commits"]
    has_releases, has_prs = ctx["has_releases"], ctx["has_prs"]
    large_changes, controlled_change = ctx["large_changes"], ctx["controlled_change"]
    rationale, followups = ctx["rationale"], ctx["followups"]
    release_urls = ctx["release_urls"]
    return {
        "traceable_change_units": indicator_input(
            traced / total_commits if total_commits else 0.0, _qf(repo_rich, total_commits),
            {"traced": traced, "total": total_commits}, [],
        ),
        "release_version_evidence": indicator_input(
            1.0 if has_releases else (0.4 if has_prs else 0.0), _qf(repo_rich, len(ctx["releases"])),
            {"releases": len(ctx["releases"]), "prs": len(ctx["prs"])}, release_urls,
        ),
        "controlled_change_size": indicator_input(
            controlled_change, _qf(repo_rich, len(ctx["file_changes"])),
            {"large_changes": large_changes}, [],
        ),
        "rationale_preservation": indicator_input(
            min(1.0, rationale / _DECISIONS_FULL_CREDIT), 0.0 if not rationale else 1.0,
            rationale, [],
        ),
        "outcome_followup": indicator_input(
            min(1.0, followups / _FOLLOWUPS_FULL_CREDIT), 0.0 if not followups else 1.0,
            followups, [],
        ),
    }


def _delivery_inputs(ctx: dict[str, Any]) -> dict[str, Any]:
    delivery, setup, repo_rich = ctx["delivery"], ctx["setup"], ctx["repo_rich"]
    checks = delivery.get("checks", {})
    value = _PLACEHOLDER_ROLLBACK[0]
    release_urls = ctx["release_urls"]
    return {
        "automated_checks": indicator_input(
            (sum(1 for c in checks.values() if c)) / 3.0, _qf(repo_rich, delivery.get("ci_files", 0)),
            checks, delivery.get("evidence", []),
        ),
        "env_config_separation": indicator_input(
            min(1.0, delivery.get("env_sep_files", 0) / _ENV_TEMPLATES_FULL), _qf(repo_rich, delivery.get("env_sep_files", 0)),
            delivery.get("env_sep_files", 0), delivery.get("evidence", []),
        ),
        "reproducible_dependency_state": indicator_input(
            min(1.0, setup["lockfiles"] / _LOCKFILES_FULL), _qf(repo_rich, setup["lockfiles"]),
            setup["lockfiles"], setup["evidence"],
        ),
        "deployment_definition": indicator_input(
            min(1.0, delivery.get("deploy_files", 0) / _ENV_TEMPLATES_FULL), _qf(repo_rich, delivery.get("deploy_files", 0)),
            delivery.get("deploy_files", 0), delivery.get("evidence", []),
        ),
        "release_rollback_evidence": indicator_input(
            value if ctx["has_releases"] else 0.0,
            _qf(repo_rich, len(ctx["releases"])) if ctx["has_releases"] else 0.0,
            {"releases": len(ctx["releases"])}, release_urls,
        ),
    }


def _scalability_inputs(ctx: dict[str, Any]) -> dict[str, Any]:
    scalability, setup, repo_rich = ctx["scalability"], ctx["setup"], ctx["repo_rich"]
    return {
        "separation_of_concerns": indicator_input(
            min(1.0, scalability["concerns"] / _CONCERNS_FULL), _qf(repo_rich, len(scalability.get("evidence", []))),
            scalability["concerns"], scalability.get("evidence", []),
        ),
        "persistent_data_discipline": indicator_input(
            min(1.0, scalability["migrations"] / _MIGRATIONS_FULL), _qf(repo_rich, scalability["migrations"]),
            scalability["migrations"], scalability.get("evidence", []),
        ),
        "stateless_configurable_services": indicator_input(
            min(1.0, setup["env_templates"] / _ENV_TEMPLATES_FULL), _qf(repo_rich, setup["env_templates"]),
            setup["env_templates"], setup["evidence"],
        ),
        "async_cache_batch": indicator_input(
            min(1.0, scalability["async_files"] / _ASYNC_FILES_FULL), _qf(repo_rich, scalability["async_files"]),
            scalability["async_files"], scalability.get("evidence", []),
        ),
        "observability_load_evidence": indicator_input(
            min(1.0, scalability["obs_files"] / _OBS_FILES_FULL), _qf(repo_rich, scalability["obs_files"]),
            scalability["obs_files"], scalability.get("evidence", []),
        ),
    }


def _debt_inputs(ctx: dict[str, Any]) -> dict[str, Any]:
    churn, tests, docs, debt_markers = ctx["churn"], ctx["tests"], ctx["docs"], ctx["debt_markers"]
    source_files, repo_rich = ctx["source_files"], ctx["repo_rich"]
    test_gap = 1.0 - min(1.0, tests["test_file_ratio"] * _TEST_RATIO_FULL_CREDIT) if source_files else 0.0
    rework_value, rework_quality = _PLACEHOLDER_REWORK
    dep_value, dep_quality = _PLACEHOLDER_DEP_CONFIG
    return {
        "hotspot_concentration": indicator_input(
            churn["concentration"] if churn else 0.0, _qf(repo_rich, churn.get("total_churn", 0)),
            churn.get("concentration", 0.0), churn.get("evidence", []),
        ),
        "rework_revert_signal": indicator_input(
            rework_value, rework_quality, "revert detection requires full history", [],
        ),
        "test_gap": indicator_input(
            test_gap, _qf(repo_rich, source_files), test_gap, tests.get("evidence", []),
        ),
        "todo_fixme_density": indicator_input(
            min(1.0, debt_markers["markers"] / _TODO_MARKERS_CAP), _qf(repo_rich, debt_markers["markers"]),
            debt_markers["markers"], debt_markers["evidence"],
        ),
        "documentation_gap": indicator_input(
            1.0 - min(1.0, docs["docs_files"] / _DOCS_FILES_FOR_NO_GAP), _qf(repo_rich, docs.get("docs_files", 0)),
            docs.get("docs_files", 0), docs.get("evidence", []),
        ),
        "dependency_config_risk": indicator_input(
            dep_value, dep_quality, "stale-lock detection limited", [],
        ),
    }


def _shared_context(
    inspection: InspectionResult,
    artifacts: list[dict],
    file_changes: list[dict],
    decision_counts: dict[str, int],
) -> dict[str, Any]:
    """Compute every metric once and derive the cross-dimension scalars."""
    total_files = max(1, len(inspection.files))
    source_files = max(1, sum(1 for f in inspection.files if f.language and not f.is_generated))
    repo_rich = min(1.0, total_files / _REPO_FILES_FOR_FULL_RICHNESS)

    commits = [a for a in artifacts if a.get("type") == "commit"]
    prs = [a for a in artifacts if a.get("type") == "pr"]
    releases = [a for a in artifacts if a.get("type") in ("release", "tag")]
    issues = [a for a in artifacts if a.get("type") == "issue"]

    # Index issue numbers once: linking check is O(commits), not O(commits*issues).
    issue_numbers = {
        num for num in ((i.get("metadata") or {}).get("number") for i in issues) if num
    }
    pr_ids = {a.get("provider_id") for a in prs}
    traced = sum(
        1 for a in commits if a.get("provider_id") in pr_ids or _links_issue(a, issue_numbers)
    )

    large_changes = sum(
        1 for fc in file_changes if fc.get("additions", 0) + fc.get("deletions", 0) > _LARGE_CHANGE_LINES
    )
    controlled_change = 1.0 - min(
        1.0, large_changes / max(1, len(file_changes) * _CHANGE_FRACTION_TOLERATED)
    )
    decision_counts = decision_counts or {}

    return {
        "repo_rich": repo_rich,
        "source_files": source_files,
        "commits": commits,
        "prs": prs,
        "releases": releases,
        "file_changes": file_changes,
        "traced": traced,
        "total_commits": len(commits),
        "has_releases": len(releases) >= _RELEASES_FOR_VERSION_EVIDENCE,
        "has_prs": len(prs) > 0,
        "large_changes": large_changes,
        "controlled_change": controlled_change,
        "rationale": decision_counts.get("decisions", 0),
        "followups": decision_counts.get("reviews", 0) + decision_counts.get("experiments", 0),
        "release_urls": [a["source_url"] for a in releases[:10] if a.get("source_url")],
        "structural": metrics.compute_structural_breadth(inspection),
        "deps": metrics.compute_dependency_breadth(inspection),
        "integration": metrics.compute_integration_breadth(inspection),
        "heterogeneity": metrics.compute_heterogeneity(inspection),
        "coupling": metrics.compute_change_coupling(file_changes),
        "churn": metrics.compute_churn_metrics(inspection, file_changes),
        "file_size": metrics.compute_file_size_health(inspection),
        "docs": metrics.compute_doc_quality(inspection),
        "tests": metrics.compute_test_signals(inspection),
        "setup": metrics.compute_setup_signals(inspection),
        "delivery": metrics.compute_delivery_signals(inspection),
        "scalability": metrics.compute_scalability_signals(inspection),
        "debt_markers": metrics.compute_debt_markers(inspection),
    }


def build_indicator_inputs(
    inspection: InspectionResult,
    artifacts: list[dict],
    file_changes: list[dict],
    decision_counts: dict[str, int] | None = None,
) -> dict[str, dict[str, Any]]:
    """Return per-dimension indicator inputs (normalized + quality + evidence)."""
    ctx = _shared_context(inspection, artifacts, file_changes, decision_counts or {})
    return {
        "technical_complexity": _complexity_inputs(ctx),
        "maintainability": _maintainability_inputs(ctx),
        "testing_maturity": _testing_inputs(ctx),
        "documentation_quality": _documentation_inputs(ctx),
        "evolution_health": _evolution_inputs(ctx),
        "delivery_readiness": _delivery_inputs(ctx),
        "scalability_readiness": _scalability_inputs(ctx),
        "technical_debt_risk": _debt_inputs(ctx),
    }


def run_pipeline(
    inspection: InspectionResult,
    artifacts: list[dict],
    file_changes: list[dict],
    decision_counts: dict[str, int] | None = None,
) -> list[Any]:
    inputs = build_indicator_inputs(inspection, artifacts, file_changes, decision_counts)
    return score_all(inputs)
