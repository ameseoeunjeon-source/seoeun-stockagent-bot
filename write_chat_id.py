"""
봇 토큰으로 CHAT_ID 를 자동 조회해서 .env 에 직접 써준다.
사용 전: 텔레그램에서 본인 봇에게 아무 메시지(예: '안녕')를 한 번 보낸다.
실행: python write_chat_id.py
"""
import re
import requests
import config


def fetch_chat_id():
    url = f"https://api.telegram.org/bot{config.BOT_TOKEN}/getUpdates"
    r = requests.get(url, timeout=30).json()
    found = {}
    for u in r.get("result", []):
        m = u.get("message") or u.get("channel_post") or {}
        chat = m.get("chat", {})
        if chat.get("id"):
            found[chat["id"]] = chat.get("title") or chat.get("username") or chat.get("first_name", "")
    return found


def write_env(chat_id):
    env_path = config.BASE_DIR / ".env"
    text = env_path.read_text(encoding="utf-8")
    if re.search(r"(?m)^CHAT_ID=.*$", text):
        text = re.sub(r"(?m)^CHAT_ID=.*$", f"CHAT_ID={chat_id}", text)
    else:
        text += f"\nCHAT_ID={chat_id}\n"
    env_path.write_text(text, encoding="utf-8")


def main():
    if not config.BOT_TOKEN:
        print("❌ .env 에 BOT_TOKEN 이 없습니다.")
        return
    found = fetch_chat_id()
    if not found:
        print("❌ 아직 메시지가 없습니다. 봇에게 '안녕'을 한 번 보낸 뒤 다시 실행하세요.")
        return
    # 개인 DM(양수 id)을 우선 선택, 없으면 첫 번째
    chat_id = next((cid for cid in found if cid > 0), list(found)[0])
    write_env(chat_id)
    print(f"✅ CHAT_ID={chat_id} ({found[chat_id]}) 를 .env 에 저장했습니다.")


if __name__ == "__main__":
    main()
