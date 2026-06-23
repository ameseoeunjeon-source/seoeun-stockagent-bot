#!/usr/bin/env bash
# 봇을 매시간 자동 실행 (계속 켜져 있는 상태). 종료: Ctrl+C
cd "$(dirname "$0")"
# shellcheck disable=SC1091
source venv/bin/activate
exec python3 scheduler.py
