"""Export service: JSON and print-friendly HTML project reports."""

from __future__ import annotations

import json
from html import escape
from typing import Any


def build_export_payload(snapshot_data: dict[str, Any]) -> dict[str, Any]:
    return {
        "project": snapshot_data.get("project"),
        "snapshot": snapshot_data.get("snapshot"),
        "dna": snapshot_data.get("dna", []),
        "timeline": snapshot_data.get("timeline", []),
        "decisions": snapshot_data.get("decisions", []),
        "experiments": snapshot_data.get("experiments", []),
        "warnings": snapshot_data.get("warnings", []),
    }


def to_json(snapshot_data: dict[str, Any]) -> str:
    payload = build_export_payload(snapshot_data)
    return json.dumps(payload, indent=2, default=str)


def to_print_html(snapshot_data: dict[str, Any]) -> str:
    project = snapshot_data.get("project") or {}
    snapshot = snapshot_data.get("snapshot") or {}
    dna = snapshot_data.get("dna", []) or []
    timeline = snapshot_data.get("timeline", []) or []
    decisions = snapshot_data.get("decisions", []) or []
    experiments = snapshot_data.get("experiments", []) or []

    dna_rows = "".join(
        f"<tr><td>{escape(d.get('dimension',''))}</td>"
        f"<td>{d.get('score') if d.get('score') is not None else '&mdash;'}</td>"
        f"<td>{d.get('coverage','')}</td><td>{escape(d.get('confidence',''))}</td></tr>"
        for d in dna
    )
    tl_rows = "".join(
        f"<tr><td>{escape(t.get('type',''))}</td><td>{escape(t.get('title',''))}</td>"
        f"<td>{escape(str(t.get('occurred_at') or ''))}</td><td>{escape(t.get('provenance',''))}</td></tr>"
        for t in timeline
    )
    dec_rows = "".join(
        f"<tr><td>{escape(d.get('title',''))}</td><td>{escape(d.get('status',''))}</td>"
        f"<td>{escape(d.get('decided_at','') or '')}</td></tr>"
        for d in decisions
    )
    exp_rows = "".join(
        f"<tr><td>{escape(e.get('title',''))}</td><td>{escape(e.get('decision',''))}</td>"
        f"<td>{escape(e.get('evaluated_at','') or '')}</td></tr>"
        for e in experiments
    )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Project DNA report - {escape(project.get('full_name',''))}</title>
<style>
body{{font-family:system-ui,sans-serif;max-width:900px;margin:40px auto;color:#1a1a1a;line-height:1.5}}
h1,h2{{border-bottom:2px solid #333;padding-bottom:4px}}
table{{border-collapse:collapse;width:100%;margin:16px 0}}
th,td{{border:1px solid #ccc;padding:8px 10px;text-align:left}}
th{{background:#f3f3f3}}
.score{{font-size:1.4em;font-weight:700}}
@media print{{body{{margin:20px}}}}
</style>
</head>
<body>
<h1>Project DNA Report</h1>
<p><strong>{escape(project.get('full_name',''))}</strong> &mdash; {escape(project.get('description','') or '')}</p>
<p>Snapshot: <code>{escape(str(snapshot.get('commit_sha',''))[:12])}</code> &middot; Analyzer {escape(str(snapshot.get('analyzer_version','')))} &middot; Model {escape(str(snapshot.get('score_model_version','')))} &middot; Captured {escape(str(snapshot.get('captured_at','')))}</p>

<h2>DNA Profile</h2>
<table><tr><th>Dimension</th><th>Score</th><th>Coverage</th><th>Confidence</th></tr>{dna_rows}</table>

<h2>Timeline</h2>
<table><tr><th>Type</th><th>Title</th><th>Date</th><th>Provenance</th></tr>{tl_rows}</table>

<h2>Decisions</h2>
<table><tr><th>Title</th><th>Status</th><th>Date</th></tr>{dec_rows}</table>

<h2>Failed Experiments</h2>
<table><tr><th>Title</th><th>Decision</th><th>Date</th></tr>{exp_rows}</table>

<h2>Warnings</h2>
<ul>{''.join(f'<li>{escape(str(w))}</li>' for w in (snapshot_data.get('warnings') or []))}</ul>
</body>
</html>"""