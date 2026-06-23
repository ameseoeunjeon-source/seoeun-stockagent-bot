"""
매시간 정각에 run_once() 실행 (VPS에서 계속 떠 있는 프로세스).
  python scheduler.py
거래시간대만 돌리고 싶으면 CronTrigger 의 hour 를 조정하세요.
"""
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from main import run_once

KST = ZoneInfo("Asia/Seoul")


def main():
    scheduler = BackgroundScheduler(timezone=KST)
    # 매시간 정각 실행. 24시간 전체.
    # 예: 평일 8~22시만 → CronTrigger(day_of_week="mon-fri", hour="8-22", minute=0)
    scheduler.add_job(
        run_once,
        CronTrigger(minute=0, timezone=KST),
        id="hourly_report",
        max_instances=1,
        misfire_grace_time=300,
    )
    scheduler.start()
    print(f"스케줄러 시작 ({datetime.now(KST):%Y-%m-%d %H:%M} KST). 매시간 정각 실행.")
    print("시작 직후 1회 실행합니다...")
    run_once()  # 부팅 직후 한 번 즉시 실행

    try:
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        print("스케줄러 종료.")


if __name__ == "__main__":
    main()
