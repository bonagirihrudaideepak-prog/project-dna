"""MCP server exposing Project DNA read-only tools to AI agents.

Tools query the platform database directly via the application/domain layer, so
an agent can ask questions like "what is the maintainability trend for repo X"
without writing SQL.

Run with::

    python -m app.mcp.server

Add to an MCP client's config (secrets via env, never hardcoded)::

    "mcpServers": {
      "project-dna": {
        "command": "<abs path to .venv python>",
        "args": ["-m", "app.mcp.server"],
        "env": { "DATABASE_URL": "${DATABASE_URL}" }
      }
    }
"""

from __future__ import annotations

import logging
import os

from mcp.server.mcpserver import MCPServer

from ..adapters.db import SessionLocal
from ..models import Alert, AlertRule, DNAScore, Project, RepositorySnapshot

logger = logging.getLogger("projectdna.mcp")

server = MCPServer("project-dna")

# Coverage honesty is a hard rule: never report a withheld score as real.
MIN_COVERAGE = 0.35

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


def _score_map(db, snapshot: RepositorySnapshot) -> dict[str, float | None]:
    rows = db.query(DNAScore).filter(DNAScore.snapshot_id == snapshot.id).all()
    out: dict[str, float | None] = {}
    for r in rows:
        out[r.dimension] = r.score if r.coverage >= MIN_COVERAGE else None
    return out


def _snapshots_for_project(db, project: Project) -> list[RepositorySnapshot]:
    return (
        db.query(RepositorySnapshot)
        .filter(RepositorySnapshot.project_id == project.id)
        .order_by(RepositorySnapshot.created_at.asc())
        .all()
    )


def _project_row(db, project: Project) -> dict:
    snapshots = _snapshots_for_project(db, project)
    latest = snapshots[-1] if snapshots else None
    scores = _score_map(db, latest) if latest else {}
    return {
        "full_name": project.full_name,
        "description": project.description,
        "is_fixture": project.is_fixture,
        "latest_snapshot": latest.created_at.isoformat() if latest else None,
        "latest_scores": {d: scores.get(d) for d in DIMENSION_ORDER},
    }


@server.tool()
async def list_projects() -> list[dict]:
    """List analyzed projects with a summary of their latest DNA scores."""
    db = SessionLocal()
    try:
        projects = db.query(Project).order_by(Project.created_at.desc()).all()
        return [_project_row(db, p) for p in projects]
    finally:
        db.close()


@server.tool()
async def get_dna_trend(
    full_name: str,
    dimension: str | None = None,
) -> dict:
    """Return per-snapshot DNA scores (0-100) for a project, oldest first.

    Dimensions with insufficient evidence (coverage < 0.35) are null.
    """
    name = full_name.strip().lstrip("/")
    db = SessionLocal()
    try:
        project = db.query(Project).filter(Project.full_name == name).first()
        if not project:
            return {"error": f"Project not found: {name}"}
        if dimension and dimension not in DIMENSION_ORDER:
            return {
                "error": f"Unknown dimension: {dimension}. Valid: {', '.join(DIMENSION_ORDER)}"
            }
        snapshots = _snapshots_for_project(db, project)
        points = []
        for s in snapshots:
            scores = _score_map(db, s)
            row = {
                "captured_at": s.captured_at.isoformat()
                if s.captured_at
                else s.created_at.isoformat(),
                "commit_sha": s.commit_sha[:12] if s.commit_sha else None,
            }
            if dimension:
                row["score"] = scores.get(dimension)
            else:
                row["scores"] = {d: scores.get(d) for d in DIMENSION_ORDER}
            points.append(row)
        return {"project": name, "points": points}
    finally:
        db.close()


@server.tool()
async def list_active_alerts() -> list[dict]:
    """List unacknowledged DNA alerts across projects, newest first."""
    db = SessionLocal()
    try:
        alerts = (
            db.query(Alert)
            .join(AlertRule)
            .filter(Alert.acknowledged_at.is_(None))
            .order_by(Alert.fired_at.desc())
            .limit(50)
            .all()
        )
        rows = []
        for a in alerts:
            project = db.query(Project).filter(Project.id == a.rule.project_id).first()
            rows.append(
                {
                    "id": str(a.id),
                    "project": project.full_name if project else None,
                    "dimension": a.dimension,
                    "old_value": a.old_value,
                    "new_value": a.new_value,
                    "fired_at": a.fired_at.isoformat() if a.fired_at else None,
                }
            )
        return rows
    finally:
        db.close()


def main() -> None:
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
    server.run(transport="stdio")


if __name__ == "__main__":
    main()