"""Unit tests for LLM prompt building and output validation."""

import json

from app.llm.prompts import PROMPT_VERSION, build_messages, validate_output


def test_prompt_version():
    assert PROMPT_VERSION == "dna-summary-v1"


def test_build_messages_contains_evidence():
    system, user = build_messages(
        project_name="team/wardrobe-api",
        snapshot_sha="abc123",
        timeline_text="- release: v1.0.0 (observed)",
        dna_text="- maintainability: 64 (coverage 0.63, low)",
        decisions_text="- Replace MongoDB with PostgreSQL [accepted]",
        experiments_text="- Recommendations engine -> rejected",
    )
    assert "team/wardrobe-api" in user
    assert "v1.0.0" in user
    assert "MongoDB" in user
    assert "evidence" in system.lower()


def test_validate_output_accepts_clean_json():
    text = json.dumps({
        "summary": "Project added PostgreSQL.",
        "highlights": ["DB migration merged"],
        "uncertainties": ["No performance data"],
    })
    parsed, status, reason = validate_output(text)
    assert status == "ok"
    assert parsed["summary"] == "Project added PostgreSQL."
    assert reason == ""


def test_validate_output_strips_fences():
    text = "```json\n{\"summary\": \"x\", \"highlights\": [\"y\"], \"uncertainties\": []}\n```"
    parsed, status, _ = validate_output(text)
    assert status == "ok"
    assert parsed["summary"] == "x"


def test_validate_output_rejects_bad_json():
    _, status, reason = validate_output("this is not json")
    assert status == "unvalidated"
    assert "Invalid JSON" in reason


def test_validate_output_rejects_missing_keys():
    _, status, reason = validate_output('{"summary": "only"}')
    assert status == "unvalidated"
    assert "Missing required keys" in reason


def test_validate_output_rejects_empty_summary():
    _, status, _ = validate_output('{"summary": "  ", "highlights": [], "uncertainties": []}')
    assert status == "unvalidated"
