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


def test_default_schema_is_in_person_and_flexible():
    schema = build_ai_schema_from_message("plumber for tap leak in 110001 budget 800")
    assert schema["locationType"] == "IN_PERSON"
    assert schema["timing"] == {"type": "FLEXIBLE", "date": None}


def test_remote_keyword_sets_location_type():
    schema = build_ai_schema_from_message("need a remote website fix budget 1500")
    assert schema["locationType"] == "REMOTE"


def test_deadline_keyword_sets_before_date_timing():
    schema = build_ai_schema_from_message("clean the flat before 25/12/2026 budget 900")
    assert schema["timing"] == {"type": "BEFORE_DATE", "date": "2026-12-25"}


def test_on_date_without_deadline_keyword():
    schema = build_ai_schema_from_message("electrician needed on 05/01/2027 budget 700")
    assert schema["timing"] == {"type": "ON_DATE", "date": "2027-01-05"}


def test_validate_task_schema_rejects_bad_location_type():
    ok, errors = validate_task_schema(
        {"title": "x", "description": "x", "category": "plumbing", "locationType": "MARS"}
    )
    assert not ok
    assert any("locationType" in e for e in errors)


def test_validate_task_schema_requires_date_for_on_date_timing():
    ok, errors = validate_task_schema(
        {
            "title": "x",
            "description": "x",
            "category": "plumbing",
            "timing": {"type": "ON_DATE", "date": None},
        }
    )
    assert not ok
    assert any("timing.date" in e for e in errors)
