import datetime
import json
import os

import requests

PROJECT_ID = "847661"  # NEKI_PROD
API_KEY = os.environ["AMPLITUDE_API_KEY"]
SECRET_KEY = os.environ["AMPLITUDE_SECRET_KEY"]
DISCORD_WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]

SEGMENTATION_URL = "https://amplitude.com/api/2/events/segmentation"


def query(date, event_type, metric="uniques", group_by=None):
    """Amplitude Event Segmentation API로 특정 이벤트의 하루치 값을 조회한다.

    group_by가 있으면 (label, value) 리스트를, 없으면 단일 값을 반환한다.
    """
    event = {"event_type": event_type}
    if group_by:
        event["group_by"] = group_by

    params = {
        "e": json.dumps(event),
        "start": date,
        "end": date,
        "m": metric,
    }
    resp = requests.get(
        SEGMENTATION_URL,
        params=params,
        auth=(API_KEY, SECRET_KEY),
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()["data"]

    if group_by:
        labels = data.get("seriesLabels", [])
        series = data.get("series", [])
        result = []
        for i, label in enumerate(labels):
            value = label[-1] if isinstance(label, list) else label
            count = series[i][0] if i < len(series) and series[i] else 0
            result.append((value, count))
        return result

    series = data.get("series", [[0]])
    return series[0][0] if series and series[0] else 0


def main():
    yesterday = (datetime.date.today() - datetime.timedelta(days=1)).strftime("%Y%m%d")
    yesterday_display = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()

    dau = query(yesterday, "_active", metric="uniques")
    new_users = query(yesterday, "[Amplitude] Application Installed", metric="uniques")

    def totals_and_users(event_type):
        return query(yesterday, event_type, metric="totals"), query(
            yesterday, event_type, metric="uniques"
        )

    map_view_count, map_view_users = totals_and_users("map_view")
    booth_select_count, booth_select_users = totals_and_users("booth_select")
    pose_view_count, pose_view_users = totals_and_users("pose_view")
    archiving_view_count, archiving_view_users = totals_and_users("archiving_view")

    map_re_search = query(yesterday, "map_re_search", metric="totals")
    map_route_click = query(yesterday, "map_route_click", metric="totals")
    map_brand_filter_toggle = query(yesterday, "map_brand_filter_toggle", metric="totals")
    brand_breakdown = query(
        yesterday,
        "map_brand_filter_toggle",
        metric="totals",
        group_by=[{"type": "event", "value": "brand_name"}],
    )
    booth_favorite_add = query(yesterday, "booth_favorite_add", metric="totals")
    booth_favorite_remove = query(yesterday, "booth_favorite_remove", metric="totals")
    favorite_booth_view = query(yesterday, "favorite_booth_view", metric="totals")

    pose_filter_toggle = query(yesterday, "pose_filter_toggle", metric="totals")
    pose_random_start = query(yesterday, "pose_random_start", metric="totals")
    pose_bookmark = query(yesterday, "pose_bookmark", metric="totals")
    pose_bookmark_filter = query(yesterday, "pose_bookmark_filter", metric="totals")

    photo_detail_view = query(yesterday, "photo_detail_view", metric="totals")
    photo_memo_create = query(yesterday, "photo_memo_create", metric="totals")
    album_create = query(yesterday, "album_create", metric="totals")
    upload_breakdown = dict(
        query(
            yesterday,
            "photo_upload",
            metric="totals",
            group_by=[{"type": "event", "value": "method"}],
        )
    )
    gallery = upload_breakdown.get("gallery", 0)
    qr = upload_breakdown.get("qr", 0)

    notification_click = query(yesterday, "notification_click", metric="totals")
    mypage_logout = query(yesterday, "mypage_logout", metric="totals")
    mypage_withdraw = query(yesterday, "mypage_withdraw", metric="totals")

    brand_lines = [
        f"    └ {name} {count}회" for name, count in brand_breakdown if name and name != "(none)"
    ]

    lines = [
        f"📊 **Amplitude 일간 리포트 · {yesterday_display}**",
        f"👥 DAU **{dau}명**  |  신규(설치) **{new_users}명**  |  🔔 알림 재유입 **{notification_click}회**",
        f"↩️ 로그아웃 **{mypage_logout}회**  |  ⚠️ 탈퇴 **{mypage_withdraw}회**",
        "",
        "🗺 **지도**",
        f"진입 **{map_view_count}회** ({map_view_users}명)",
        f"재검색 **{map_re_search}회**",
        f"브랜드 필터 **{map_brand_filter_toggle}회**",
        *brand_lines,
        f"부스 선택 **{booth_select_count}회** ({booth_select_users}명)",
        f"길찾기 **{map_route_click}회**",
        f"즐겨찾기 추가/삭제 **{booth_favorite_add}회 / {booth_favorite_remove}회**",
        f"즐겨찾기 조회 **{favorite_booth_view}회**",
        "",
        "🧘 **포즈**",
        f"진입 **{pose_view_count}회** ({pose_view_users}명)",
        f"필터 토글 **{pose_filter_toggle}회**",
        f"랜덤 시작 **{pose_random_start}회**",
        f"북마크 **{pose_bookmark}회**  |  북마크 필터 **{pose_bookmark_filter}회**",
        "",
        "📦 **아카이브**",
        f"진입 **{archiving_view_count}회** ({archiving_view_users}명)",
        f"사진 상세 **{photo_detail_view}회**",
        f"메모 작성 **{photo_memo_create}회**",
        f"앨범 생성 **{album_create}회**",
        f"업로드  갤러리 **{gallery}회**  |  QR **{qr}회**",
        "",
        "-# neki · Amplitude 자동 리포트",
    ]

    payload = {
        "username": "네키 Amplitude 봇",
        "avatar_url": "https://i.ifh.cc/PbdkGM.jpg",
        "content": "\n".join(lines),
    }

    resp = requests.post(DISCORD_WEBHOOK_URL, json=payload)
    resp.raise_for_status()
    print(f"전송 완료: {resp.status_code} / {yesterday_display}")


if __name__ == "__main__":
    main()
