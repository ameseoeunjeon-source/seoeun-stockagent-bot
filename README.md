# 📈 주식 통합 알리미 봇

매시간 정각에 텔레그램으로 두 가지를 보내주는 봇입니다.

1. **📊 감시종목 thesis 점검** — 서은님의 투자 thesis 기준. *침묵이 기본값*이라 실제 변화(주문·매출·가이던스·마진·희석·수주 등)가 있을 때만 7단계 형식으로 보고하고, 없으면 `이상 없음`만 표시합니다.
2. **📝 텔레그램 심층 분석 리포트** — 구독 중인 채널들의 글을 모아 시장 센티먼트·키워드·주목 종목·인기 게시글 TOP 10을 요약합니다.

분석은 **하이브리드**입니다. 기본은 규칙기반(무료), 상위 중요 글과 thesis 판정만 AI(LLM)로 정밀 분석해 비용을 아낍니다.

---

## 1. 작동 원리 (한 장 요약)

```
매시간 정각
   │
   ├─ collector.py   구독 채널 최근 70분 글 수집 (텔레그램 개인 API)
   │
   ├─ thesis_monitor 감시종목 구성종목(SK하이닉스·LS일렉트릭 등) 언급 글 필터
   │                 → (선택) 웹 뉴스 보강 → thesis_prompt 로 LLM 판정
   │                 → "이상 없음" 또는 7단계 보고
   │
   ├─ analyzer.py    감정·키워드·종목 스코어링 + 상위 글 AI 요약
   │
   └─ sender.py      봇으로 텔레그램 전송
```

> ⚠️ **왜 개인 계정 API가 필요한가?** 텔레그램 봇 토큰만으로는 다른 채널의 과거 글을 읽을 수 없습니다. 채널 글 수집은 **개인 계정(Telethon)** 으로 하고, 결과 전송만 **봇 토큰**으로 합니다. 둘 다 필요합니다.

---

## 2. 발급받을 것 3가지

### (A) 텔레그램 개인 API — 채널 글 수집용
1. https://my.telegram.org 접속 → 본인 전화번호로 로그인
2. **API development tools** 클릭
3. 앱 이름 아무거나 입력하고 생성 → **api_id**(숫자)와 **api_hash**(문자열) 복사
4. `.env` 의 `TG_API_ID`, `TG_API_HASH`, `TG_PHONE`(국가코드 포함, 예 `+8210...`)에 입력

### (B) 알림 봇 토큰 — 결과 전송용
1. 텔레그램에서 **@BotFather** 검색 → `/newbot` → 안내따라 봇 생성
2. 받은 토큰을 `.env` 의 `BOT_TOKEN` 에 입력
3. 방금 만든 봇과 대화창을 열고 아무 메시지나 한 번 전송(`안녕`)
4. `python get_chat_id.py` 실행 → 출력된 `CHAT_ID=...` 값을 `.env` 에 입력
   - 개인 DM이 아니라 특정 그룹/채널로 받고 싶으면, 그 방에 봇을 초대한 뒤 같은 방법으로 chat_id 확인

### (C) Gemini API 키 — AI 정밀 분석용 (무료)
1. https://aistudio.google.com/apikey 접속 → 구글 로그인 → **Create API key** (신용카드 불필요)
2. 발급된 키(`AIza...`)를 `.env` 의 `GEMINI_API_KEY` 에 입력
3. 모델 기본값 `gemini-2.5-flash` (무료 등급, 하루 1,500회 — 매시간 봇엔 충분). 더 가볍게 하려면 `GEMINI_MODEL=gemini-2.5-flash-lite`
4. AI를 아예 끄려면 `.env` 에서 `LLM_ENABLED=false` (단, thesis 자동 판정 품질은 떨어집니다)

> 무료 등급은 분당 요청 수(RPM) 제한이 있어, 봇은 호출 사이에 자동으로 `LLM_MIN_INTERVAL`(기본 7초) 간격을 둡니다. 한 번 실행에 약 1~2분 걸릴 수 있는데 정상입니다.

---

> 📱 **알림은 모든 기기에 자동으로 옵니다.** 봇은 *한 곳*에서만 돌리면 되고, 텔레그램이 폰·모든 컴퓨터로 동기화해 줍니다. 여러 곳에서 돌리면 같은 알림이 중복됩니다.

## 3. ⭐ 완전 자동 — GitHub Actions (추천: 서버도 내 컴퓨터도 필요 없음)

깃헙이 매시간 자동으로 봇을 돌립니다. **무료**이고, 내 컴퓨터를 켜둘 필요가 없어요. 파이썬 설치도 필요 없습니다(브라우저만 있으면 됨).

### A. 자격증명 만들기 — 브라우저에서 (5분)

1. https://colab.research.google.com 접속 → 구글 로그인
2. 좌측 상단 **파일 → 노트북 업로드** → 이 폴더의 `setup_colab.ipynb` 선택
3. 코드 셀 왼쪽 **▶ 실행** 클릭 → 안내대로 입력:
   - API ID `30875478`, API HASH, 전화번호 `+82...`, 봇 토큰
   - 텔레그램으로 오는 **5자리 코드** 입력
   - 봇에게 `안녕` 보내고 Enter
