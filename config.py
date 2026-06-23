"""환경설정 로더. .env 파일에서 모든 설정을 읽어온다."""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def _int(key, default):
    try:
        return int(os.getenv(key, default))
    except (TypeError, ValueError):
        return int(default)


def _bool(key, default="false"):
    return os.getenv(key, default).strip().lower() in ("1", "true", "yes", "on")


# --- 텔레그램 개인 계정 (수집) ---
TG_API_ID = _int("TG_API_ID", 0)
TG_API_HASH = os.getenv("TG_API_HASH", "")
TG_PHONE = os.getenv("TG_PHONE", "")
SESSION_NAME = str(BASE_DIR / "collector_session")
# GitHub Actions 등 헤드리스 환경용 세션 문자열 (gen_session.py 로 1회 생성)
TG_SESSION_STRING = os.getenv("TG_SESSION_STRING", "")

# --- 알림 봇 (전송) ---
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
CHAT_ID = os.getenv("CHAT_ID", "")

# --- LLM (Google Gemini, 무료 등급) ---
LLM_ENABLED = _bool("LLM_ENABLED", "true")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
LLM_TOP_N = _int("LLM_TOP_N", 8)
# 무료 등급 분당요청(RPM) 한도 대응: LLM 호출 사이 최소 간격(초)
LLM_MIN_INTERVAL = _int("LLM_MIN_INTERVAL", 7)

# --- 수집/분석 파라미터 ---
LOOKBACK_MINUTES = _int("LOOKBACK_MINUTES", 70)
TOP_POSTS = _int("TOP_POSTS", 10)
TOP_STOCKS = _int("TOP_STOCKS", 10)
TOP_KEYWORDS = _int("TOP_KEYWORDS", 5)

# --- 리포트 모드 ---
REPORT_MODE = os.getenv("REPORT_MODE", "full").strip().lower()

# --- 웹 검색 ---
WEB_SEARCH_ENABLED = _bool("WEB_SEARCH_ENABLED", "false")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")

# --- 파일 경로 ---
CHANNELS_FILE = BASE_DIR / "channels.txt"
THESIS_PROMPT_FILE = BASE_DIR / "thesis_prompt.txt"
STATE_FILE = BASE_DIR / "state.json"     # 중복 알림 방지용 상태 저장


def load_channels():
    """channels.txt 에서 채널 목록을 읽는다. # 주석과 빈 줄은 무시."""
    if not CHANNELS_FILE.exists():
        return []
    out = []
    for line in CHANNELS_FILE.read_text(encoding="utf-8").splitlines():
        # 인라인 주석(#뒤) 제거
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        # t.me/xxx, https://t.me/xxx, @xxx, xxx 모두 허용
        line = line.replace("https://", "").replace("http://", "")
        line = line.replace("t.me/", "").lstrip("@")
        if not line:
            continue
        # 숫자(채널 ID, 음수 포함)면 int 로
        try:
            out.append(int(line))
        except ValueError:
            out.append(line)
    return out


def validate():
    """필수 설정 확인. 누락 시 사람이 읽을 수 있는 에러 메시지 리스트 반환."""
    errors = []
    if not TG_API_ID:
        errors.append("TG_API_ID 가 비어 있습니다 (.env)")
    if not TG_API_HASH:
        errors.append("TG_API_HASH 가 비어 있습니다 (.env)")
    if not BOT_TOKEN:
        errors.append("BOT_TOKEN 이 비어 있습니다 (.env)")
    if not CHAT_ID:
        errors.append("CHAT_ID 가 비어 있습니다 (.env) — get_chat_id.py 로 확인하세요")
    if LLM_ENABLED and not GEMINI_API_KEY:
        errors.append("LLM_ENABLED=true 인데 GEMINI_API_KEY 가 비어 있습니다")
    if not load_channels():
        errors.append("channels.txt 에 수집할 채널이 하나도 없습니다")
    return errors
