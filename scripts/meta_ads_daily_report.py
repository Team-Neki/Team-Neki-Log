import datetime
import os

import requests

AD_ACCOUNT_ID = os.environ["META_AD_ACCOUNT_ID"]
ACCESS_TOKEN = os.environ["META_ACCESS_TOKEN"]
DISCORD_WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]

GRAPH_API_VERSION = "v21.0"
INSIGHTS_URL = f"https://graph.facebook.com/{GRAPH_API_VERSION}/act_{AD_ACCOUNT_ID}/insights"

FIELDS = ["campaign_name", "spend", "impressions", "clicks", "ctr", "cpc"]


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


def format_krw(value):
    return f"{round(float(value)):,}"


def main():
    yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()

    insights = get_campaign_insights(yesterday)

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
            ctr = row.get("ctr", "0")
            cpc = row.get("cpc")
            cpc_display = f"₩{format_krw(cpc)}" if cpc else "-"
            lines.append(
                f"**{row['campaign_name']}**\n"
                f"지출 ₩{spend}  |  노출 {impressions}  |  클릭 {clicks}  |  "
                f"CTR {ctr}%  |  CPC {cpc_display}"
            )
        lines += ["", "-# neki · Meta Ads 자동 리포트"]

    payload = {
        "username": "네키 Meta Ads 봇",
        "avatar_url": "https://i.ifh.cc/PbdkGM.jpg",
        "content": "\n".join(lines),
    }

    resp = requests.post(DISCORD_WEBHOOK_URL, json=payload)
    resp.raise_for_status()
    print(f"전송 완료: {resp.status_code} / {yesterday}")


if __name__ == "__main__":
    main()
