import datetime
import os

import requests

AD_ACCOUNT_ID = os.environ["META_AD_ACCOUNT_ID"]
ACCESS_TOKEN = os.environ["META_ACCESS_TOKEN"]
DISCORD_WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]

GRAPH_API_VERSION = "v21.0"
INSIGHTS_URL = f"https://graph.facebook.com/{GRAPH_API_VERSION}/act_{AD_ACCOUNT_ID}/insights"

FIELDS = [
    "campaign_name",
    "spend",
    "impressions",
    "clicks",
    "ctr",
    "cpc",
    "reach",
    "frequency",
    "actions",
]

GENDER_LABELS = {"male": "남", "female": "여", "unknown": "기타"}


def get_campaign_insights(date):
    """Meta Marketing API insights로 하루치 캠페인별 성과를 조회한다.

    해당 날짜에 지출/노출이 없던 캠페인은 응답에 아예 포함되지 않는다.
    """
    params = {
        "level": "campaign",
        "fields": ",".join(FIELDS),
        "time_range": f'{{"since":"{date}","until":"{date}"}}',
        "access_token": ACCESS_TOKEN,
    }
    resp = requests.get(INSIGHTS_URL, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()["data"]


def get_gender_installs(date):
    """캠페인별 성별 앱설치 breakdown을 {campaign_name: {gender: installs}} 형태로 반환한다."""
    params = {
        "level": "campaign",
        "fields": "campaign_name,actions",
        "breakdowns": "gender",
        "time_range": f'{{"since":"{date}","until":"{date}"}}',
        "access_token": ACCESS_TOKEN,
    }
    resp = requests.get(INSIGHTS_URL, params=params, timeout=15)
    resp.raise_for_status()

    result = {}
    for row in resp.json()["data"]:
        installs = get_action_count(row, "mobile_app_install")
        if installs == 0:
            continue
        result.setdefault(row["campaign_name"], {})[row["gender"]] = installs
    return result


def format_krw(value):
    return f"{round(float(value)):,}"


def get_action_count(row, action_type):
    """actions 배열에서 지정한 action_type 값을 뽑는다. 없으면 0."""
    for action in row.get("actions", []):
        if action["action_type"] == action_type:
            return int(action["value"])
    return 0


def escape_discord(text):
    """Discord 마크다운 특수문자(_, *, ~)를 이스케이프해 캠페인명이 그대로 보이게 한다."""
    for char in ("\\", "_", "*", "~", "`"):
        text = text.replace(char, f"\\{char}")
    return text


def main():
    yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()

    insights = get_campaign_insights(yesterday)
    gender_installs = get_gender_installs(yesterday) if insights else {}

    if not insights:
        lines = [
            f"📢 **Meta 광고 일간 리포트 · {yesterday}**",
            "어제 지출/노출이 발생한 캠페인이 없습니다.",
            "",
            "-# neki · Meta Ads 자동 리포트",
        ]
    else:
        total_spend = sum(float(row["spend"]) for row in insights)

        lines = [
            f"📢 **Meta 광고 일간 리포트 · {yesterday}**",
            f"💰 총 지출 **₩{format_krw(total_spend)}**",
            "",
        ]
        for row in sorted(insights, key=lambda r: float(r["spend"]), reverse=True):
            spend = format_krw(row["spend"])
            impressions = row.get("impressions", "0")
            clicks = row.get("clicks", "0")
            ctr = round(float(row.get("ctr", 0)), 2)
            cpc = row.get("cpc")
            cpc_display = f"₩{format_krw(cpc)}" if cpc else "-"
            reach = row.get("reach", "0")
            frequency = round(float(row.get("frequency", 0)), 2)
            installs = get_action_count(row, "mobile_app_install")
            activations = get_action_count(row, "omni_activate_app")
            cpi_display = f"₩{format_krw(float(row['spend']) / installs)}" if installs else "-"

            genders = gender_installs.get(row["campaign_name"], {})
            gender_display = "  ".join(
                f"{GENDER_LABELS.get(g, g)} {c}건"
                for g, c in sorted(genders.items(), key=lambda item: -item[1])
            )

            lines.append(
                f"**{escape_discord(row['campaign_name'])}**\n"
                f"• 지출 ₩{spend}  |  노출 {impressions}  |  클릭 {clicks}\n"
                f"• CTR {ctr}%  |  CPC {cpc_display}\n"
                f"• 도달 {reach}명  |  빈도 {frequency}회\n"
                f"• 앱설치 {installs}건  |  CPI {cpi_display}  |  앱활성화 {activations}건"
                + (f"\n• 설치 성별 {gender_display}" if gender_display else "")
            )
        lines += ["", "-# neki · Meta Ads 자동 리포트"]

    payload = {
        "username": "네키 Meta Ads 봇",
        "avatar_url": "https://i.ifh.cc/PbdkGM.jpg",
        "content": "\n".join(lines),
    }

    print("--- 전송 내용 ---")
    print(payload["content"])
    print("-----------------")

    resp = requests.post(DISCORD_WEBHOOK_URL, json=payload)
    resp.raise_for_status()
    print(f"전송 완료: {resp.status_code} / {yesterday}")


if __name__ == "__main__":
    main()
