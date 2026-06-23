#!/usr/bin/env bash
# ============================================================
#  주식 알리미 봇 - 한 번만 실행하는 설치 스크립트 (Mac / Linux)
#  사용법: 터미널에서 이 폴더로 이동 후
#     bash setup.sh
# ============================================================
set -e
cd "$(dirname "$0")"

echo "============================================"
echo " 주식 통합 알리미 봇 설치를 시작합니다"
echo "============================================"

# 1) 파이썬 가상환경
if [ ! -d "venv" ]; then
  echo "[1/5] 가상환경 생성..."
  python3 -m venv venv
fi
# shellcheck disable=SC1091
source venv/bin/activate

# 2) 의존성 설치
echo "[2/5] 라이브러리 설치 (몇 분 걸릴 수 있어요)..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

# 3) .env 확인
if [ ! -f ".env" ]; then
  echo "❌ .env 파일이 없습니다. .env.example 을 복사해 값을 채운 뒤 다시 실행하세요."
  exit 1
fi

# 4) 텔레그램 개인계정 로그인 (처음 한 번, 인증코드 입력)
echo "[3/5] 텔레그램 로그인..."
echo "  → 잠시 후 텔레그램 앱으로 5자리 인증코드가 옵니다. 그 숫자를 입력하세요."
python3 - <<'PY'
import asyncio, config
from telethon import TelegramClient
async def go():
    c = TelegramClient(config.SESSION_NAME, config.TG_API_ID, config.TG_API_HASH)
    await c.start(phone=config.TG_PHONE)
    me = await c.get_me()
    print(f"  ✅ 로그인 완료: {me.first_name}")
    await c.disconnect()
asyncio.run(go())
PY

# 5) CHAT_ID 자동 설정
echo "[4/5] 알림 받을 채팅 설정..."
echo "  → 지금 텔레그램에서 봇(@seoeun_stockagent_bot)에게 '안녕' 을 한 번 보내세요."
read -r -p "  보냈으면 Enter 를 누르세요... " _
python3 write_chat_id.py

# 6) 연결 테스트
echo "[5/5] 테스트 메시지 전송..."
python3 sender.py || true

echo ""
echo "============================================"
echo " ✅ 설치 완료!"
echo "   - 한 번 실행해 보기:   ./run.sh"
echo "   - 24시간 자동 실행 설정은 README 4장을 참고하세요."
echo "============================================"
