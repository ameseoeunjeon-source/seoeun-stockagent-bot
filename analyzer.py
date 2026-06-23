"""
하이브리드 분석 엔진.
- 규칙기반: 글별 감정점수, 키워드 빈도, 종목 탐지/스코어링, 전체 센티먼트
- AI(LLM): 상위 LLM_TOP_N 게시글의 요약·종목감정을 정밀 보정 + 전체 요약문 생성
"""
import re
import json
from collections import Counter, defaultdict
from pathlib import Path

import config
import llm
from lexicon import POSITIVE, NEGATIVE, STOPWORDS

_STOCK_CACHE = config.BASE_DIR / "stock_names.json"
_word_re = re.compile(r"[가-힣A-Za-z0-9]+")


# ----------------------------- 종목 사전 -----------------------------
def load_stock_names():
    """KRX 상장 종목명 집합. FinanceDataReader로 받아 로컬 캐시."""
    if _STOCK_CACHE.exists():
        try:
            data = json.loads(_STOCK_CACHE.read_text(encoding="utf-8"))
            if data:
                return set(data)
        except Exception:  # noqa
            pass
    names = set()
    try:
        import FinanceDataReader as fdr
        df = fdr.StockListing("KRX")
        col = "Name" if "Name" in df.columns else df.columns[1]
        for n in df[col].dropna().tolist():
            n = str(n).strip()
            if len(n) >= 2:
                names.add(n)
        _STOCK_CACHE.write_text(
            json.dumps(sorted(names), ensure_ascii=False), encoding="utf-8")
    except Exception as e:  # noqa
        print(f"[analyzer] 종목 리스트 로드 실패(웹), 내장 목록 사용: {e}")
        names = set(_FALLBACK_STOCKS)
    return names


# FinanceDataReader 실패 시 최소 안전망 (주요 대형주 + 감시 구성종목)
_FALLBACK_STOCKS = [
    "삼성전자", "SK하이닉스", "삼성전기", "LG에너지솔루션", "현대차", "기아",
    "삼성바이오로직스", "셀트리온", "POSCO홀딩스", "LG화학", "네이버", "카카오",
    "LS일렉트릭", "효성중공업", "HD현대일렉트릭", "한온시스템", "OCI홀딩스",
    "비츠로셀", "예스티", "JW신약", "미래나노텍", "HD한국조선해양", "한화오션",
]


# ----------------------------- 토큰/감정 -----------------------------
def tokenize(text):
    return [w for w in _word_re.findall(text)]


def sentiment_of(text):
    """규칙기반 글 감정점수. 키워드 가중치 합을 -100~100 으로 클램프."""
    score = 0
    for word, w in POSITIVE.items():
        if word in text:
            score += w
    for word, w in NEGATIVE.items():
        if word in text:
            score += w
    return max(-100, min(100, score * 8))


def extract_keywords(posts, top_n):
    cnt = Counter()
    for p in posts:
        seen = set()
        for tok in tokenize(p["text"]):
            low = tok.lower()
            if len(tok) < 2 or low in STOPWORDS or tok.isdigit():
                continue
            if tok in seen:
                continue
            seen.add(tok)
            cnt[tok] += 1
    return cnt.most_common(top_n)


# ----------------------------- 종목 스코어링 -----------------------------
def score_stocks(posts, stock_names, top_n):
    """
    각 종목: 언급 글들의 (감정 * (1+공유가중)) 평균을 -100~100 로.
    언급 1회짜리 노이즈는 제외(최소 언급수 적용은 완만하게).
    반환: [(종목명, 점수, 대표글), ...]
    """
    agg = defaultdict(lambda: {"score": 0.0, "weight": 0.0, "count": 0, "best": None, "best_share": -1})
    for p in posts:
        senti = sentiment_of(p["text"])
        share_w = 1.0 + min(p["forwards"], 500) / 100.0  # 공유 많을수록 가중
        # 빠른 1차 필터: 토큰 단위로 후보 추출
        text = p["text"]
        for name in _candidates_in_text(text, stock_names):
            a = agg[name]
            a["score"] += senti * share_w
            a["weight"] += share_w
            a["count"] += 1
            if p["forwards"] > a["best_share"]:
                a["best_share"] = p["forwards"]
                a["best"] = p
    results = []
    for name, a in agg.items():
        if a["weight"] == 0:
            continue
        score = int(max(-100, min(100, a["score"] / a["weight"])))
        results.append((name, score, a["count"], a["best"]))
    # 절댓값(주목도) 큰 순 + 언급수
    results.sort(key=lambda x: (abs(x[1]) * (1 + x[2] / 5)), reverse=True)
    return results[:top_n]


