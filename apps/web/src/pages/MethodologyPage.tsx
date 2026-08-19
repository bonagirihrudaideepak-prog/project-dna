import { useState } from "react";
import { Card, Button } from "../lib/components";

export const MethodologyPage = () => {
  const dimensions = [
    {
      key: "technical_complexity",
      name: "Technical Complexity",
      direction: "descriptive",
      description:
        "The number and interaction of technical elements. Descriptive, not a quality judgement.",
      indicators: [
        { key: "structural_breadth", weight: 0.2 },
        { key: "dependency_breadth", weight: 0.2 },
        { key: "integration_breadth", weight: 0.2 },
        { key: "change_coupling", weight: 0.2 },
        { key: "lang_config_heterogeneity", weight: 0.2 },
      ],
    },
    {
      key: "maintainability",
      name: "Maintainability",
      direction: "higher_is_better",
      description:
        "Ease of understanding and changing the codebase safely.",
      indicators: [
        { key: "hotspot_dispersion", weight: 0.25 },
        { key: "file_size_health", weight: 0.15 },
        { key: "change_coupling_inverse", weight: 0.2 },
        { key: "test_maturity", weight: 0.2 },
        { key: "documentation_quality", weight: 0.2 },
      ],
    },
    {
      key: "testing_maturity",
      name: "Testing Maturity",
      direction: "higher_is_better",
      description:
        "Presence of tests, CI test execution, and test breadth. Not a claim about actual coverage.",
      indicators: [
        { key: "test_file_ratio", weight: 0.25 },
        { key: "ci_test_execution", weight: 0.25 },
        { key: "test_breadth", weight: 0.2 },
        { key: "test_recency", weight: 0.15 },
        { key: "trusted_coverage_artifact", weight: 0.15 },
      ],
    },
    {
      key: "documentation_quality",
      name: "Documentation Quality",
      direction: "higher_is_better",
      description:
        "Quality of README, setup, architecture, API, and governance documentation.",
      indicators: [
        { key: "readme_completeness", weight: 0.3 },
        { key: "setup_reproducibility", weight: 0.2 },
        { key: "architecture_decision_docs", weight: 0.2 },
        { key: "api_user_docs", weight: 0.15 },
        { key: "governance_docs", weight: 0.15 },
      ],
    },
    {
      key: "evolution_health",
      name: "Evolution Health",
      direction: "higher_is_better",
      description:
        "Quality of project history: traceable change units, releases, controlled change size, rationale, and follow-up.",
      indicators: [
        { key: "traceable_change_units", weight: 0.25 },
        { key: "release_version_evidence", weight: 0.2 },
        { key: "controlled_change_size", weight: 0.2 },
        { key: "rationale_preservation", weight: 0.2 },
        { key: "outcome_followup", weight: 0.15 },
      ],
    },
    {
      key: "delivery_readiness",
      name: "Delivery Readiness",
      direction: "higher_is_better",
      description:
        "Signals for automated checks, environment separation, reproducible dependencies, deployment, and release/rollback.",
      indicators: [
        { key: "automated_checks", weight: 0.25 },
        { key: "env_config_separation", weight: 0.2 },
        { key: "reproducible_dependency_state", weight: 0.2 },
        { key: "deployment_definition", weight: 0.2 },
        { key: "release_rollback_evidence", weight: 0.15 },
      ],
    },
    {
      key: "scalability_readiness",
      name: "Scalability Readiness",
      direction: "higher_is_better",
      description:
        "Readiness signals for separation of concerns, data discipline, statelessness, async mechanisms, and observability.",
      indicators: [
        { key: "separation_of_concerns", weight: 0.25 },
        { key: "persistent_data_discipline", weight: 0.2 },
        { key: "stateless_configurable_services", weight: 0.2 },
        { key: "async_cache_batch", weight: 0.15 },
        { key: "observability_load_evidence", weight: 0.2 },
      ],
    },
    {
      key: "technical_debt_risk",
      name: "Technical Debt Risk",
      direction: "lower_is_better",
      description:
        "Risk signals from hotspots, rework, test gaps, debt markers, doc gaps, and dependency/config risk.",
      indicators: [
        { key: "hotspot_concentration", weight: 0.25 },
        { key: "rework_revert_signal", weight: 0.2 },
        { key: "test_gap", weight: 0.2 },
        { key: "todo_fixme_density", weight: 0.1 },
        { key: "documentation_gap", weight: 0.1 },
        { key: "dependency_config_risk", weight: 0.15 },
      ],
    },
  ];

  return (
    <div className="min-h-screen bg-pageBg p-4 md:p-8">
      <h1 className="text-2xl font-bold text-slate-700 mb-6">
        Methodology
      </h1>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {dimensions.map((dim) => (
          <Card key={dim.key} className="p-4 mb-6">
            <h2 className="text-lg font-medium text-slate-700 mb-3">
              {dim.name}
            </h2>
            <p className="text-sm text-slate-500 mb-4">
              {dim.description}
            </p>
            <div className="space-y-2">
              {dim.indicators.map((ind) => (
                <div key={ind.key} className="flex items-baseline text-xs">
                  <span className="w-24 text-slate-500">{ind.key}</span>
                  <span className="flex-1">
                    <span className="font-medium">{ind.weight}</span>
                    <span className="text-slate-400">weight</span>
                  </span>
                </div>
              ))}
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
};

export default MethodologyPage;