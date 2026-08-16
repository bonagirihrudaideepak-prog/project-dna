"""Evolution graph builder.

Constructs a bounded, evidence-first graph of nodes (Project, Snapshot, Phase,
Event, Decision, Experiment, Component, Technology, Outcome) and typed edges
with provenance. Stored as ordinary PostgreSQL tables; a graph database is
unnecessary for the MVP.
"""

from __future__ import annotations

from typing import Any


def build_graph(
    project: dict[str, Any],
    snapshot: dict[str, Any] | None,
    events: list[dict],
    decisions: list[dict] | None = None,
    experiments: list[dict] | None = None,
) -> tuple[list[dict], list[dict]]:
    """Return (nodes, edges). Each node has a stable logical key for dedup."""
    nodes: dict[str, dict] = {}
    edges: list[dict] = []

    def node(node_type: str, entity_type: str, entity_id: str, label: str, meta: dict | None = None):
        key = f"{entity_type}:{entity_id}"
        if key not in nodes:
            nodes[key] = {
                "key": key,
                "node_type": node_type,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "label": label,
                "metadata_json": meta or {},
            }
        return key

    def edge(source_key: str, target_key: str, edge_type: str, provenance: str, confidence: float, evidence: dict | None = None):
        edges.append({
            "source": source_key,
            "target": target_key,
            "edge_type": edge_type,
            "provenance": provenance,
            "confidence": confidence,
            "evidence_json": evidence or {},
        })

    project_key = node("project", "project", str(project.get("id") or project.get("full_name")), project.get("full_name") or project.get("name") or "Project")
    snapshot_key = None
    if snapshot:
        snapshot_key = node("snapshot", "snapshot", str(snapshot.get("id")), f"Snapshot {snapshot.get('commit_sha', '')[:8]}", snapshot)
        edge(project_key, snapshot_key, "CONTAINS", "observed", 1.0)

    components_seen: set[str] = set()
    for ev in events:
        ev_key = node("event", "event", str(ev.get("id") or ev.get("title")), ev.get("title") or "Event", ev)
        if snapshot_key:
            edge(snapshot_key, ev_key, "CONTAINS", ev.get("provenance") or "observed", float(ev.get("confidence") or 1.0))
        for comp in (ev.get("metadata_json") or {}).get("components", []):
            comp_key = node("component", "component", comp, comp)
            components_seen.add(comp)
            edge(ev_key, comp_key, "AFFECTED", "rule-derived", 0.8)

    for d in decisions or []:
        d_key = node("decision", "decision", str(d.get("id")), d.get("title") or "Decision", d)
        if snapshot_key:
            edge(snapshot_key, d_key, "CONTAINS", "user", 1.0)
        for comp in (d.get("expected_impact") or {}).get("components", []) if isinstance(d.get("expected_impact"), dict) else []:
            comp_key = node("component", "component", comp, comp)
            edge(d_key, comp_key, "AFFECTED", "user", 1.0)
        for review in d.get("outcome_reviews") or []:
            o_key = node("outcome", "outcome", str(review.get("id")), f"Review: {review.get('verdict', 'neutral')}", review)
            edge(d_key, o_key, "RESULTED_IN", "user", 1.0)

    for e in experiments or []:
        e_key = node("experiment", "experiment", str(e.get("id")), e.get("title") or "Experiment", e)
        if snapshot_key:
            edge(snapshot_key, e_key, "CONTAINS", "user", 1.0)

    for comp in components_seen:
        edge(project_key, f"component:{comp}", "CONTAINS", "rule-derived", 0.9)

    return list(nodes.values()), edges


def query_bounded(nodes: list[dict], edges: list[dict], focus_key: str, depth: int = 1) -> dict:
    """Return a bounded subgraph around focus_key at given hop depth."""
    by_key = {n["key"]: n for n in nodes}
    adjacency: dict[str, list[str]] = {}
    for e in edges:
        adjacency.setdefault(e["source"], []).append(e["target"])
        adjacency.setdefault(e["target"], []).append(e["source"])

    included: set[str] = set()
    frontier = {focus_key}
    for _ in range(depth):
        included |= frontier
        nxt: set[str] = set()
        for k in frontier:
            nxt |= set(adjacency.get(k, []))
        frontier = nxt - included
    included |= frontier

    focus = by_key.get(focus_key)
    if not focus:
        return {"nodes": [], "edges": [], "focus": None}
    sel_nodes = [n for k, n in by_key.items() if k in included]
    sel_edges = [e for e in edges if e["source"] in included and e["target"] in included]
    return {"nodes": sel_nodes, "edges": sel_edges, "focus": focus}