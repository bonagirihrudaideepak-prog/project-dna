import { Link } from "react-router-dom";

export function HomePage() {
  return (
    <div>
      <h1>Understand what your software became — and why.</h1>
      <p className="muted mb-lg">
        Project DNA reconstructs project evolution from repository evidence and human-confirmed decision
        rationale. Every score is explainable, every claim links back to evidence.
      </p>
      <div className="grid grid-3">
        <div className="card">
          <h3>Explainable DNA</h3>
          <p className="muted small">
            Eight dimensions with formula, coverage, confidence, and evidence. No hidden LLM scoring.
          </p>
        </div>
        <div className="card">
          <h3>Evolution timeline</h3>
          <p className="muted small">
            Releases, pull requests, commit clusters, dependency changes, decisions, and failed experiments
            in one chronology.
          </p>
        </div>
        <div className="card">
          <h3>Decision Archaeology</h3>
          <p className="muted small">
            Preserve the why: alternatives, reasons, linked evidence, and later outcome reviews.
          </p>
        </div>
      </div>
      <div className="mt-lg">
        <Link to="/projects">
          <button>Sign in with GitHub →</button>
        </Link>
      </div>
    </div>
  );
}