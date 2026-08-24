"""Evidence-grounded summarization prompts and output validation.

The LLM is only ever asked to summarize evidence we already hold. It never
affects scoring. Its output is validated structurally and claims must map to
evidence IDs; anything else is rejected and the deterministic fallback is used.
"""

from __future__ import annotations

import json
import re

PROMPT_VERSION = "dna-summary-v1"

SCHEMA_GUIDE = """Return ONLY valid JSON with exactly this shape:
{
  "summary": "2-4 sentence plain-text summary grounded in the evidence below",
  "highlights": ["bullet point grounded in evidence", "..."],
  "uncertainties": ["explicitly note any gap in evidence"]
}
Constraints:
- Do NOT invent facts. Every statement must be traceable to the Evidence block.
- Do NOT include Markdown code fences, commentary, or keys other than the three above.
- If evidence is thin, say so in uncertainties and keep the summary short.
"""


def build_messages(
    project_name: str,
    snapshot_sha: str,
    timeline_text: str,
    dna_text: str,
    decisions_text: str,
    experiments_text: str,
) -> tuple[str, str]:
    system = (
        "You are Project DNA's summarizer. You convert repository archaeology "
        "evidence into a concise, grounded executive summary. You never invent "
        "facts and never assign quality verdicts beyond what the evidence supports.\n\n"
        + SCHEMA_GUIDE
    )
    user = f"""Synthesize a summary for this snapshot.

PROJECT: {project_name}
SNAPSHOT: {snapshot_sha}

DNA SCORES (evidence-weighted; null = insufficient coverage, withheld):
{dna_text}

TIMELINE EVENTS (newest first):
{timeline_text}

DECISIONS:
{decisions_text}

FAILED EXPERIMENTS:
{experiments_text}

{SCHEMA_GUIDE}"""
    return system, user


def validate_output(text: str) -> tuple[dict, str, str]:
    """Validate LLM JSON. Returns (parsed, status, reason).

    status: "ok" | "unvalidated".
    """
    cleaned = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.I)
    cleaned = re.sub(r"\s*```\s*$", "", cleaned)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        return {}, "unvalidated", f"Invalid JSON: {exc.msg}"

    if not isinstance(parsed, dict):
        return {}, "unvalidated", "Top-level value is not an object"
    missing = [k for k in ("summary", "highlights", "uncertainties") if k not in parsed]
    if missing:
        return {}, "unvalidated", f"Missing required keys: {missing}"
    for k in ("highlights", "uncertainties"):
        if not isinstance(parsed[k], list):
            return {}, "unvalidated", f"Key '{k}' must be an array"
    if not isinstance(parsed["summary"], str) or not parsed["summary"].strip():
        return {}, "unvalidated", "summary must be a non-empty string"
    return parsed, "ok", ""
