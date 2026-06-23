"""
1회 실행 파이프라인: 수집 → 분석 → thesis 점검 → 포맷 → 전송.
스케줄러가 매시간 run_once() 를 호출한다. 단독 테스트도 가능:
  python main.py
"""
import traceback
from datetime import datetime
from zoneinfo import ZoneInfo

import config
import collector
import analyzer
import thesis_monitor
import formatter
import sender

KST = ZoneInfo("Asia/Seoul")


def run_once():
    ts = datetime.now(KST).strftime("%Y-%m-%d %H:%M")
    print(f"\n===== 실행 시작 {ts} (KST) =====")

    errs = config.validate()
    if errs:
        msg = "⚠️ 설정 오류로 실행 중단:\n" + "\n".join(f"- {e}" for e in errs)
        print(msg)
        try:
            if config.BOT_TOKEN and config.CHAT_ID:
                sender.send(msg)
        except Exception:  # noqa
            pass
        return

    # 1) 수집
    try:
        posts, ok_ch, total_ch = collector.collect()
    except Exception as e:  # noqa
        print("수집 실패:", e)
        traceback.print_exc()
        sender.send(f"⚠️ 수집 단계 오류: {e}")
        return
    print(f"수집: {ok_ch}/{total_ch} 채널, 글 {len(posts)}개")

    # 2) 감시종목 thesis 점검
    try:
        thesis = thesis_monitor.check(posts)
    except Exception as e:  # noqa
        print("thesis 점검 실패:", e)
        traceback.print_exc()
        thesis = {"alert": False, "no_change": True, "text": f"이상 없음 (점검 오류: {e})"}

    # 3) 시장 전반 분석
    market_text = None
    if config.REPORT_MODE == "full":
        try:
            a = analyzer.analyze(posts)
            market_text = formatter.format_market(a, ok_ch, total_ch, len(posts))
        except Exception as e:  # noqa
            print("시장 분석 실패:", e)
            traceback.print_exc()

    # 4) 전송 결정
    thesis_text = formatter.format_thesis(thesis)

    if config.REPORT_MODE == "alert_only":
        if thesis["alert"]:
            sender.send(thesis_text)
            print("alert_only: 변화 감지 → 전송")
        else:
            print("alert_only: 이상 없음 → 침묵")
        return

    # full / thesis_only
    parts = [thesis_text]
    if market_text:
        parts.append("\n" + "─" * 20 + "\n\n" + market_text)
    sender.send("\n".join(parts))
    print("전송 완료")


if __name__ == "__main__":
    run_once()
