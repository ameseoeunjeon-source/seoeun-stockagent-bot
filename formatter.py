"""리포트 텍스트 구성. 예시 형식을 최대한 따른다."""
from datetime import datetime
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")


def _now_str():
    n = datetime.now(KST)
    return n.strftime("%H시 %M분")


def _emoji_label(label):
    return {
        "극단적 공포": "😱", "공포": "😨", "중립": "😐",
        "탐욕": "🤑", "극단적 탐욕": "🚀",
    }.get(label, "🌡️")


def format_thesis(thesis_result):
    """감시종목 thesis 점검 섹션."""
    head = f"📊 감시종목 thesis 점검 ({_now_str()})\n"
    if thesis_result.get("no_change"):
        return head + "✅ 이상 없음"
    return head + "🚨 변화 감지\n\n" + thesis_result["text"]


def format_market(a, ok_channels, total_channels, post_count):
    """시장 전반 심층 분석 리포트 섹션 (예시 형식)."""
    L = []
    L.append(f"📝 텔레그램 심층 분석 Report ({_now_str()}) 기준\n")

    emo = _emoji_label(a["sentiment_label"])
    L.append(f"{emo} 센티먼트 {a['sentiment_label']} ({a['sentiment_score']})")
    L.append(f"💡 요약 {a['summary']}\n")

    if a["keywords"]:
        parts = []
        for k, c in a["keywords"]:
            parts.append(f"{k}({c})" if isinstance(c, int) and c > 0 else f"{k}")
        L.append(f"🗣️ Top 키워드: {', '.join(parts)}\n")

    if a["stocks"]:
        L.append("🔥 주목받는 종목")
        for s in a["stocks"]:
            arrow = "📈" if s["score"] >= 0 else "📉"
            sign = f"+{s['score']}" if s["score"] >= 0 else str(s["score"])
            L.append(f"{arrow} {s['name']} ({sign})")
            if s["reason"]:
                L.append(f"   {s['reason']}")
        L.append("")

    L.append(f"🎉 {ok_channels}개 채널에서 게시글 {post_count}개 수집 완료!\n")

    if a["popular"]:
        L.append("🔥 현시점 인기 게시글 TOP %d\n" % len(a["popular"]))
        for i, p in enumerate(a["popular"], 1):
            snippet = p["text"].split("\n")[0][:50]
            L.append(f"[{i}위] {p['views']:,} 👁️ | {p['forwards']} 📤")
            L.append(f"📺 {p['channel']}")
            L.append(f"📝 {snippet}...")
            L.append(f"🔗 {p['url']}\n")

    L.append("ℹ️ 스코어링: 최근 게시글의 감정(-100~100)과 공유 횟수를 종합 분석합니다.")
    return "\n".join(L)


def split_for_telegram(text, limit=4000):
    """텔레그램 4096자 제한 대응. 줄 단위로 안전 분할."""
    if len(text) <= limit:
        return [text]
    chunks, cur = [], ""
    for line in text.split("\n"):
        if len(cur) + len(line) + 1 > limit:
            chunks.append(cur)
            cur = ""
        cur += line + "\n"
    if cur.strip():
        chunks.append(cur)
    return chunks
