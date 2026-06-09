import json
from pathlib import Path

import pytest
from ingest import build_payload
from jsonschema import Draft7Validator

SCHEMA_PATH = (
    Path(__file__).parent.parent.parent
    / "aggregation"
    / "src"
    / "schemas"
    / "ga4-daily-report.v1.json"
)


@pytest.fixture
def schema():
    with SCHEMA_PATH.open(encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def sample_kwargs():
    return {
        "report_date": "2026-05-24",
        "generated_at": "2026-05-25T01:00:00Z",
        "events": {"session_start": 123, "first_open": 45, "map_view": 100},
        "users": {"session_start": 123, "first_open": 45, "map_view": 80},
        "dimensions": {
            "map_brand_filter_toggle.brand_name": {"MUSINSA": 10, "(not set)": 7},
            "photo_upload.method": {"gallery": 30, "qr": 5},
        },
    }


def test_payload_matches_schema(schema, sample_kwargs):
    payload = build_payload(**sample_kwargs)
    Draft7Validator(schema).validate(payload)


def test_constants_and_source(sample_kwargs):
    payload = build_payload(**sample_kwargs)
    assert payload["schema_version"] == "1.0"
    assert payload["report_type"] == "ga4-daily-report"
    assert payload["source"] == {"property_id": "524989384"}
    assert payload["report_date"] == "2026-05-24"
    assert payload["generated_at"] == "2026-05-25T01:00:00Z"


def test_events_map_count_and_users(sample_kwargs):
    payload = build_payload(**sample_kwargs)
    assert payload["events"]["session_start"] == {"count": 123, "users": 123}
    assert payload["events"]["map_view"] == {"count": 100, "users": 80}


def test_event_without_users_omits_users(sample_kwargs):
    sample_kwargs["events"] = {"orphan_event": 9}
    sample_kwargs["users"] = {}
    payload = build_payload(**sample_kwargs)
    assert payload["events"]["orphan_event"] == {"count": 9}


def test_dimension_filters_not_set_and_sorts_desc(sample_kwargs):
    sample_kwargs["dimensions"]["map_brand_filter_toggle.brand_name"] = {
        "MUSINSA": 3,
        "(not set)": 99,
        "ADIDAS": 10,
    }
    payload = build_payload(**sample_kwargs)
    brand = payload["dimensions"]["map_brand_filter_toggle.brand_name"]
    assert {"value": "(not set)", "count": 99} not in brand
    assert brand == [
        {"value": "ADIDAS", "count": 10},
        {"value": "MUSINSA", "count": 3},
    ]


def test_empty_dimension_key_dropped(sample_kwargs):
    sample_kwargs["dimensions"] = {
        "map_brand_filter_toggle.brand_name": {"(not set)": 5},
        "photo_upload.method": {"gallery": 1},
    }
    payload = build_payload(**sample_kwargs)
    dims = payload["dimensions"]
    assert "map_brand_filter_toggle.brand_name" not in dims
    assert "photo_upload.method" in dims


def test_no_dimensions_omits_key(sample_kwargs):
    sample_kwargs["dimensions"] = {}
    payload = build_payload(**sample_kwargs)
    assert "dimensions" not in payload