def _candidates_in_text(text, stock_names):
    """텍스트에 등장하는 종목명. 2글자 종목은 오탐 많아 단어경계 보강."""
    hits = set()
    for name in stock_names:
        if name in text:
            if len(name) <= 2:
                # 너무 짧은 이름은 앞뒤가 한글이면 다른 단어일 가능성 → 스킵
                idx = text.find(name)
                before = text[idx - 1] if idx > 0 else " "
                after = text[idx + len(name)] if idx + len(name) < len(text) else " "
                if re.match(r"[가-힣]", before) or re.match(r"[가-힣]", after):
                    continue
            hits.add(name)
    return hits


# ----------------------------- 전체 센티먼트 -----------------------------
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


def overall_sentiment(posts):
    if not posts:
        return 0, "중립"
    total_w = 0.0
    total = 0.0
    for p in posts:
        w = 1.0 + min(p["forwards"], 500) / 100.0
        total += sentiment_of(p["text"]) * w
        total_w += w
    score = int(total / total_w) if total_w else 0
    return score, _fear_greed_label(score)


# ----------------------------- 인기 게시글 -----------------------------
def top_posts(posts, top_n):
    def pop(p):
        return p["views"] + p["forwards"] * 30  # 공유 1회 = 조회 30 가중
    return sorted(posts, key=pop, reverse=True)[:top_n]


# ----------------------------- LLM 보정/요약 -----------------------------
def llm_summary(posts, sentiment_score, label, keywords):
    if not llm.available() or not posts:
        return _rule_summary(sentiment_score, label, keywords)
    sample = "\n".join(f"- {p['text'][:120]}" for p in top_posts(posts, 25))
    kw = ", ".join(k for k, _ in keywords)
    system = ("너는 한국 주식시장 애널리스트다. 주어진 텔레그램 글 샘플을 바탕으로 "
              "현재 시장 분위기를 2~3문장으로 요약하라. 과장 없이 사실 위주로.")
    user = f"전체 센티먼트: {sentiment_score} ({label})\n주요 키워드: {kw}\n\n글 샘플:\n{sample}"
    out = llm.chat(system, user, max_tokens=300)
    return out or _rule_summary(sentiment_score, label, keywords)


def _rule_summary(score, label, keywords):
    kw = ", ".join(k for k, _ in keywords[:5])
    return (f"현재 시장 투자심리는 '{label}'(센티먼트 {score})입니다. "
            f"주요 키워드는 {kw} 등이며, 관련 이슈가 게시글에서 활발히 거론되고 있습니다.")


def llm_stock_reason(name, best_post):
    """주목 종목의 한 줄 이유. LLM 가능하면 정밀, 아니면 대표글 발췌."""
    snippet = (best_post["text"][:140] if best_post else "")
    if not llm.available() or not best_post:
        return snippet.replace("\n", " ")
    system = "주어진 글을 보고 해당 종목이 주목받는 이유를 한 문장(40자 내외)으로 요약하라."
    out = llm.chat(system, f"종목: {name}\n글: {best_post['text'][:300]}", max_tokens=80)
    return (out or snippet).replace("\n", " ")


# ----------------------------- 메인 진입점 -----------------------------
def analyze(posts):
    stock_names = load_stock_names()
    senti_score, label = overall_sentiment(posts)
    keywords = extract_keywords(posts, config.TOP_KEYWORDS)
    stocks_raw = score_stocks(posts, stock_names, config.TOP_STOCKS)
    populars = top_posts(posts, config.TOP_POSTS)

    # 하이브리드: 상위 종목만 LLM 이유 생성 (비용 절감)
    stocks = []
    for i, (name, score, count, best) in enumerate(stocks_raw):
        reason = llm_stock_reason(name, best) if i < config.LLM_TOP_N else (
            (best["text"][:120].replace("\n", " ")) if best else "")
        stocks.append({"name": name, "score": score, "count": count, "reason": reason})

    summary = llm_summary(posts, senti_score, label, keywords)

    return {
        "sentiment_score": senti_score,
        "sentiment_label": label,
        "summary": summary,
        "keywords": keywords,
        "stocks": stocks,
        "popular": populars,
    }
