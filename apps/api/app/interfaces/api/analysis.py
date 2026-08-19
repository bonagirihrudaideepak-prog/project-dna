"""Comparison, evolution graph, summaries, and export endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session

from ...adapters.db import get_db
from ...adapters.llm.prompts import PROMPT_VERSION
from ...application.exports import to_json, to_print_html
from ...application.llm_service import LLMService
from ...application.similarity import model_compatible, weighted_distance
from ...config import settings
from ...models import (
    Decision,
    DNAScore,
    Experiment,
    GraphEdge,
    GraphNode,
    LLMRun,
    RepositorySnapshot,
    TimelineEvent,
)
from ..deps import current_user, optional_user, parse_id
from ..schemas import CompareIn, SummaryIn
from .projects import require_membership

router = APIRouter(tags=["analysis"])

# Module-level LLM service instance
_llm_service = LLMService()


def _snapshot(db: Session, snapshot_id: str, user_id: str | None = None) -> RepositorySnapshot:
    sid = parse_id(snapshot_id, "snapshot_id")
    s = db.get(RepositorySnapshot, sid)
    if not s:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    require_membership(db, s.project_id, user_id)
    return s


def _dna_map(db: Session, snapshot_id: str) -> dict:
    rows = db.query(DNAScore).filter(DNAScore.snapshot_id == snapshot_id).all()
    return {r.dimension: {"score": r.score, "coverage": r.coverage, "confidence": r.confidence} for r in rows}


@router.post("/comparisons")
def compare(body: CompareIn, user_id: str | None = Depends(optional_user), db: Session = Depends(get_db)):
    a = _snapshot(db, body.snapshot_a, user_id)
    b = _snapshot(db, body.snapshot_b, user_id)
    score_a = _dna_map(db, a.id)
    score_b = _dna_map(db, b.id)
    compatible = model_compatible(a.score_model_version, b.score_model_version)
    result = weighted_distance(score_a, score_b)
    return {
        "snapshot_a": {"id": str(a.id), "project": a.project.full_name, "sha": a.commit_sha[:12]},
        "snapshot_b": {"id": str(b.id), "project": b.project.full_name, "sha": b.commit_sha[:12]},
        "model_compatible": compatible,
        "score_model_version": a.score_model_version,
        **result,
        "warning": None if compatible else "Snapshots use different score-model versions; comparison is approximate.",
    }


@router.get("/snapshots/{snapshot_id}/graph")
def get_graph(snapshot_id: str, focus: str | None = None, depth: int = 1, user_id: str | None = Depends(optional_user), db: Session = Depends(get_db)):
    s = _snapshot(db, snapshot_id, user_id)
    nodes = db.query(GraphNode).filter(GraphNode.snapshot_id == s.id).all()
    edges = (
        db.query(GraphEdge)
        .filter(GraphEdge.project_id == s.project_id)
        .filter(GraphEdge.id.in_(
            db.query(GraphEdge.id).join(GraphNode, GraphEdge.source_node_id == GraphNode.id)
            .filter(GraphNode.snapshot_id == s.id).distinct()
        ))
        .all()
    )
    node_dicts = [
        {
            "key": f"{n.entity_type}:{n.entity_id}",
            "node_type": n.node_type,
            "entity_type": n.entity_type,
            "entity_id": n.entity_id,
            "label": n.label,
            "metadata_json": n.metadata_json or {},
        }
        for n in nodes
    ]
    node_keys = {f"{n.entity_type}:{n.entity_id}" for n in nodes}
    edge_dicts = [
        {
            "source": f"{e.source.entity_type}:{e.source.entity_id}",
            "target": f"{e.target.entity_type}:{e.target.entity_id}",
            "edge_type": e.edge_type,
            "provenance": e.provenance,
            "confidence": e.confidence,
            "evidence_json": e.evidence_json or {},
        }
        for e in edges
        if f"{e.source.entity_type}:{e.source.entity_id}" in node_keys
        and f"{e.target.entity_type}:{e.target.entity_id}" in node_keys
    ]
    if focus:
        from ...domain.analysis.graph.builder import query_bounded

        bounded = query_bounded(node_dicts, edge_dicts, focus, depth)
        return bounded
    return {"nodes": node_dicts, "edges": edge_dicts, "focus": None}


@router.post("/snapshots/{snapshot_id}/summaries")
def create_summary(snapshot_id: str, body: SummaryIn, user_id: str = Depends(current_user), db: Session = Depends(get_db)):
    """Evidence-grounded summary endpoint.

    Tries configured LLM providers with automatic failover. If none succeed, or
    if LLM is disabled, returns a deterministic template built from the events.
    LLM output is validated and never used for scoring."""
    s = _snapshot(db, snapshot_id, user_id)
    events = db.query(TimelineEvent).filter(TimelineEvent.snapshot_id == s.id)
    if body.event_ids:
        events = events.filter(TimelineEvent.id.in_(body.event_ids))
    events = events.order_by(TimelineEvent.occurred_at).all()

    phases: list[dict] = []
    for e in events:
        phases.append({
            "text": f"{e.type}: {e.title}",
            "evidence_ids": (e.metadata_json or {}).get("artifact_ids", []),
        })

    if settings.llm_provider_order.lower() in ("none",):
        return {
            "summary": f"Snapshot {s.commit_sha[:12]} captured {len(events)} timeline events across {s.project.full_name}.",
            "claims": [
                {"text": p["text"], "evidence_ids": p["evidence_ids"]}
                for p in phases[: body.max_claims]
            ],
            "uncertainties": [
                "Reasons for changes are only available where confirmed by linked decisions or PR/issue text."
            ],
            "validation_status": "ok",
            "ai_assisted": False,
        }

    dna_rows = db.query(DNAScore).filter(DNAScore.snapshot_id == s.id).all()
    decisions = db.query(Decision).filter(Decision.project_id == s.project_id).all()
    experiments = db.query(Experiment).filter(Experiment.project_id == s.project_id).all()

    dna_text = "\n".join(
        f"- {r.dimension}: score={r.score if r.score is not None else 'withheld'} "
        f"(coverage {r.coverage:.2f}, {r.confidence})"
        for r in dna_rows
    ) or "- no DNA scores"

    timeline_text = "\n".join(
        f"- {e.type}: {e.title} ({e.provenance})"
        for e in reversed(events[:50])
    ) or "- no timeline events"

    decisions_text = "\n".join(
        f"- {d.title} [{d.status}]" for d in decisions
    ) or "- none"
    experiments_text = "\n".join(
        f"- {e.title} -> {e.decision}" for e in experiments
    ) or "- none"

    summary = _llm_service.summarize_snapshot(
        s.project.full_name,
        s.commit_sha,
        timeline_text,
        dna_text,
        decisions_text,
        experiments_text,
    )
    return summary


def _persist_llm_run(
    db: Session,
    snapshot_id: str,
    purpose: str,
    provider: str,
    model: str,
    system: str,
    user: str,
    output: dict,
    status: str,
) -> None:
    run = LLMRun(
        snapshot_id=snapshot_id,
        purpose=purpose,
        provider=provider,
        model=model,
        prompt_version=PROMPT_VERSION,
        input_evidence_ids=[line for line in user.splitlines() if line.startswith("- ")][:50],
        output_json=output,
        validation_status=status,
    )
    db.add(run)
    db.commit()


@router.get("/summaries/{summary_id}")
def get_summary(summary_id: str, user_id: str | None = Depends(optional_user), db: Session = Depends(get_db)):
    run = db.get(LLMRun, parse_id(summary_id, "summary_id"))
    if not run:
        raise HTTPException(status_code=404, detail="Summary not found")
    require_membership(db, run.snapshot.project_id, user_id)
    return {
        "id": str(run.id),
        "snapshot_id": str(run.snapshot_id),
        "purpose": run.purpose,
        "provider": run.provider,
        "model": run.model,
        "prompt_version": run.prompt_version,
        "validation_status": run.validation_status,
        "output": run.output_json,
    }


@router.post("/snapshots/{snapshot_id}/exports")
def queue_export(snapshot_id: str, fmt: str = "json", user_id: str | None = Depends(optional_user), db: Session = Depends(get_db)):
    s = _snapshot(db, snapshot_id, user_id)
    payload = _snapshot_payload(db, s, fmt)
    if fmt == "json":
        return JSONResponse({"format": "json", "content": payload})
    if fmt == "html":
        return HTMLResponse(payload)
    raise HTTPException(status_code=400, detail="Unsupported format")


def _snapshot_payload(db: Session, s: RepositorySnapshot, fmt: str):
    dna = _dna_map(db, s.id)
    timeline = db.query(TimelineEvent).filter(TimelineEvent.snapshot_id == s.id).all()
    decisions = db.query(Decision).filter(Decision.project_id == s.project_id).all()
    experiments = db.query(Experiment).filter(Experiment.project_id == s.project_id).all()
    data = {
        "project": {
            "id": str(s.project.id),
            "full_name": s.project.full_name,
            "description": s.project.description,
            "default_branch": s.project.default_branch,
        },
        "snapshot": {
            "id": str(s.id),
            "commit_sha": s.commit_sha,
            "analyzer_version": s.analyzer_version,
            "score_model_version": s.score_model_version,
            "captured_at": s.captured_at.isoformat() if s.captured_at else None,
            "status": s.status,
        },
        "dna": [
            {"dimension": k, "score": v["score"], "coverage": v["coverage"], "confidence": v["confidence"]}
            for k, v in dna.items()
        ],
        "timeline": [
            {"type": t.type, "title": t.title, "occurred_at": t.occurred_at, "provenance": t.provenance}
            for t in timeline
        ],
        "decisions": [{"title": d.title, "status": d.status, "decided_at": d.decided_at} for d in decisions],
        "experiments": [{"title": e.title, "decision": e.decision, "evaluated_at": e.evaluated_at} for e in experiments],
        "warnings": (s.warning_json or {}).get("warnings", []),
    }
    if fmt == "json":
        return to_json(data)
    return to_print_html(data)