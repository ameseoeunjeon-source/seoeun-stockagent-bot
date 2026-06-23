"""
Google Gemini API 호출 래퍼 (무료 등급).
- LLM_ENABLED=false 이거나 키가 없으면 자동 비활성(None 반환).
- 무료 등급 분당요청(RPM) 한도를 넘지 않도록 호출 사이 최소 간격을 둔다.
"""
import json
import time
import config

_client = None
_last_call = 0.0


def available():
    return config.LLM_ENABLED and bool(config.GEMINI_API_KEY)


def _get_client():
    global _client
    if _client is None:
        from google import genai
        _client = genai.Client(api_key=config.GEMINI_API_KEY)
    return _client


def _throttle():
    """무료 등급 RPM 보호: 직전 호출과 최소 간격 유지."""
    global _last_call
    wait = config.LLM_MIN_INTERVAL - (time.monotonic() - _last_call)
    if wait > 0:
        time.sleep(wait)
    _last_call = time.monotonic()


def chat(system, user, max_tokens=800, temperature=0.2, want_json=False):
    """단일 호출. 실패 시 None 반환 (봇이 죽지 않도록). 429면 한 번 더 대기 후 재시도."""
    if not available():
        return None
    from google.genai import types

    sys_prompt = system
    if want_json:
        sys_prompt += "\n\n반드시 유효한 JSON 객체 하나만 출력하라. 코드펜스나 설명 없이."

    cfg = types.GenerateContentConfig(
        system_instruction=sys_prompt,
        temperature=temperature,
        max_output_tokens=max_tokens,
    )

    for attempt in range(2):
        try:
            _throttle()
            resp = _get_client().models.generate_content(
                model=config.GEMINI_MODEL, contents=user, config=cfg)
            return (resp.text or "").strip()
        except Exception as e:  # noqa
            msg = str(e)
            if ("429" in msg or "RESOURCE_EXHAUSTED" in msg) and attempt == 0:
                print("[llm] 무료 한도 일시 초과 — 30초 대기 후 재시도")
                time.sleep(30)
                continue
            print(f"[llm] 호출 실패: {e}")
            return None
    return None


def chat_json(system, user, max_tokens=800):
    """JSON 응답을 파싱해서 dict 반환. 실패 시 None."""
    raw = chat(system, user, max_tokens=max_tokens, want_json=True)
    if not raw:
        return None
    raw = raw.strip().lstrip("`").strip()
    if raw.startswith("json"):
        raw = raw[4:].strip()
    raw = raw.strip("`").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None
