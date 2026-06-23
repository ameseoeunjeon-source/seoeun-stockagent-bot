"""
분석 엔진.
- 인기 게시글 랭킹: 규칙기반(조회수+공유)
- 시장 분석(센티먼트/요약/키워드/주목종목): LLM이 게시글을 읽고 통째로 생성
  → 예시처럼 깔끔한 종목명 + 한 줄 인사이트 + 의미있는 키워드
- LLM 비활성/실패 시 규칙기반으로 폴백
"""
import re
import json
from collections import Counter, defaultdict

import config
import llm
from lexicon import POSITIVE, NEGATIVE, STOPWORDS

_word_re = re.compile(r"[가-힣A-Za-z0-9]+")


# ----------------------------- 공통 유틸 -----------------------------
def _fear_greed_label(score):
    if score <= -60:
        return "극단적 공포"
    if score <= -20:
        return "공포"
    if score < 20:
        return "중립"
    if score < 60:
        return "탐욕"
    return "극단적 탐욕"


def top_posts(posts, top_n):
    def pop(p):
        return p["views"] + p["forwards"] * 30
    return sorted(posts, key=pop, reverse=True)[:top_n]


# ----------------------------- 규칙기반(폴백/보조) -----------------------------
def sentiment_of(text):
    score = 0
    for word, w in POSITIVE.items():
        if word in text:
            score += w
    for word, w in NEGATIVE.items():
        if word in text:
            score += w
    return max(-100, min(100, score * 8))


def overall_sentiment(posts):
    if not posts:
        return 0, "중립"
    total_w = total = 0.0
    for p in posts:
        w = 1.0 + min(p["forwards"], 500) / 100.0
        total += sentiment_of(p["text"]) * w
        total_w += w
    score = int(total / total_w) if total_w else 0
    return score, _fear_greed_label(score)


def extract_keywords(posts, top_n):
    cnt = Counter()
    for p in posts:
        seen = set()
        for tok in _word_re.findall(p["text"]):
            low = tok.lower()
            if len(tok) < 2 or low in STOPWORDS or tok.isdigit():
                continue
            if tok in seen:
                continue
            seen.add(tok)
            cnt[tok] += 1
    return cnt.most_common(top_n)


def _rule_based(posts):
    """LLM 없이 동작하는 최소 분석."""
    senti, label = overall_sentiment(posts)
    kws = extract_keywords(posts, config.TOP_KEYWORDS)
    # 간단 종목: 감정 강한 인기글에서 첫 줄만
    stocks = []
    for p in top_posts(posts, config.TOP_STOCKS):
        s = sentiment_of(p["text"])
        stocks.append({
            "name": p["channel"], "score": s, "count": 0,
            "reason": p["text"].split("\n")[0][:60],
        })
    summary = (f"현재 시장 투자심리는 '{label}'(센티먼트 {senti})입니다. "
               f"주요 키워드: {', '.join(k for k, _ in kws)}.")
    return {
        "sentiment_score": senti, "sentiment_label": label, "summary": summary,
        "keywords": kws, "stocks": stocks, "popular": top_posts(posts, config.TOP_POSTS),
    }


# ----------------------------- LLM 통합 분석 -----------------------------
_SYSTEM = (
    "너는 한국 주식·테크 텔레그램 채널 수십 개를 모니터링하는 베테랑 애널리스트다. "
    "아래는 최근 1시간 여러 채널에 올라온 게시글이다. 이걸 읽고 '시장 인사이트'를 뽑아라. "
    "링크 나열이 아니라, 사람이 읽고 바로 흐름을 파악할 수 있게 분석해야 한다.\n\n"
    "반드시 아래 JSON 스키마로만 응답:\n"
    "{\n"
    '  "sentiment_score": 정수 (-100~100, -100=극단적 공포, +100=극단적 탐욕),\n'
    '  "summary": "2~3문장. 오늘 시장을 움직이는 핵심 동인과 분위기를 사실 기반으로. 구체적으로.",\n'
    '  "keywords": [["키워드", 등장빈도정수], ...최대 5개. 실제 자주/중요하게 다뤄진 테마·종목. 조사·부사 금지],\n'
    '  "stocks": [\n'
    '     {"name": "정확한 종목명 또는 테마(예: OCI홀딩스, 전선업계, 모바일 D램)",\n'
    '      "score": 정수(-100~100, 호재+/악재-),\n'
    '      "reason": "40자 내외 한 줄. 왜 주목받는지 구체적 사실(수주/실적/가이던스/이벤트)"}\n'
    "     ...주목도 높은 순 최대 10개\n"
    "  ]\n"
    "}\n\n"
    "규칙: 종목명은 절대 잘리거나 토막내지 말 것(예: '하이닉스'를 '이닉스'로 쓰지 말 것). "
    "근거 없는 종목 만들지 말 것. reason 은 게시글에 실제 있는 사실만. "
    "단순 인사·잡담 글은 무시."
)


def _llm_analysis(posts):
    src = top_posts(posts, 30)
    blocks = []
    for p in src:
        txt = p["text"].replace("\n", " ").strip()
        blocks.append(f"- ({p['channel']} | 공유 {p['forwards']}) {txt[:350]}")
    body = "오늘 게시글:\n" + "\n".join(blocks)
    data = llm.chat_json(_SYSTEM, body, max_tokens=2500)
    if not data or not isinstance(data, dict):
        return None

    # 파싱(방어적)
    try:
        score = int(data.get("sentiment_score", 0))
    except (TypeError, ValueError):
        score = 0
    score = max(-100, min(100, score))

    kws = []
    for k in data.get("keywords", []) or []:
        if isinstance(k, (list, tuple)) and len(k) >= 2:
            kws.append((str(k[0]), k[1]))
        elif isinstance(k, dict):
            kws.append((str(k.get("word") or k.get("keyword", "")), k.get("count", 0)))
        elif isinstance(k, str):
            kws.append((k, 0))
    kws = [(w, c) for w, c in kws if w][:config.TOP_KEYWORDS]

    stocks = []
    for s in data.get("stocks", []) or []:
        if not isinstance(s, dict):
            continue
        name = str(s.get("name", "")).strip()
        if not name:
            continue
        try:
            sc = int(s.get("score", 0))
        except (TypeError, ValueError):
            sc = 0
        stocks.append({
            "name": name, "score": max(-100, min(100, sc)), "count": 0,
            "reason": str(s.get("reason", "")).strip()[:120],
        })
    stocks = stocks[:config.TOP_STOCKS]

    summary = str(data.get("summary", "")).strip()
    if not summary or not stocks:
        return None  # 부실하면 폴백

    return {
        "sentiment_score": score,
        "sentiment_label": _fear_greed_label(score),
        "summary": summary,
        "keywords": kws,
        "stocks": stocks,
        "popular": top_posts(posts, config.TOP_POSTS),
    }


# ----------------------------- 진입점 -----------------------------
def analyze(posts):
    if not posts:
        return _rule_based(posts)
    if llm.available():
        out = _llm_analysis(posts)
        if out:
            return out
        print("[analyzer] LLM 분석 실패/부실 → 규칙기반 폴백")
    return _rule_based(posts)
