"""End-to-end smoke test: queue an analysis job for a fixture and run the
pipeline synchronously, printing DNA scores."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://projectdna:projectdna@localhost:5434/projectdna")
os.environ.setdefault("FIXTURE_ROOT", "C:\\Users\\durga\\OneDrive\\Desktop\\ttgh\\project-dna\\fixtures")

from app.adapters.db import SessionLocal  # noqa: E402
from app.application.analysis import FixtureSource, run_snapshot_analysis  # noqa: E402
from app.config import settings  # noqa: E402
from app.models import AnalysisJob, DNAScore, Project, RepositorySnapshot  # noqa: E402


def run(full_name: str):
    db = SessionLocal()
    try:
        project = db.query(Project).filter(Project.full_name == full_name).first()
        if not project:
            print(f"project not found: {full_name}")
            return
        snap = RepositorySnapshot(
            project_id=project.id,
            commit_sha="",
            analyzer_version="dna-analyzer-1.0",
            score_model_version="dna-core-1.0",
            status="PENDING",
        )
        db.add(snap)
        db.flush()
        job = AnalysisJob(snapshot_id=snap.id, state="QUEUED")
        db.add(job)
        db.commit()

        import json
        from pathlib import Path

        root = Path(settings.fixture_root) / full_name.split("/")[-1]
        for d in Path(settings.fixture_root).iterdir():
            if (d / "manifest.json").exists() and json.loads((d / "manifest.json").read_text()).get("full_name") == full_name:
                root = d
                break
        source = FixtureSource(root)

        result = run_snapshot_analysis(db, str(snap.id), source)
        print(f"\n=== {full_name}: {result['status']} ({result['event_count']} timeline events) ===")
        scores = db.query(DNAScore).filter(DNAScore.snapshot_id == snap.id).all()
        for s in sorted(scores, key=lambda x: x.dimension):
            status = str(s.score) if s.score is not None else "withheld"
            print(f"  {s.dimension:<26} {status:>7}  cov={s.coverage:.2f}  {s.confidence}")
        print(f"  warnings: {result['warnings']}")
    finally:
        db.close()


if __name__ == "__main__":
    for name in ["team/wardrobe-api", "student/minimal-app", "student/evolution-app"]:
        run(name)