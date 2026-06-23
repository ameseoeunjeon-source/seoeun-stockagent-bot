"""
[한 번만 실행] 텔레그램 세션 문자열 + CHAT_ID 를 만들어 출력한다.
설치 없이 브라우저(Google Colab)에서 돌릴 수 있도록 self-contained 로 작성.

Colab/로컬 어디서든:
  - 필요한 값(API_ID, API_HASH, PHONE, BOT_TOKEN)을 아래 input 으로 입력
  - 텔레그램으로 오는 5자리 코드 입력
  - 출력된 TG_SESSION_STRING / CHAT_ID 를 GitHub Secrets 에 붙여넣기
"""
import os
import asyncio


def _ask(name, env):
    v = os.getenv(env, "").strip()
    if v:
        return v
    return input(f"{name} 입력: ").strip()


async def main():
    # 의존성 자동 설치 (Colab 대비)
    try:
        from telethon import TelegramClient
        from telethon.sessions import StringSession
    except ImportError:
        os.system("pip -q install telethon requests")
        from telethon import TelegramClient
        from telethon.sessions import StringSession
    import requests

    api_id = int(_ask("API ID (숫자)", "TG_API_ID"))
    api_hash = _ask("API HASH", "TG_API_HASH")
    phone = _ask("전화번호 (+82...)", "TG_PHONE")
    bot_token = _ask("봇 토큰", "BOT_TOKEN")

    print("\n[1/2] 텔레그램 로그인 중... 잠시 후 앱으로 오는 5자리 코드를 입력하세요.")
    client = TelegramClient(StringSession(), api_id, api_hash)
    await client.start(phone=phone)
    session_string = client.session.save()
    me = await client.get_me()
    await client.disconnect()
    print(f"  ✅ 로그인 완료: {me.first_name}")

    print("\n[2/2] 이제 텔레그램에서 봇에게 '안녕' 을 한 번 보내세요.")
    input("  보냈으면 Enter... ")
    r = requests.get(f"https://api.telegram.org/bot{bot_token}/getUpdates", timeout=30).json()
    chat_id = None
    for u in r.get("result", []):
        m = u.get("message") or u.get("channel_post") or {}
        c = m.get("chat", {})
        if c.get("id"):
            chat_id = c["id"]
            if c["id"] > 0:
                break
    if chat_id is None:
        print("  ⚠️ 메시지를 못 찾았습니다. 봇에게 먼저 메시지를 보낸 뒤 다시 실행하세요.")

    print("\n" + "=" * 60)
    print(" 아래 값들을 GitHub Secrets 에 그대로 넣으세요")
    print("=" * 60)
    print(f"TG_API_ID            = {api_id}")
    print(f"TG_API_HASH          = {api_hash}")
    print(f"TG_PHONE             = {phone}")
    print(f"BOT_TOKEN            = {bot_token}")
    print(f"CHAT_ID              = {chat_id}")
    print(f"TG_SESSION_STRING    = {session_string}")
    print("=" * 60)
    print("(GEMINI_API_KEY 는 따로 발급받은 값을 넣으세요)")


if __name__ == "__main__":
    asyncio.run(main())
