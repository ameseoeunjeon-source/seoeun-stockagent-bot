"""
감시종목 thesis 점검.
- 수집한 텔레그램 글 중 감시종목 구성종목을 언급한 글을 필터
- (선택) Tavily 웹 검색으로 종목별 최근 뉴스 보강
- thesis_prompt.txt 를 시스템 프롬프트로 LLM 판정 → "이상 없음" 또는 7단계 보고
- state.json 으로 동일 이벤트 중복 알림 방지
"""
import json
import hashlib
from datetime import datetime, timezone, timedelta

import config
import llm
import watchlist


# ----------------------------- 상태(중복방지) -----------------------------
def _load_state():
    if config.STATE_FILE.exists():
        try:
            return json.loads(config.STATE_FILE.read_text(encoding="utf-8"))
        except Exception:  # noqa
            return {}
    return {}


def _save_state(state):
    config.STATE_FILE.write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _prune_state(state, days=3):
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).timestamp()
    return {k: v for k, v in state.items() if v > cutoff}


# ----------------------------- 입력 수집 -----------------------------
def _relevant_posts(posts):
    """감시종목 구성종목을 언급한 글만 (종목 매칭과 함께)."""
    out = []
    for p in posts:
        hits = watchlist.match_holdings(p["text"])
        if hits:
            out.append((p, hits))
    return out


def _web_news():
    """선택: Tavily 로 활성 감시종목 최근 뉴스 검색."""
    if not (config.WEB_SEARCH_ENABLED and config.TAVILY_API_KEY):
        return []
    try:
        from tavily import TavilyClient
        tv = TavilyClient(api_key=config.TAVILY_API_KEY)
    except Exception as e:  # noqa
        print(f"[thesis] Tavily 초기화 실패: {e}")
        return []

    items = []
    for h in watchlist.active_holdings():
        # 구성종목 위주 쿼리
        terms = h["constituents"][:3] or [h["name"]]
        query = f"{' OR '.join(terms)} 실적 공시 수주 가이던스 뉴스"
        try:
            r = tv.search(query=query, topic="news", days=2, max_results=3)
            for res in r.get("results", []):
                items.append({
                    "holding": h["name"], "ticker": h["ticker"],
                    "title": res.get("title", ""),
                    "content": res.get("content", "")[:400],
                    "url": res.get("url", ""),
                })
        except Exception as e:  # noqa
            print(f"[thesis] 검색 실패({h['name']}): {e}")
    return items


# ----------------------------- LLM 판정 -----------------------------
def _build_input(rel_posts, news):
    lines = []
    if rel_posts:
        lines.append("### 텔레그램 글 (감시종목 언급)")
        for p, hits in rel_posts[:40]:
            tickers = ",".join(h["name"] for h in hits)
            lines.append(f"- [{tickers}] ({p['channel']}) {p['text'][:300]}  <{p['url']}>")
    if news:
        lines.append("\n### 웹 뉴스")
        for n in news:
            lines.append(f"- [{n['holding']}] {n['title']}: {n['content']}  <{n['url']}>")
    if not lines:
        return ""
    holdings_ref = "\n".join(
        f"- {h['name']}({h['ticker']}): 감시포인트={h['focus']} | kill={h['kill']}"
        for h in watchlist.active_holdings())
    return (f"## 감시종목 참고\n{holdings_ref}\n\n"
            f"## 이번 시간 수집 자료\n" + "\n".join(lines))


def check(posts):
    """
    반환: {"alert": bool, "text": str, "no_change": bool}
    alert=True 면 실제 thesis 변화 보고가 있음.
    """
    rel = _relevant_posts(posts)
    news = _web_news()

    if not rel and not news:
        return {"alert": False, "no_change": True,
                "text": "이상 없음 (감시종목 관련 신규 글 없음)"}

    user_input = _build_input(rel, news)
    if not llm.available():
        # LLM 없으면 보수적으로: 관련 글 목록만 제시 (자동 판정 불가)
        names = sorted({h["name"] for _, hits in rel for h in hits})
        body = "\n".join(f"- [{','.join(n2['name'] for n2 in hits)}] {p['text'][:120]}  {p['url']}"
                         for p, hits in rel[:15])
        return {"alert": True, "no_change": False,
                "text": ("⚠️ LLM 비활성 상태 — 자동 판정 불가. 감시종목 언급 글을 그대로 전달합니다.\n"
                         f"관련 종목: {', '.join(names)}\n{body}")}

    system = config.THESIS_PROMPT_FILE.read_text(encoding="utf-8")
    out = llm.chat(system, user_input, max_tokens=1200, temperature=0.1)
    if not out:
        return {"alert": False, "no_change": True, "text": "이상 없음 (분석 실패)"}

    out = out.strip()
    # "이상 없음"만 나온 경우
    if out.replace(" ", "").startswith("이상없음") and len(out) < 40:
        return {"alert": False, "no_change": True, "text": "이상 없음"}

    # 중복 보고 억제: 동일 보고 해시가 최근에 있었으면 무시
    state = _prune_state(_load_state())
    h = hashlib.sha1(out.encode("utf-8")).hexdigest()[:16]
    if h in state:
        return {"alert": False, "no_change": True, "text": "이상 없음 (이미 보고된 내용)"}
    state[h] = datetime.now(timezone.utc).timestamp()
    _save_state(state)

    return {"alert": True, "no_change": False, "text": out}
