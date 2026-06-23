"""
텔레그램 채널 수집기 (Telethon).
지난 LOOKBACK_MINUTES 분 동안 각 채널/그룹에 올라온 글을 모아 dict 리스트로 반환한다.

channels.txt 에는 채널 ID(-100...) 또는 @username 을 넣을 수 있다.
ID 로 접근하려면 먼저 대화목록(dialogs)을 한 번 훑어 엔티티 캐시를 채운다.

각 글:
{
  "channel": 표시이름, "username": 아이디(있으면), "id": 메시지 id,
  "date": datetime(UTC), "text": 본문, "views": 조회수, "forwards": 공유수,
  "url": 메시지 링크
}
"""
import asyncio
from datetime import datetime, timedelta, timezone

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError, ChannelPrivateError, UsernameNotOccupiedError

import config


def _make_client():
    """세션 문자열이 있으면 그걸로(헤드리스/GitHub Actions), 없으면 파일 세션으로."""
    if config.TG_SESSION_STRING:
        return TelegramClient(
            StringSession(config.TG_SESSION_STRING),
            config.TG_API_ID, config.TG_API_HASH)
    return TelegramClient(config.SESSION_NAME, config.TG_API_ID, config.TG_API_HASH)


def _msg_url(entity, username, msg_id):
    """공개 채널이면 t.me/username/id, 비공개면 t.me/c/<internal>/id."""
    if username:
        return f"https://t.me/{username}/{msg_id}"
    cid = getattr(entity, "id", None)
    if cid:
        return f"https://t.me/c/{cid}/{msg_id}"
    return ""


async def _collect_async():
    requested = config.load_channels()
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=config.LOOKBACK_MINUTES)

    client = _make_client()
    await client.start(phone=config.TG_PHONE)

    # 엔티티 캐시 채우기 (ID 로 접근하려면 dialogs 를 먼저 훑어야 함)
    id_map, uname_map = {}, {}
    async for d in client.iter_dialogs():
        id_map[d.id] = d.entity
        uname = getattr(d.entity, "username", None)
        if uname:
            uname_map[uname.lower()] = d.entity

    posts = []
    ok_channels = 0
    for ch in requested:
        try:
            # 엔티티 해석
            if isinstance(ch, int):
                entity = id_map.get(ch)
                if entity is None:
                    try:
                        entity = await client.get_entity(ch)
                    except Exception:  # noqa
                        entity = None
            else:
                entity = uname_map.get(ch.lower())
                if entity is None:
                    entity = await client.get_entity(ch)

            if entity is None:
                print(f"[collector] 못 찾음(미구독/ID변경): {ch}")
                continue

            title = getattr(entity, "title", str(ch))
            username = getattr(entity, "username", None)
            got = 0
            async for msg in client.iter_messages(entity, limit=200):
                if msg.date < cutoff:
                    break  # 시간 역순이므로 cutoff 이전이면 중단
                text = (msg.message or "").strip()
                if not text:
                    continue
                posts.append({
                    "channel": title,
                    "username": username or "",
                    "id": msg.id,
                    "date": msg.date,
                    "text": text,
                    "views": int(msg.views or 0),
                    "forwards": int(msg.forwards or 0),
                    "url": _msg_url(entity, username, msg.id),
                })
                got += 1
            if got:
                ok_channels += 1
        except FloodWaitError as e:
            print(f"[collector] FloodWait {e.seconds}s — 대기 후 계속")
            await asyncio.sleep(e.seconds + 1)
        except (ChannelPrivateError, UsernameNotOccupiedError):
            print(f"[collector] 접근 불가 채널 건너뜀: {ch}")
        except Exception as e:  # noqa
            print(f"[collector] {ch} 수집 오류: {e}")

    await client.disconnect()
    return posts, ok_channels, len(requested)


def collect():
    """동기 래퍼. (posts, 성공채널수, 전체채널수) 반환."""
    return asyncio.run(_collect_async())


if __name__ == "__main__":
    p, ok, total = collect()
    print(f"수집 완료: {ok}/{total} 채널, 글 {len(p)}개")
    for x in p[:5]:
        print(f"  [{x['channel']}] 👁{x['views']} 📤{x['forwards']} {x['text'][:40]}")
