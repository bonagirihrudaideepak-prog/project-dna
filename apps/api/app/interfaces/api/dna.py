"""DNA, timeline, hotspots, and change exploration endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ...adapters.cache_service import CacheService
from ...adapters.db import get_db
from ...config import settings
from ...models import DNAScore, MetricValue, RepositorySnapshot, TimelineEvent
from ..deps import current_user, optional_user, parse_id
from ..schemas import EventPatchIn
from .projects import require_membership

router = APIRouter(tags=["dna"])

# Module-level cache service instance
_cache_service = CacheService()


def _get_snapshot(db: Session, snapshot_id: str, user_id: str | None = None) -> RepositorySnapshot:
    sid = parse_id(snapshot_id, "snapshot_id")
    snap = db.get(RepositorySnapshot, sid)
    if not snap:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    require_membership(db, snap.project_id, user_id)
    return snap


@router.get("/snapshots/{snapshot_id}/dna")
def get_dna(snapshot_id: str, user_id: str | None = Depends(optional_user), db: Session = Depends(get_db)):
    snap = _get_snapshot(db, snapshot_id, user_id)
    cache_key = f"dna:{snap.id}"
    cached = _cache_service.get(cache_key)
    if cached is not None:
        return cached
    scores = db.query(DNAScore).filter(DNAScore.snapshot_id == snap.id).all()
    payload = [
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
    _cache_service.set(cache_key, payload, ttl=settings.cache_dna_ttl)
    return payload


@router.get("/snapshots/{snapshot_id}/dna/{dimension}")
def get_dna_dimension(snapshot_id: str, dimension: str, user_id: str | None = Depends(optional_user), db: Session = Depends(get_db)):
    snap = _get_snapshot(db, snapshot_id, user_id)
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
    snap = _get_snapshot(db, snapshot_id, user_id)
    # Only the unfiltered view is cached; filtered variants are rare and cheap.
    cache_key = f"timeline:{snap.id}"
    if event_type is None and component is None:
        cached = _cache_service.get(cache_key)
        if cached is not None:
            return cached
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
            "occurred_at": e.occurred_at.isoformat() if e.occurred_at else None,
            "end_at": e.end_at.isoformat() if e.end_at else None,
            "confidence": e.confidence,
            "provenance": e.provenance,
            "components": meta.get("components", []),
            "artifact_ids": meta.get("artifact_ids", []),
            "metadata": meta,
        })
    if event_type is None and component is None:
        _cache_service.set(cache_key, out, ttl=settings.cache_dna_ttl)
    return out


@router.get("/timeline-events/{event_id}")
def get_event(event_id: str, user_id: str | None = Depends(optional_user), db: Session = Depends(get_db)):
    e = db.get(TimelineEvent, parse_id(event_id, "event_id"))
    if not e:
        raise HTTPException(status_code=404, detail="Event not found")
    require_membership(db, e.snapshot.project_id, user_id)
    meta = e.metadata_json or {}
    return {
        "id": str(e.id),
        "type": e.type,
        "title": e.title,
        "summary": e.summary,
        "occurred_at": e.occurred_at.isoformat() if e.occurred_at else None,
        "end_at": e.end_at.isoformat() if e.end_at else None,
        "confidence": e.confidence,
        "provenance": e.provenance,
        "components": meta.get("components", []),
        "artifact_ids": meta.get("artifact_ids", []),
        "metadata": meta,
    }


@router.patch("/timeline-events/{event_id}")
def patch_event(event_id: str, body: EventPatchIn, user_id: str = Depends(current_user), db: Session = Depends(get_db)):
    e = db.get(TimelineEvent, parse_id(event_id, "event_id"))
    if not e:
        raise HTTPException(status_code=404, detail="Event not found")
    require_membership(db, e.snapshot.project_id, user_id)
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
    snap = _get_snapshot(db, snapshot_id, user_id)
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
    snap = _get_snapshot(db, snapshot_id, user_id)
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