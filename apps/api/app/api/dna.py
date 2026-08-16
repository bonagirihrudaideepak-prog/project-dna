"""DNA, timeline, hotspots, and change exploration endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import optional_user, parse_id
from ..models import DNAScore, MetricValue, RepositorySnapshot, TimelineEvent
from ..schemas import EventPatchIn

router = APIRouter(tags=["dna"])


def _get_snapshot(db: Session, snapshot_id: str) -> RepositorySnapshot:
    sid = parse_id(snapshot_id, "snapshot_id")
    snap = db.get(RepositorySnapshot, sid)
    if not snap:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    return snap


@router.get("/snapshots/{snapshot_id}/dna")
def get_dna(snapshot_id: str, user_id: str | None = Depends(optional_user), db: Session = Depends(get_db)):
    snap = _get_snapshot(db, snapshot_id)
    scores = db.query(DNAScore).filter(DNAScore.snapshot_id == snap.id).all()
    return [
        {
            "dimension": s.dimension,
            "score": s.score,
            "coverage": s.coverage,
            "confidence": s.confidence,
            "direction": s.direction,
            "model_version": s.model_version,
            "explanation": s.explanation_json,
        }
        for s in sorted(scores, key=lambda s: s.dimension)
    ]


@router.get("/snapshots/{snapshot_id}/dna/{dimension}")
def get_dna_dimension(snapshot_id: str, dimension: str, user_id: str | None = Depends(optional_user), db: Session = Depends(get_db)):
    snap = _get_snapshot(db, snapshot_id)
    score = (
        db.query(DNAScore)
        .filter(DNAScore.snapshot_id == snap.id, DNAScore.dimension == dimension)
        .first()
    )
    if not score:
        raise HTTPException(status_code=404, detail="Dimension not found")
    return {
        "dimension": score.dimension,
        "score": score.score,
        "coverage": score.coverage,
        "confidence": score.confidence,
        "direction": score.direction,
        "model_version": score.model_version,
        "explanation": score.explanation_json,
        "evidence": score.explanation_json.get("indicators", []),
    }


@router.get("/snapshots/{snapshot_id}/timeline")
def get_timeline(
    snapshot_id: str,
    event_type: str | None = None,
    component: str | None = None,
    user_id: str | None = Depends(optional_user),
    db: Session = Depends(get_db),
):
    snap = _get_snapshot(db, snapshot_id)
    q = db.query(TimelineEvent).filter(TimelineEvent.snapshot_id == snap.id)
    if event_type:
        q = q.filter(TimelineEvent.type == event_type)
    events = q.order_by(TimelineEvent.occurred_at.desc()).all()
    out = []
    for e in events:
        meta = e.metadata_json or {}
        if component and component not in meta.get("components", []):
            continue
        out.append({
            "id": str(e.id),
            "type": e.type,
            "title": e.title,
            "summary": e.summary,
            "occurred_at": e.occurred_at,
            "end_at": e.end_at,
            "confidence": e.confidence,
            "provenance": e.provenance,
            "components": meta.get("components", []),
            "artifact_ids": meta.get("artifact_ids", []),
            "metadata": meta,
        })
    return out


@router.get("/timeline-events/{event_id}")
def get_event(event_id: str, user_id: str | None = Depends(optional_user), db: Session = Depends(get_db)):
    e = db.get(TimelineEvent, parse_id(event_id, "event_id"))
    if not e:
        raise HTTPException(status_code=404, detail="Event not found")
    meta = e.metadata_json or {}
    return {
        "id": str(e.id),
        "type": e.type,
        "title": e.title,
        "summary": e.summary,
        "occurred_at": e.occurred_at,
        "end_at": e.end_at,
        "confidence": e.confidence,
        "provenance": e.provenance,
        "components": meta.get("components", []),
        "artifact_ids": meta.get("artifact_ids", []),
        "metadata": meta,
    }


@router.patch("/timeline-events/{event_id}")
def patch_event(event_id: str, body: EventPatchIn, user_id: str | None = Depends(optional_user), db: Session = Depends(get_db)):
    e = db.get(TimelineEvent, parse_id(event_id, "event_id"))
    if not e:
        raise HTTPException(status_code=404, detail="Event not found")
    updates = body.model_dump(exclude_unset=True)
    if "title" in updates:
        e.title = updates["title"]
    if "summary" in updates:
        e.summary = updates["summary"]
    if updates.get("confirmed"):
        e.provenance = "user-confirmed"
    db.commit()
    return {"ok": True}


@router.get("/snapshots/{snapshot_id}/hotspots")
def get_hotspots(snapshot_id: str, user_id: str | None = Depends(optional_user), db: Session = Depends(get_db)):
    snap = _get_snapshot(db, snapshot_id)
    mv = db.query(MetricValue).filter(
        MetricValue.snapshot_id == snap.id,
        MetricValue.key == "churn",
    ).first()
    if not mv:
        return {"hotspots": [], "concentration": None}
    return {
        "hotspots": (mv.raw_value_json or {}).get("hotspots", []),
        "concentration": (mv.raw_value_json or {}).get("concentration"),
    }


@router.get("/snapshots/{snapshot_id}/metrics")
def get_metrics(snapshot_id: str, user_id: str | None = Depends(optional_user), db: Session = Depends(get_db)):
    snap = _get_snapshot(db, snapshot_id)
    mvs = db.query(MetricValue).filter(MetricValue.snapshot_id == snap.id).all()
    return [
        {
            "key": mv.key,
            "raw_value": mv.raw_value_json,
            "normalized_value": mv.normalized_value,
            "extractor_version": mv.extractor_version,
            "evidence": (mv.evidence_json or {}).get("evidence_ids", []),
        }
        for mv in mvs
    ]