"""
분석 엔진 (1시간 단위).
- 인기 게시글 랭킹: 규칙기반(조회수+공유)
- 시장 분석: LLM이 지난 1시간 게시글을 읽고, 보유·관심 섹터 관점으로 정리
  → 이 시간의 핵심 / 시장·매크로 / 섹터별 영향 / 신규 부상 / 액션 포인트 / 키워드 / 인기글 요약
- LLM 비활성/실패 시 규칙기반 최소 분석으로 폴백
"""
import re
from collections import Counter

import config
import llm
import watchlist
from lexicon import POSITIVE, NEGATIVE, STOPWORDS

_word_re = re.compile(r"[가-힣A-Za-z0-9]+")


# ----------------------------- 공통 -----------------------------
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


# ----------------------------- 규칙기반(폴백) -----------------------------
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


def _empty_struct(posts):
    senti, label = overall_sentiment(posts)
    return {
        "sentiment_score": senti, "sentiment_label": label,
        "headline": [], "macro": "", "sectors": [], "emerging": [],
        "actions": [], "keywords": extract_keywords(posts, config.TOP_KEYWORDS),
        "popular": top_posts(posts, config.TOP_POSTS),
    }


# ----------------------------- LLM 통합 분석 -----------------------------
_SYSTEM = (
    "너는 한국·미국 주식과 AI·반도체 테크를 추적하는 베테랑 애널리스트다. "
    "아래는 '지난 약 1시간' 동안 여러 텔레그램 채널에 올라온 게시글이다(번호 매김). "
    "이걸 읽고, 아래 '보유·관심 섹터' 관점에서 이 시간의 시장 인사이트를 정리하라. "
    "링크 나열이 아니라 사람이 읽고 흐름을 바로 파악할 수 있는 분석이어야 한다.\n\n"
    "[보유·관심 섹터]\n" + watchlist.sectors_for_prompt() + "\n\n"
    "반드시 아래 JSON 스키마로만 응답:\n"
    "{\n"
    '  "sentiment_score": 정수(-100~100, -100=극단적 공포 ~ +100=극단적 탐욕),\n'
    '  "headline": ["이 시간 핵심 1줄", ...가장 중요한 변화·이벤트 최대 3개],\n'
    '  "macro": "시장·매크로 흐름 2~4문장(지수·유가·금리·환율·지정학 등 게시글에 실제 나온 것만). 없으면 빈 문자열",\n'
    '  "sectors": [\n'
    '     {"name": "섹터명(위 목록 기준)", "summary": "이 섹터 관련 이 시간 흐름 1~3문장, 구체적 사실"}\n'
    "     ...관련 내용 있는 섹터만. 없으면 빈 배열\n"
    "  ],\n"
    '  "emerging": [\n'
    '     {"theme": "새로 부상한 테마/이슈", "sources": "언급 채널들", "note": "1~2문장"}\n'
    "     ...서로 다른 2개 이상 채널에서 공통 언급된 것만. 없으면 빈 배열\n"
    "  ],\n"
    '  "actions": ["점검·확인 포인트 (매수/매도 지시 금지, \'~확인/점검/모니터링\' 형태)", ...최대 4개],\n'
    '  "keywords": [["키워드", 빈도정수], ...최대 5개. 조사·부사 금지],\n'
    '  "posts": [{"i": 게시글번호, "summary": "그 게시글 핵심 1~2문장(60~90자) 완결 요약"} ...[1]~[10]번]\n'
    "}\n\n"
    "규칙: 게시글에 없는 수치·사실을 지어내지 말 것. 종목명은 절대 토막내지 말 것. "
    "1시간 단위라 내용이 적으면 적은 대로 — 빈 섹션은 빈 배열/빈 문자열로 두고 억지로 채우지 말 것. "
    "매수·매도 직접 지시는 절대 금지(점검·관찰 포인트로만 표현)."
)


def _as_str_list(v, limit):
    out = []
    for x in v or []:
        if isinstance(x, str) and x.strip():
            out.append(x.strip())
    return out[:limit]


def _llm_analysis(posts):
    src = top_posts(posts, 30)
    blocks = []
    for i, p in enumerate(src, 1):
        txt = p["text"].replace("\n", " ").strip()
        blocks.append(f"[{i}] ({p['channel']} | 공유 {p['forwards']}) {txt[:350]}")
    body = ("아래는 번호를 매긴 지난 1시간 게시글이다. "
            "[1]~[10]은 인기글이니 posts 요약을 꼭 만들어라.\n" + "\n".join(blocks))

    data = llm.chat_json(_SYSTEM, body, max_tokens=3500)
    if not data or not isinstance(data, dict):
        return None

    try:
        score = max(-100, min(100, int(data.get("sentiment_score", 0))))
    except (TypeError, ValueError):
        score = 0

    headline = _as_str_list(data.get("headline"), 3)

    macro = str(data.get("macro", "")).strip()

    sectors = []
    for s in data.get("sectors", []) or []:
        if isinstance(s, dict):
            name = str(s.get("name", "")).strip()
            summ = str(s.get("summary", "")).strip()
            if name and summ:
                sectors.append({"name": name, "summary": summ})

    emerging = []
    for e in data.get("emerging", []) or []:
        if isinstance(e, dict):
            theme = str(e.get("theme", "")).strip()
            if theme:
                emerging.append({
                    "theme": theme,
                    "sources": str(e.get("sources", "")).strip(),
                    "note": str(e.get("note", "")).strip(),
                })

    actions = _as_str_list(data.get("actions"), 4)

    kws = []
    for k in data.get("keywords", []) or []:
        if isinstance(k, (list, tuple)) and len(k) >= 2:
            kws.append((str(k[0]), k[1]))
        elif isinstance(k, dict):
            kws.append((str(k.get("word") or k.get("keyword", "")), k.get("count", 0)))
        elif isinstance(k, str):
            kws.append((k, 0))
    kws = [(w, c) for w, c in kws if w][:config.TOP_KEYWORDS]

    # 인기글 요약 매핑 ([i] 번호 = top_posts 순서)
    post_summaries = {}
    for ps in data.get("posts", []) or []:
        if isinstance(ps, dict):
            try:
                idx = int(ps.get("i"))
            except (TypeError, ValueError):
                continue
            sm = str(ps.get("summary", "")).strip()
            if sm:
                post_summaries[idx] = sm
    populars = top_posts(posts, config.TOP_POSTS)
    for j, p in enumerate(populars, 1):
        if j in post_summaries:
            p["summary"] = post_summaries[j]

    # 내용이 너무 부실하면 폴백 신호
    if not headline and not sectors and not macro:
        return None

    return {
        "sentiment_score": score,
        "sentiment_label": _fear_greed_label(score),
        "headline": headline,
        "macro": macro,
        "sectors": sectors,
        "emerging": emerging,
        "actions": actions,
        "keywords": kws,
        "popular": populars,
    }


# ----------------------------- 진입점 -----------------------------
def analyze(posts):
    if not posts:
        return _empty_struct(posts)
    if llm.available():
        out = _llm_analysis(posts)
        if out:
            return out
        print("[analyzer] LLM 분석 실패/부실 → 규칙기반 폴백")
    return _empty_struct(posts)
