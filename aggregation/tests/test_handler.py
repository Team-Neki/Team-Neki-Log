import importlib
import json
import sys
from datetime import datetime, timedelta, timezone

import boto3
import pytest
from moto import mock_aws

KST = timezone(timedelta(hours=9))


def _make_event(body, content_type="application/json"):
    if isinstance(body, dict):
        body = json.dumps(body)
    return {"headers": {"content-type": content_type}, "body": body}


def _reload_handler():
    """Reload handler module so module-level boto3 client picks up moto."""
    sys.modules.pop("handler", None)
    return importlib.import_module("handler")


@pytest.fixture
def s3_client():
    with mock_aws():
        client = boto3.client("s3", region_name="ap-northeast-2")
        client.create_bucket(
            Bucket="test-bucket",
            CreateBucketConfiguration={"LocationConstraint": "ap-northeast-2"},
        )
        yield client


def test_valid_payload_stores_and_returns_200(s3_client, fixture_payload, context):
    handler = _reload_handler()
    response = handler.lambda_handler(_make_event(fixture_payload), context)

    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["status"] == "stored"
    assert body["report_date"] == fixture_payload["report_date"]

    obj = s3_client.get_object(Bucket="test-bucket", Key=body["object_key"])
    assert obj["ContentType"] == "application/json; charset=utf-8"
    stored = json.loads(obj["Body"].read())
    assert stored == fixture_payload
    assert obj["Metadata"]["schema-version"] == fixture_payload["schema_version"]
    assert obj["Metadata"]["report-type"] == "ga4-daily-report"


def test_object_key_uses_zero_padded_hive_partition(s3_client, fixture_payload, context):
    handler = _reload_handler()
    fixture_payload["report_date"] = (
        datetime.now(KST).date() - timedelta(days=1)
    ).isoformat()

    response = handler.lambda_handler(_make_event(fixture_payload), context)
    body = json.loads(response["body"])
    key = body["object_key"]

    # aggregation/year=YYYY/month=MM/day=DD/ga4-daily-report.json
    assert key.startswith("aggregation/year=")
    parts = key.split("/")
    assert parts[1].startswith("year=") and len(parts[1].split("=")[1]) == 4
    assert parts[2].startswith("month=") and len(parts[2].split("=")[1]) == 2
    assert parts[3].startswith("day=") and len(parts[3].split("=")[1]) == 2
    assert parts[4] == "ga4-daily-report.json"


def test_non_json_content_type_returns_400(s3_client, fixture_payload, context):
    handler = _reload_handler()
    event = _make_event(fixture_payload, content_type="text/plain")
    response = handler.lambda_handler(event, context)
    assert response["statusCode"] == 400
    assert json.loads(response["body"])["error"]["code"] == "INVALID_JSON"


def test_unparseable_body_returns_400(s3_client, context):
    handler = _reload_handler()
    event = {
        "headers": {"content-type": "application/json"},
        "body": "{not-json",
    }
    response = handler.lambda_handler(event, context)
    assert response["statusCode"] == 400
    assert json.loads(response["body"])["error"]["code"] == "INVALID_JSON"


def test_missing_required_field_returns_400(s3_client, fixture_payload, context):
    handler = _reload_handler()
    del fixture_payload["events"]
    response = handler.lambda_handler(_make_event(fixture_payload), context)
    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert "field" in body["error"]["details"]


def test_additional_property_rejected(s3_client, fixture_payload, context):
    handler = _reload_handler()
    fixture_payload["unexpected_field"] = "x"
    response = handler.lambda_handler(_make_event(fixture_payload), context)
    assert response["statusCode"] == 400
    assert json.loads(response["body"])["error"]["code"] == "VALIDATION_ERROR"


def test_unsupported_schema_version_returns_400(s3_client, fixture_payload, context):
    handler = _reload_handler()
    fixture_payload["schema_version"] = "2.0"
    response = handler.lambda_handler(_make_event(fixture_payload), context)
    # major != 1 → either VALIDATION_ERROR (pattern fail) or UNSUPPORTED_SCHEMA_VERSION
    # schema pattern is ^1\.[0-9]+$, so "2.0" fails schema first
    assert response["statusCode"] == 400
    code = json.loads(response["body"])["error"]["code"]
    assert code in ("VALIDATION_ERROR", "UNSUPPORTED_SCHEMA_VERSION")


def test_minor_version_accepted(s3_client, fixture_payload, context):
    handler = _reload_handler()
    fixture_payload["schema_version"] = "1.5"
    response = handler.lambda_handler(_make_event(fixture_payload), context)
    assert response["statusCode"] == 200


def test_date_too_old_returns_400(s3_client, fixture_payload, context):
    handler = _reload_handler()
    fixture_payload["report_date"] = (
        datetime.now(KST).date() - timedelta(days=30)
    ).isoformat()
    response = handler.lambda_handler(_make_event(fixture_payload), context)
    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert body["error"]["code"] == "DATE_OUT_OF_RANGE"
    assert "min" in body["error"]["details"]
    assert "max" in body["error"]["details"]


def test_date_in_future_returns_400(s3_client, fixture_payload, context):
    handler = _reload_handler()
    fixture_payload["report_date"] = (
        datetime.now(KST).date() + timedelta(days=2)
    ).isoformat()
    response = handler.lambda_handler(_make_event(fixture_payload), context)
    assert response["statusCode"] == 400
    assert json.loads(response["body"])["error"]["code"] == "DATE_OUT_OF_RANGE"


def test_s3_failure_returns_500(fixture_payload, context, monkeypatch):
    """Without moto, boto3 hits real AWS and fails (no creds/bucket)."""
    # Force credentials to point at a non-existent service to fail fast
    handler = _reload_handler()

    def _raise(*args, **kwargs):
        raise Exception("simulated S3 failure")

    monkeypatch.setattr(handler.s3, "put_object", _raise)

    response = handler.lambda_handler(_make_event(fixture_payload), context)
    assert response["statusCode"] == 500
    assert json.loads(response["body"])["error"]["code"] == "STORAGE_ERROR"
