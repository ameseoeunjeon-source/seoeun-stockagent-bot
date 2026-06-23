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
    """1시간 단위 시장 분석 (섹터 중심)."""
    L = []
    L.append(f"📝 텔레그램 분석 ({_now_str()}, 최근 1시간)\n")

    emo = _emoji_label(a["sentiment_label"])
    L.append(f"{emo} 센티먼트 {a['sentiment_label']} ({a['sentiment_score']})\n")

    if a.get("headline"):
        L.append("🎯 이 시간의 핵심")
        for i, h in enumerate(a["headline"], 1):
            L.append(f"{i}. {h}")
        L.append("")

    if a.get("macro"):
        L.append("📊 시장·매크로")
        L.append(a["macro"])
        L.append("")

    # 내 보유종목 브리핑 (항상 표시 — 포트폴리오를 매시간 챙김)
    holds = a.get("holdings") or []
    total = a.get("holdings_total", 0)
    if holds or total:
        L.append("📌 내 보유종목 브리핑")
        if holds:
            for h in holds:
                L.append(f"▸ {h['name']}")
                L.append(f"   {h['note']}")
            if total and len(holds) < total:
                L.append("▸ 그 외 보유종목: 이번 시간 특이 언급 없음")
        else:
            L.append("▸ 이번 시간 보유종목 관련 특이 언급 없음")
        L.append("")

    if a.get("sectors"):
        L.append("💎 보유·관심 섹터 영향")
        for s in a["sectors"]:
            L.append(f"▸ {s['name']}")
            L.append(f"   {s['summary']}")
        L.append("")

    if a.get("emerging"):
        L.append("📰 신규 부상 (2개+ 채널 동시 언급)")
        for e in a["emerging"]:
            src = f" ({e['sources']})" if e.get("sources") else ""
            note = f": {e['note']}" if e.get("note") else ""
            L.append(f"▸ {e['theme']}{src}{note}")
        L.append("")

    if a.get("actions"):
        L.append("⚠️ 점검 포인트")
        for act in a["actions"]:
            L.append(f"▸ {act}")
        L.append("")

    if a.get("keywords"):
        parts = []
        for k, c in a["keywords"]:
            parts.append(f"{k}({c})" if isinstance(c, int) and c > 0 else f"{k}")
        L.append(f"🗣️ Top 키워드: {', '.join(parts)}\n")

    L.append(f"🎉 {ok_channels}개 채널 / 게시글 {post_count}개 수집\n")

    if a.get("popular"):
        L.append(f"🔥 인기 게시글 TOP {len(a['popular'])}\n")
        for i, p in enumerate(a["popular"], 1):
            summ = p.get("summary")
            line = summ if summ else (p["text"].split("\n")[0][:50] + "…")
            L.append(f"[{i}위] {p['views']:,} 👁️ | {p['forwards']} 📤")
            L.append(f"📺 {p['channel']}")
            L.append(f"📝 {line}")
            L.append(f"🔗 {p['url']}\n")

    L.append("ℹ️ 위 내용은 모니터링 채널 게시글 기반 자동 요약입니다. 투자판단은 본인 책임입니다.")
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
