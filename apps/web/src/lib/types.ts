export type Direction = "higher_is_better" | "lower_is_better" | "descriptive";

export interface DNAIndicator {
  key: string;
  raw_value: unknown;
  normalized_value: number;
  quality: number;
  evidence_ids: string[];
}

export interface ScoredDimension {
  dimension: string;
  score: number | null;
  coverage: number;
  confidence: string;
  direction: Direction;
  model_version: string;
  indicators: DNAIndicator[];
  limitations: string[];
}

export interface DNAScore {
  dimension: string;
  score: number | null;
  coverage: number;
  confidence: string;
  direction: Direction;
  model_version: string;
  explanation?: Record<string, unknown>;
}

export interface TimelineEvent {
  id: string;
  type: string;
  title: string;
  summary: string | null;
  occurred_at: string | null;
  end_at: string | null;
  confidence: number;
  provenance: string;
  components: string[];
  artifact_ids: string[];
  metadata: Record<string, unknown>;
}

export interface Snapshot {
  id: string;
  project_id: string;
  commit_sha: string;
  analyzer_version: string;
  score_model_version: string;
  status: string;
  captured_at: string | null;
  warning_json: Record<string, unknown>;
  limits_json: Record<string, unknown>;
}

export interface Project {
  id: string;
  full_name: string;
  owner: string;
  name: string;
  visibility: string;
  default_branch: string;
  description: string | null;
  is_fixture: boolean;
  latest_snapshot: Snapshot | null;
}

export interface AnalysisJob {
  id: string;
  snapshot_id: string;
  state: string;
  progress: number;
  phase: string | null;
  error_code: string | null;
  error_detail: string | null;
}

export interface Decision {
  id: string;
  title: string;
  context: string | null;
  decision_text: string | null;
  reason: string | null;
  expected_impact: Record<string, unknown>;
  status: string;
  decided_at: string | null;
  provenance: string;
  archived: boolean;
  alternatives: {
    id: string;
    name: string;
    advantages: string | null;
    disadvantages: string | null;
    rejection_reason: string | null;
  }[];
  outcome_reviews: {
    id: string;
    reviewed_at: string;
    actual_impact: string | null;
    evidence: string | null;
    verdict: string;
  }[];
}

export interface Experiment {
  id: string;
  title: string;
  hypothesis: string | null;
  success_criterion: string | null;
  method: string | null;
  result: string | null;
  decision: string;
  reason: string | null;
  start_at: string | null;
  evaluated_at: string | null;
  archived: boolean;
}

export interface GraphData {
  nodes: {
    key: string;
    node_type: string;
    label: string;
    entity_type: string;
    entity_id: string;
    metadata_json: Record<string, unknown>;
  }[];
  edges: {
    source: string;
    target: string;
    edge_type: string;
    provenance: string;
    confidence: number;
    evidence_json: Record<string, unknown>;
  }[];
  focus: unknown;
}

export interface User {
  id: string;
  login: string;
  display_name: string | null;
  avatar_url: string | null;
  github_connected: boolean;
}

export interface AlertRule {
  id: string;
  project_id: string;
  dimension: string;
  operator: "lt" | "gt";
  threshold: number;
  enabled: boolean;
}

export interface Alert {
  id: string;
  rule_id: string;
  snapshot_id: string;
  dimension: string;
  old_value: number | null;
  new_value: number | null;
  fired_at: string | null;
  acknowledged_at: string | null;
}

export interface TrendPoint {
  snapshot_id: string;
  captured_at: string | null;
  created_at: string | null;
  scores: Record<string, number | null>;
}

// API response envelopes
export interface ApiListResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export interface ApiErrorResponse {
  error: {
    code: string;
    message: string;
    retryable: boolean;
  };
}
export interface MethodologyIndicator {
  key: string;
  weight: number;
  direction: Direction;
}

export interface MethodologyDimension {
  key: string;
  name: string;
  direction: Direction;
  description: string;
  indicators: MethodologyIndicator[];
}

export interface CoverageLabel {
  below: number;
  label: string;
}

export interface Methodology {
  model_version: string;
  dimensions: MethodologyDimension[];
  coverage_labels: CoverageLabel[];
  min_coverage_for_score: number;
  caveats: string[];
}