4. 맨 아래 출력된 값 6개(특히 `TG_SESSION_STRING`, `CHAT_ID`)를 메모해 둡니다

### B. 코드를 GitHub에 올리기

1. https://github.com 가입/로그인 → 우측 상단 **＋ → New repository**
2. 이름 입력(예 `stock-alert-bot`) → **Public** 선택 → **Create repository**
   - (Public 이면 실행시간 무료 무제한. 비밀값은 코드가 아니라 Secrets에 들어가니 안전합니다.)
3. **uploading an existing file** 링크 클릭 → 이 폴더 파일을 전부 드래그해서 올림 → **Commit changes**
   - ⚠️ `.env`, `collector_session*`, `state.json` **은 올리지 마세요**(비밀/임시 파일). 나머지는 다 올려도 됩니다.

### C. 비밀값(Secrets) 입력

저장소 상단 **Settings → 좌측 Secrets and variables → Actions → New repository secret** 에서, 아래 7개를 이름=값으로 하나씩 추가:

```
TG_API_ID, TG_API_HASH, TG_PHONE, TG_SESSION_STRING,
BOT_TOKEN, CHAT_ID, GEMINI_API_KEY
```

(앞 A단계 출력값 + 따로 발급한 Gemini 키)

### D. 채널 목록 넣기

`channels.txt` 에는 이미 옵시디언 '📋 텔레그램 방 목록' 에서 `[x]` 표시한 **채널 20개**가 들어가 있습니다. 그대로 올리면 됩니다. 방을 추가/제거하려면 채널 ID(`-100...`) 또는 `@username` 을 한 줄씩 적거나, 줄 맨 앞에 `#` 를 붙여 끄세요. (수집 계정이 그 방에 가입돼 있어야 읽힙니다.)

### E. 켜기 / 테스트

상단 **Actions** 탭 → (처음이면 워크플로 활성화 버튼 클릭) → **hourly-stock-alert** → **Run workflow** 로 즉시 한 번 돌려보세요. 텔레그램으로 리포트가 오면 성공. 이후 **매시간 정각 자동 실행**됩니다.

> 참고: 무료 스케줄은 정각보다 몇 분 늦을 수 있고, 저장소를 60일간 안 건드리면 자동 실행이 일시정지됩니다(아무 변경이나 커밋하면 다시 켜짐). 즉시·정확한 정각이 중요하면 4장의 VPS 방식을 쓰세요.

---

## 3-B. 대안: 내 컴퓨터/VPS 에서 한 줄로 설치 (Mac / Linux)

`.env` 의 값들(API·전화번호·봇토큰·Gemini키)이 채워져 있다면, 봇을 돌릴 컴퓨터(또는 VPS)의 터미널에서 이 폴더로 이동한 뒤 한 줄만 실행하세요.

```bash
bash setup.sh
```

이 스크립트가 가상환경 생성 → 라이브러리 설치 → 텔레그램 로그인 → CHAT_ID 자동 설정 → 테스트 전송까지 알아서 합니다. 중간에 딱 두 번만 사람이 개입해요.

1. **텔레그램 5자리 인증코드** 입력 (개인계정 로그인, 처음 한 번)
2. 봇(`@seoeun_stockagent_bot`)에게 `안녕` 한 번 보내고 Enter (CHAT_ID 자동 확보)

설치가 끝나면 매시간 자동 실행을 시작합니다.

```bash
./run.sh          # 켜 두면 매시간 정각에 알림. 끄려면 Ctrl+C
```

> 💡 수동으로 하고 싶다면: `python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt` 후 `python write_chat_id.py`(봇에 메시지 먼저) → `python main.py`(1회 실행).

---

## 4. VPS에 올려 24시간 돌리기

VPS가 없다면 **Oracle Cloud Always Free**(영구 무료 VM), AWS Lightsail, Vultr 등이면 충분합니다. 아래는 Ubuntu 기준.

```bash
# 1) 코드 업로드 (예: scp 또는 git)
scp -r stock-alert-bot ubuntu@<서버IP>:~/

# 2) 서버 접속 후 환경 구성
ssh ubuntu@<서버IP>
cd ~/stock-alert-bot
sudo apt update && sudo apt install -y python3-venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3) .env 와 channels.txt 작성 (로컬에서 쓰던 것 그대로 올려도 됨)
#    ⚠️ collector_session 파일도 함께 올리면 로그인 인증을 다시 안 해도 됩니다.
#    (없으면 서버에서 python main.py 한 번 실행해 코드 입력)
python main.py     # 서버에서 1회 정상 동작 확인

# 4) systemd 서비스 등록 (자동 재시작 + 부팅 시 실행)
sudo cp deploy/stock-alert-bot.service /etc/systemd/system/
sudo nano /etc/systemd/system/stock-alert-bot.service   # User/경로를 본인 환경에 맞게 수정
sudo systemctl daemon-reload
sudo systemctl enable --now stock-alert-bot

# 5) 상태/로그 확인
systemctl status stock-alert-bot
journalctl -u stock-alert-bot -f
```

