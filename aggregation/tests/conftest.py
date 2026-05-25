import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
SRC_DIR = ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

KST = timezone(timedelta(hours=9))


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("S3_BUCKET", "test-bucket")
    monkeypatch.setenv("S3_PREFIX", "aggregation")
    monkeypatch.setenv("REPORT_DATE_MAX_AGE_DAYS", "7")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "ap-northeast-2")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")


@pytest.fixture
def fixture_payload():
    """Load valid payload fixture and set report_date to KST yesterday."""
    with (Path(__file__).parent / "fixtures" / "valid_payload.json").open() as f:
        payload = json.load(f)
    yesterday = (datetime.now(KST).date() - timedelta(days=1)).isoformat()
    payload["report_date"] = yesterday
    return payload


class _Context:
    aws_request_id = "test-request-id"


@pytest.fixture
def context():
    return _Context()
