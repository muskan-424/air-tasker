import pytest

from app.services.gemini_task_schema_service import validate_task_schema
from app.services.task_chat_schema_service import build_ai_schema_from_message, resolve_ai_schema


def test_validate_task_schema_accepts_rule_output():
    schema = build_ai_schema_from_message("plumber for tap leak in 110001 budget 800")
    ok, errors = validate_task_schema(schema)
    assert ok, errors


def test_validate_task_schema_rejects_empty_title():
    ok, errors = validate_task_schema({"title": "", "description": "x", "category": "plumbing"})
    assert not ok
    assert any("title" in e for e in errors)


def test_resolve_ai_schema_falls_back_to_rule_without_gemini():
    schema, provider = resolve_ai_schema("need electrician for fan repair budget 600")
    assert provider == "rule"
    assert schema["category"] == "electrical"
    assert schema["title"]


def test_resolve_ai_schema_extracts_pin_into_location():
    schema, provider = resolve_ai_schema(
        "Need electrical repair in Dehradun PIN 110001 with quick turnaround, budget up to 2000 INR"
    )
    assert provider == "rule"
    assert schema["location"] == "110001"