이제 `scheduler.py` 가 계속 떠 있으면서 **매시간 정각**에 리포트를 보냅니다. 부팅 직후에도 즉시 1회 실행합니다.

### Mac 에서 항상 켜두기 (VPS 없이)

집/사무실 데스크탑 Mac을 항상 켜둘 수 있다면 `deploy/com.seoeun.stockbot.plist` 로 자동 시작·자동 재시작을 걸 수 있습니다(파일 안 주석에 설치법). 단, **노트북은 뚜껑을 닫거나 절전되면 멈추므로** 24시간 알림엔 데스크탑이나 VPS가 적합합니다. 잠깐 테스트만 할 거면 `./run.sh` 를 켜둔 터미널 창만 닫지 않으면 됩니다.

---

## 5. 자주 바꾸는 설정 (.env)

| 항목 | 설명 |
|------|------|
| `REPORT_MODE` | `full`(thesis+시장리포트) / `thesis_only`(thesis만) / `alert_only`(변화 있을 때만 전송, 평소 침묵) |
| `LOOKBACK_MINUTES` | 매시간 실행이면 `70` 권장(겹침 여유) |
| `LLM_TOP_N` | AI로 정밀 분석할 상위 글 수(비용 ↔ 정확도) |
| `WEB_SEARCH_ENABLED` | `true`면 thesis 점검 시 [Tavily](https://tavily.com) 웹 뉴스도 함께 확인(무료 키 필요) |
| `TOP_POSTS` / `TOP_STOCKS` / `TOP_KEYWORDS` | 각 섹션 개수 |

거래시간대(평일 8~22시)만 돌리고 싶으면 `scheduler.py` 의 `CronTrigger` 를
`CronTrigger(day_of_week="mon-fri", hour="8-22", minute=0)` 로 바꾸세요.

---

## 6. 감시종목 수정

`watchlist.py` 의 `HOLDINGS` 리스트를 편집하면 됩니다.
- `check=False` : 코어/현금성 — 일상 점검 제외
- `constituents` : 이 단어가 글에 잡히면 해당 종목 thesis 점검 대상
- `kill` : kill condition 메모

thesis 판정 기준(말투·보고 형식·알림/비알림 규칙)은 `thesis_prompt.txt` 를 직접 고치면 LLM 판정에 바로 반영됩니다. (현재 서은님이 주신 프롬프트가 그대로 들어가 있습니다.)

---

## 7. 파일 구조

```
stock-alert-bot/
├─ .env.example          설정 템플릿 → .env 로 복사해 사용
├─ requirements.txt      의존성
├─ channels.txt          수집할 채널 목록
├─ thesis_prompt.txt     thesis 판정 시스템 프롬프트(서은님 프롬프트)
├─ watchlist.py          감시종목/구성종목/kill condition 정의
├─ lexicon.py            한국어 금융 감정 사전(규칙기반)
├─ config.py             설정 로더
├─ collector.py          텔레그램 채널 수집(Telethon)
├─ analyzer.py           감정/키워드/종목 스코어링 + AI 요약
├─ thesis_monitor.py     감시종목 thesis 점검(LLM 판정 + 중복방지)
├─ formatter.py          리포트 메시지 구성
├─ sender.py             봇 전송
├─ get_chat_id.py        CHAT_ID 확인 도우미(출력만)
├─ write_chat_id.py      CHAT_ID 자동 조회 후 .env 에 기록
├─ setup.sh              한 줄 설치 스크립트(설치+로그인+CHAT_ID+테스트)
├─ run.sh                매시간 자동 실행 시작
├─ main.py               1회 실행 파이프라인
├─ scheduler.py          매시간 실행 루프
└─ deploy/
   ├─ stock-alert-bot.service       VPS(Linux) systemd 서비스
   └─ com.seoeun.stockbot.plist     Mac launchd 자동시작
```

---

## 8. 주의 / 한계

- **종목 자동 판정은 보조 도구**입니다. 직접적인 매수/매도 지시는 하지 않으며, thesis 보고는 텔레그램·웹 글을 근거로 한 **추론**입니다. 최종 판단은 직접 공시·실적 원문을 확인하세요.
- 텔레그램 개인 API는 과도하게 많은 채널을 짧은 간격으로 긁으면 `FloodWait`(일시 제한)이 걸릴 수 있습니다. 봇은 자동으로 대기/재시도하지만, 채널 수가 매우 많으면 `LOOKBACK_MINUTES`/채널 수를 조절하세요.
- `state.json`, `collector_session`, `stock_names.json`, `.env` 는 자동 생성/민감 파일이므로 외부에 공유하지 마세요.
- 종목명 매칭은 KRX 상장 종목명 기준으로 자동 수집되며, 2글자 짧은 종목명은 오탐을 줄이기 위해 단어경계 검사를 합니다(완벽하진 않음).
