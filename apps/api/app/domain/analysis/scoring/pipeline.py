"""Analysis pipeline: converts inspection + artifact data into indicators and
scores for all eight dimensions. Deterministic and reproducible."""

from __future__ import annotations

from typing import Any

from ..extractors import metrics  # noqa: F401
from ..inspector import InspectionResult
from .engine import indicator_input, score_all


def build_indicator_inputs(
    inspection: InspectionResult,
    artifacts: list[dict],
    file_changes: list[dict],
    decision_counts: dict[str, int] | None = None,
) -> dict[str, dict[str, Any]]:
    """Return per-dimension indicator inputs (normalized + quality + evidence)."""
    decision_counts = decision_counts or {}

    structural = metrics.compute_structural_breadth(inspection)
    deps = metrics.compute_dependency_breadth(inspection)
    integration = metrics.compute_integration_breadth(inspection)
    heterogeneity = metrics.compute_heterogeneity(inspection)
    coupling = metrics.compute_change_coupling(file_changes)
    churn = metrics.compute_churn_metrics(inspection, file_changes)
    file_size = metrics.compute_file_size_health(inspection)
    docs = metrics.compute_doc_quality(inspection)
    tests = metrics.compute_test_signals(inspection)
    setup = metrics.compute_setup_signals(inspection)
    delivery = metrics.compute_delivery_signals(inspection)
    scalability = metrics.compute_scalability_signals(inspection)
    debt_markers = metrics.compute_debt_markers(inspection)

    total_files = max(1, len(inspection.files))
    source_files = max(1, sum(1 for f in inspection.files if f.language and not f.is_generated))

    # Whether repository-level evidence is rich enough for a quality factor
    repo_rich = min(1.0, total_files / 50.0)

    commits = [a for a in artifacts if a.get("type") == "commit"]
    prs = [a for a in artifacts if a.get("type") == "pr"]
    releases = [a for a in artifacts if a.get("type") in ("release", "tag")]
    issues = [a for a in artifacts if a.get("type") == "issue"]

    pr_ids = {a.get("provider_id") for a in prs}
    traced = sum(
        1 for a in commits if a.get("provider_id") in pr_ids or _links_issue(a, issues)
    )
    traceable_ratio = traced / len(commits) if commits else 0.0

    has_releases = len(releases) >= 2
    has_prs = len(prs) > 0
    large_changes = sum(1 for fc in file_changes if fc.get("additions", 0) + fc.get("deletions", 0) > 1000)
    controlled_change = 1.0 - min(1.0, large_changes / max(1, len(file_changes) * 0.1))
    rationale = decision_counts.get("decisions", 0)
    followups = decision_counts.get("reviews", 0) + decision_counts.get("experiments", 0)

    # ------- Technical Complexity (descriptive) -------
    complexity = {
        "structural_breadth": indicator_input(
            min(1.0, structural["dirs"] / 40.0), _qf(repo_rich, structural["dirs"]),
            structural["raw_value"], structural["evidence"],
        ),
        "dependency_breadth": indicator_input(
            min(1.0, deps["dependencies"] / 80.0), _qf(repo_rich, deps["dependencies"]),
            deps["raw_value"], deps["evidence"],
        ),
        "integration_breadth": indicator_input(
            min(1.0, integration["raw_value"] / 25.0), _qf(repo_rich, integration["raw_value"]),
            integration["raw_value"], integration["evidence"],
        ),
        "change_coupling": indicator_input(
            min(1.0, coupling["max_coupling"] / 30.0), _qf(repo_rich, coupling["max_coupling"]),
            coupling["raw_value"], coupling["evidence"],
        ),
        "lang_config_heterogeneity": indicator_input(
            min(1.0, heterogeneity["raw_value"] / 15.0), _qf(repo_rich, heterogeneity["raw_value"]),
            heterogeneity["raw_value"], heterogeneity["evidence"],
        ),
    }

    # ------- Maintainability (higher is better) -------
    hotspot_dispersion = 1.0 - (churn["concentration"] if churn else 0.0)
    coupling_inverse = 1.0 - min(1.0, coupling["avg_coupling"] / max(1, coupling["max_coupling"])) if coupling.get("max_coupling") else 1.0
    maintainability = {
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

    # ------- Testing Maturity (higher is better) -------
    testing = {
        "test_file_ratio": indicator_input(
            min(1.0, tests["test_file_ratio"] * 3.0), _qf(repo_rich, tests.get("test_files", 0)),
            tests.get("test_file_ratio", 0.0), tests.get("evidence", []),
        ),
        "ci_test_execution": indicator_input(
            1.0 if tests.get("has_ci_test") else 0.0, _qf(repo_rich, len(tests.get("evidence", []))),
            tests.get("has_ci_test"), tests.get("evidence", []),
        ),
        "test_breadth": indicator_input(
            min(1.0, len(tests.get("test_breadth", set())) / 3.0), _qf(repo_rich, len(tests.get("test_breadth", set()))),
            list(tests.get("test_breadth", set())), tests.get("evidence", []),
        ),
        "test_recency": indicator_input(0.5, 0.3, "not computed", []),
        "trusted_coverage_artifact": indicator_input(0.0, 0.0, "none", []),
    }

    # ------- Documentation Quality (higher is better) -------
    documentation = {
        "readme_completeness": indicator_input(
            min(1.0, docs["readme_sections"] / 5.0), _qf(repo_rich, docs.get("docs_files", 0)),
            docs.get("readme_sections", 0), docs.get("evidence", []),
        ),
        "setup_reproducibility": indicator_input(
            min(1.0, (setup["lockfiles"] + setup["env_templates"]) / 3.0), _qf(repo_rich, len(setup["evidence"])),
            {"lockfiles": setup["lockfiles"], "env_templates": setup["env_templates"]}, setup["evidence"],
        ),
        "architecture_decision_docs": indicator_input(
            min(1.0, docs["adrs"] / 3.0), _qf(repo_rich, docs["adrs"]),
            docs["adrs"], docs["evidence"],
        ),
        "api_user_docs": indicator_input(0.0, 0.2, "not detected", []),
        "governance_docs": indicator_input(
            1.0 if setup["readme_present"] else 0.0, 0.5,
            setup["readme_present"], ["file:README" if setup["readme_present"] else ""],
        ),
    }

    # ------- Evolution Health (higher is better) -------
    evolution = {
        "traceable_change_units": indicator_input(
            traceable_ratio, _qf(repo_rich, len(commits)),
            {"traced": traced, "total": len(commits)}, [],
        ),
        "release_version_evidence": indicator_input(
            1.0 if has_releases else (0.4 if has_prs else 0.0), _qf(repo_rich, len(releases)),
            {"releases": len(releases), "prs": len(prs)}, [a["source_url"] for a in releases[:10] if a.get("source_url")],
        ),
        "controlled_change_size": indicator_input(
            controlled_change, _qf(repo_rich, len(file_changes)),
            {"large_changes": large_changes}, [],
        ),
        "rationale_preservation": indicator_input(
            min(1.0, rationale / 5.0), 0.0 if not rationale else 1.0,
            rationale, [],
        ),
        "outcome_followup": indicator_input(
            min(1.0, followups / 5.0), 0.0 if not followups else 1.0,
            followups, [],
        ),
    }

    # ------- Delivery Readiness (higher is better) -------
    checks = delivery.get("checks", {})
    delivery_inputs = {
        "automated_checks": indicator_input(
            (sum(1 for c in checks.values() if c)) / 3.0, _qf(repo_rich, delivery.get("ci_files", 0)),
            checks, delivery.get("evidence", []),
        ),
        "env_config_separation": indicator_input(
            min(1.0, delivery.get("env_sep_files", 0) / 2.0), _qf(repo_rich, delivery.get("env_sep_files", 0)),
            delivery.get("env_sep_files", 0), delivery.get("evidence", []),
        ),
        "reproducible_dependency_state": indicator_input(
            min(1.0, setup["lockfiles"] / 2.0), _qf(repo_rich, setup["lockfiles"]),
            setup["lockfiles"], setup["evidence"],
        ),
        "deployment_definition": indicator_input(
            min(1.0, delivery.get("deploy_files", 0) / 2.0), _qf(repo_rich, delivery.get("deploy_files", 0)),
            delivery.get("deploy_files", 0), delivery.get("evidence", []),
        ),
        "release_rollback_evidence": indicator_input(
            0.5 if has_releases else 0.0, 0.4,
            {"releases": len(releases)}, [a["source_url"] for a in releases[:10] if a.get("source_url")],
        ),
    }

    # ------- Scalability Readiness (higher is better, evidence-limited) -------
    scalability_inputs = {
        "separation_of_concerns": indicator_input(
            min(1.0, scalability["concerns"] / 4.0), _qf(repo_rich, len(scalability.get("evidence", []))),
            scalability["concerns"], scalability.get("evidence", []),
        ),
        "persistent_data_discipline": indicator_input(
            min(1.0, scalability["migrations"] / 5.0), _qf(repo_rich, scalability["migrations"]),
            scalability["migrations"], scalability.get("evidence", []),
        ),
        "stateless_configurable_services": indicator_input(
            min(1.0, setup["env_templates"] / 2.0), _qf(repo_rich, setup["env_templates"]),
            setup["env_templates"], setup["evidence"],
        ),
        "async_cache_batch": indicator_input(
            min(1.0, scalability["async_files"] / 5.0), _qf(repo_rich, scalability["async_files"]),
            scalability["async_files"], scalability.get("evidence", []),
        ),
        "observability_load_evidence": indicator_input(
            min(1.0, scalability["obs_files"] / 3.0), _qf(repo_rich, scalability["obs_files"]),
            scalability["obs_files"], scalability.get("evidence", []),
        ),
    }

    # ------- Technical Debt Risk (lower is better) -------
    test_gap = 1.0 - min(1.0, tests["test_file_ratio"] * 3.0) if source_files else 0.0
    debt_inputs = {
        "hotspot_concentration": indicator_input(
            churn["concentration"] if churn else 0.0, _qf(repo_rich, churn.get("total_churn", 0)),
            churn.get("concentration", 0.0), churn.get("evidence", []),
        ),
        "rework_revert_signal": indicator_input(
            0.2, 0.3, "revert detection requires full history", [],
        ),
        "test_gap": indicator_input(
            test_gap, _qf(repo_rich, source_files), test_gap, tests.get("evidence", []),
        ),
        "todo_fixme_density": indicator_input(
            min(1.0, debt_markers["markers"] / 30.0), _qf(repo_rich, debt_markers["markers"]),
            debt_markers["markers"], debt_markers["evidence"],
        ),
        "documentation_gap": indicator_input(
            1.0 - min(1.0, docs["docs_files"] / 8.0), _qf(repo_rich, docs.get("docs_files", 0)),
            docs.get("docs_files", 0), docs.get("evidence", []),
        ),
        "dependency_config_risk": indicator_input(0.2, 0.4, "stale-lock detection limited", []),
    }

    return {
        "technical_complexity": complexity,
        "maintainability": maintainability,
        "testing_maturity": testing,
        "documentation_quality": documentation,
        "evolution_health": evolution,
        "delivery_readiness": delivery_inputs,
        "scalability_readiness": scalability_inputs,
        "technical_debt_risk": debt_inputs,
    }


def _links_issue(commit: dict, issues: list[dict]) -> bool:
    body = (commit.get("metadata") or {}).get("message", "")[:200]
    for issue in issues:
        num = (issue.get("metadata") or {}).get("number")
        if num and f"#{num}" in body:
            return True
    return False


def _qf(repo_rich: float, evidence_count: float) -> float:
    """Evidence-quality factor: how much can we trust this indicator.

    Driven primarily by the presence of retrieved evidence; repository size
    only nudges the confidence slightly so small but well-documented repos are
    not unfairly withheld.
    """
    if evidence_count <= 0:
        return 0.0
    count_factor = min(1.0, 0.7 + 0.3 * evidence_count / 10.0)
    richness = min(1.0, 0.7 + 0.3 * repo_rich)
    return count_factor * richness


def _test_score(tests: dict) -> float:
    return min(
        1.0,
        min(1.0, tests.get("test_file_ratio", 0.0) * 3.0) * 0.4
        + (1.0 if tests.get("has_ci_test") else 0.0) * 0.3
        + min(1.0, len(tests.get("test_breadth", set())) / 3.0) * 0.3,
    )


def _doc_score(docs: dict) -> float:
    return min(1.0, docs.get("readme_sections", 0) / 5.0)


def run_pipeline(
    inspection: InspectionResult,
    artifacts: list[dict],
    file_changes: list[dict],
    decision_counts: dict[str, int] | None = None,
) -> list[Any]:
    inputs = build_indicator_inputs(inspection, artifacts, file_changes, decision_counts)
    return score_all(inputs)