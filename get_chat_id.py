"""
CHAT_ID 확인 도우미.
사용법:
  1) 텔레그램에서 본인 봇에게 아무 메시지나 한 번 보낸다 (예: "안녕")
  2) python get_chat_id.py 실행
  3) 출력된 chat_id 를 .env 의 CHAT_ID 에 넣는다
"""
import requests
import config


def main():
    if not config.BOT_TOKEN:
        print("먼저 .env 에 BOT_TOKEN 을 넣으세요.")
        return
    url = f"https://api.telegram.org/bot{config.BOT_TOKEN}/getUpdates"
    r = requests.get(url, timeout=30).json()
    results = r.get("result", [])
    if not results:
        print("업데이트가 없습니다. 봇에게 먼저 메시지를 한 번 보낸 뒤 다시 실행하세요.")
        return
    seen = {}
    for u in results:
        msg = u.get("message") or u.get("channel_post") or {}
        chat = msg.get("chat", {})
        if chat.get("id"):
            seen[chat["id"]] = chat.get("title") or chat.get("username") or chat.get("first_name", "")
    print("발견된 chat_id:")
    for cid, name in seen.items():
        print(f"  CHAT_ID={cid}   ({name})")


if __name__ == "__main__":
    main()
