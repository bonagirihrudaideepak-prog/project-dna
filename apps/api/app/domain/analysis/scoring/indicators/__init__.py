"""Per-dimension indicator builders for the DNA scoring pipeline.

Each module builds the indicator inputs for one DNA dimension.
Exports a single ``build_indicators`` function returning a dict compatible
with ``pipeline.build_indicator_inputs``.
"""

from __future__ import annotations

from ...extractors import metrics
from ...inspector import InspectionResult
from ..engine import indicator_input
from ..pipeline import _qf  # evidence-quality factor

__all__ = [
    "build_complexity_indicators",
    "build_maintainability_indicators",
    "build_testing_indicators",
    "build_documentation_indicators",
    "build_evolution_indicators",
    "build_delivery_indicators",
    "build_scalability_indicators",
    "build_debt_indicators",
]


# ── Technical Complexity ────────────────────────────────────────────

def build_complexity_indicators(
    inspection: InspectionResult,
    artifacts: list[dict],
    file_changes: list[dict],
    repo_rich: float,
) -> dict:
    structural = metrics.compute_structural_breadth(inspection)
    deps = metrics.compute_dependency_breadth(inspection)
    integration = metrics.compute_integration_breadth(inspection)
    heterogeneity = metrics.compute_heterogeneity(inspection)
    coupling = metrics.compute_change_coupling(file_changes)

    return {
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


# ── Maintainability ─────────────────────────────────────────────────

def build_maintainability_indicators(
    inspection: InspectionResult,
    artifacts: list[dict],
    file_changes: list[dict],
    repo_rich: float,
) -> dict:
    churn = metrics.compute_churn_metrics(inspection, file_changes)
    file_size = metrics.compute_file_size_health(inspection)
    coupling = metrics.compute_change_coupling(file_changes)
    tests = metrics.compute_test_signals(inspection)
    docs = metrics.compute_doc_quality(inspection)

    hotspot_dispersion = 1.0 - (churn["concentration"] if churn else 0.0)
    coupling_inverse = 1.0 - min(1.0, coupling["avg_coupling"] / max(1, coupling["max_coupling"])) if coupling.get("max_coupling") else 1.0

    return {
        "hotspot_dispersion": indicator_input(
            hotspot_dispersion, _qf(repo_rich, churn.get("total_churn", 0)) if churn else 0.0,
            churn.get("concentration", 0.0) if churn else 0.0, churn.get("evidence", []) if churn else [],
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


# ── Testing Maturity ────────────────────────────────────────────────

def build_testing_indicators(
    inspection: InspectionResult,
    artifacts: list[dict],
    file_changes: list[dict],
    repo_rich: float,
) -> dict:
    tests = metrics.compute_test_signals(inspection)

    return {
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


# ── Documentation Quality ───────────────────────────────────────────

def build_documentation_indicators(
    inspection: InspectionResult,
    artifacts: list[dict],
    file_changes: list[dict],
    repo_rich: float,
) -> dict:
    docs = metrics.compute_doc_quality(inspection)
    setup = metrics.compute_setup_signals(inspection)

    return {
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


# ── Evolution Health ────────────────────────────────────────────────

def build_evolution_indicators(
    inspection: InspectionResult,
    artifacts: list[dict],
    file_changes: list[dict],
    repo_rich: float,
) -> dict:
    from ..pipeline import _links_issue

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

    return {
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
            min(1.0, 0 / 5.0), 0.0 if 0 else 1.0, 0, [],
        ),
        "outcome_followup": indicator_input(
            min(1.0, 0 / 5.0), 0.0 if 0 else 1.0, 0, [],
        ),
    }


# ── Delivery Readiness ──────────────────────────────────────────────

def build_delivery_indicators(
    inspection: InspectionResult,
    artifacts: list[dict],
    file_changes: list[dict],
    repo_rich: float,
) -> dict:
    delivery = metrics.compute_delivery_signals(inspection)
    setup = metrics.compute_setup_signals(inspection)

    # Derive release status from artifacts
    releases = [a for a in artifacts if a.get("type") in ("release", "tag")]
    has_releases = len(releases) >= 2

    checks = delivery.get("checks", {})

    return {
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


# ── Scalability Readiness ───────────────────────────────────────────

def build_scalability_indicators(
    inspection: InspectionResult,
    artifacts: list[dict],
    file_changes: list[dict],
    repo_rich: float,
) -> dict:
    scalability = metrics.compute_scalability_signals(inspection)
    setup = metrics.compute_setup_signals(inspection)

    return {
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


# ── Technical Debt Risk ─────────────────────────────────────────────

def build_debt_indicators(
    inspection: InspectionResult,
    artifacts: list[dict],
    file_changes: list[dict],
    repo_rich: float,
) -> dict:
    debt_markers = metrics.compute_debt_markers(inspection)
    churn = metrics.compute_churn_metrics(inspection, file_changes)
    tests = metrics.compute_test_signals(inspection)
    docs = metrics.compute_doc_quality(inspection)

    source_files = max(1, sum(1 for f in inspection.files if f.language and not f.is_generated))

    test_gap = 1.0 - min(1.0, tests["test_file_ratio"] * 3.0) if source_files else 0.0

    return {
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


# Helper functions duplicated from pipeline.py (avoid circular imports)
def _test_score(tests: dict) -> float:
    """Replicate pipeline._test_score without circular import dependency."""
    return min(
        1.0,
        min(1.0, tests.get("test_file_ratio", 0.0) * 3.0) * 0.4
        + (1.0 if tests.get("has_ci_test") else 0.0) * 0.3
        + min(1.0, len(tests.get("test_breadth", set())) / 3.0) * 0.3,
    )


def _doc_score(docs: dict) -> float:
    """Replicate pipeline._doc_score without circular import dependency."""
    return min(1.0, docs.get("readme_sections", 0) / 5.0)