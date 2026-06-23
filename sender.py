"""텔레그램 봇으로 메시지 전송 (Bot API, requests 사용)."""
import time
import requests
import config
from formatter import split_for_telegram


def send(text, disable_preview=True):
    """긴 메시지는 자동 분할 전송. 성공 여부 반환."""
    url = f"https://api.telegram.org/bot{config.BOT_TOKEN}/sendMessage"
    ok = True
    for chunk in split_for_telegram(text):
        try:
            r = requests.post(url, data={
                "chat_id": config.CHAT_ID,
                "text": chunk,
                "disable_web_page_preview": disable_preview,
            }, timeout=30)
            if r.status_code != 200:
                print(f"[sender] 전송 실패 {r.status_code}: {r.text[:200]}")
                ok = False
            time.sleep(0.5)  # rate limit 여유
        except Exception as e:  # noqa
            print(f"[sender] 전송 예외: {e}")
            ok = False
    return ok


if __name__ == "__main__":
    print("테스트 메시지 전송:", send("✅ 주식 알리미 봇 연결 테스트입니다."))
