"""GA4 일간 리포트를 aggregation ingest API로 전송한다.

`build_payload`는 GA4에서 모은 데이터를 LLD §2.2 페이로드 스키마로 변환하는
순수 함수다(서드파티 의존 없음 → 단위 테스트 용이). `post_report`는 실제 HTTP
전송으로, 일시적 오류만 지수 backoff 재시도한다.

Refs: LLD §2.2, ADR-0003
"""

from __future__ import annotations

import logging
import time

logger = logging.getLogger(__name__)

PROPERTY_ID = "524989384"
SCHEMA_VERSION = "1.0"
REPORT_TYPE = "ga4-daily-report"
NOT_SET = "(not set)"

# 일시적 오류로 보고 재시도하는 HTTP 상태 코드 (LLD §2.4).
RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})


def _event_stat(count: int, users: int | None) -> dict[str, int]:
    stat: dict[str, int] = {"count": count}
    if users is not None:
        stat["users"] = users
    return stat


def _breakdown(counts: dict[str, int]) -> list[dict[str, object]]:
    """디멘션 값별 카운트를 count 내림차순 리스트로. `(not set)`는 제외."""
    rows = [{"value": value, "count": count} for value, count in counts.items() if value != NOT_SET]
    rows.sort(key=lambda r: (-r["count"], r["value"]))
    return rows


def build_payload(
    *,
    report_date: str,
    generated_at: str,
    events: dict[str, int],
    users: dict[str, int],
    dimensions: dict[str, dict[str, int]],
    property_id: str = PROPERTY_ID,
    schema_version: str = SCHEMA_VERSION,
) -> dict[str, object]:
    """GA4 집계 데이터를 ingest 페이로드(dict)로 만든다.

    Args:
        report_date: KST 기준 보고 일자 (YYYY-MM-DD).
        generated_at: 페이로드 생성 시각 (ISO 8601 UTC).
        events: 이벤트명 -> eventCount.
        users: 이벤트명 -> totalUsers (events와 같은 키 집합 가정, 없으면 생략).
        dimensions: 디멘션 키(`<event>.<field>`) -> {디멘션값: count}.
    """
    payload: dict[str, object] = {
        "schema_version": schema_version,
        "report_date": report_date,
        "report_type": REPORT_TYPE,
        "generated_at": generated_at,
        "source": {"property_id": property_id},
        "events": {name: _event_stat(count, users.get(name)) for name, count in events.items()},
    }

    dims = {key: rows for key, counts in dimensions.items() if (rows := _breakdown(counts))}
    if dims:
        payload["dimensions"] = dims

    return payload


def post_report(
    url: str,
    payload: dict[str, object],
    *,
    max_retries: int = 3,
    base_delay: float = 1.0,
) -> dict[str, object]:
    """ingest API에 페이로드를 POST한다.

    200이면 응답 body(dict)를 반환한다. 429/5xx/네트워크 오류는 지수 backoff로
    최대 `max_retries`회 재시도한다. 4xx(우리 페이로드 버그)는 응답 body를 남기고
    즉시 예외를 던진다(재시도 무의미). 재시도 소진 시에도 예외.

    Refs: LLD §2.4
    """
    import requests  # 지연 import: 빌더 단위 테스트가 requests 없이 동작하도록

    last_error: str | None = None
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.post(url, json=payload, timeout=10)
        except requests.RequestException as exc:
            last_error = f"네트워크 오류: {exc}"
            logger.warning("ingest 전송 실패 (시도 %d/%d): %s", attempt, max_retries, exc)
        else:
            if resp.status_code == 200:
                body = resp.json()
                logger.info("ingest 저장 성공: %s", body.get("object_key"))
                return body
            if resp.status_code not in RETRYABLE_STATUS:
                raise RuntimeError(f"ingest 실패 (비재시도) {resp.status_code}: {resp.text}")
            last_error = f"{resp.status_code}: {resp.text}"
            logger.warning(
                "ingest 재시도 가능 응답 (시도 %d/%d): %s",
                attempt,
                max_retries,
                last_error,
            )

        if attempt < max_retries:
            time.sleep(base_delay * (2 ** (attempt - 1)))

    raise RuntimeError(f"ingest 재시도 소진 ({max_retries}회): {last_error}")
