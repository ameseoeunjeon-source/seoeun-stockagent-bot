"""
서은 투자 thesis 감시종목 정의.
- check=False 인 코어/현금성 종목은 일상 점검에서 제외 (thesis 프롬프트 기준).
- constituents: 텔레그램/웹 글에서 이 단어들이 잡히면 해당 보유종목 thesis 점검 대상이 됨.
- kill: 주요 kill condition 메모.
이 파일을 수정하면 감시 대상이 바뀝니다.
"""

HOLDINGS = [
    # --- 국내 ---
    {
        "ticker": "395270", "name": "HANARO Fn K-반도체", "region": "KR", "check": True,
        "constituents": ["SK하이닉스", "하이닉스", "삼성전자", "삼성전기", "HBM", "HBM4",
                          "DRAM", "D램", "메모리", "낸드", "NAND"],
        "focus": "HBM/메모리 사이클, 고객·주문·가이던스·마진",
        "kill": "DRAM 고정가 2분기 연속 하락 + 가이던스 하향 동시",
    },
    {
        "ticker": "360750", "name": "TIGER 미국S&P500", "region": "KR", "check": False,
        "constituents": [], "focus": "코어 — 점검 불필요", "kill": "",
    },
    {
        "ticker": "487240", "name": "KODEX AI전력핵심설비", "region": "KR", "check": True,
        "constituents": ["LS일렉트릭", "LS ELECTRIC", "효성중공업", "HD현대일렉트릭",
                          "현대일렉트릭", "전력기기", "변압기", "수주잔고", "전선", "전력설비"],
        "focus": "구성사 수주잔고, 마진",
        "kill": "구성사 2곳 이상 수주잔고 감소 + 마진 하락",
    },
    {
        "ticker": "458730", "name": "TIGER 미국배당다우존스", "region": "KR", "check": False,
        "constituents": [], "focus": "코어 — 점검 불필요", "kill": "",
    },
    {
        "ticker": "455030", "name": "KODEX 미국달러SOFR", "region": "KR", "check": False,
        "constituents": [], "focus": "현금성 — 점검 불필요", "kill": "",
    },
    {
        "ticker": "379810", "name": "KODEX 미국나스닥100", "region": "KR", "check": False,
        "constituents": [], "focus": "코어 — 점검 불필요", "kill": "",
    },
    {
        "ticker": "411060", "name": "ACE KRX금현물", "region": "KR", "check": True,
        "constituents": ["금현물", "KRX금", "괴리율"],
        "focus": "괴리율 급등만",
        "kill": "(해당 없음 — 괴리율 이벤트만)",
    },
    {
        "ticker": "0167A0", "name": "SOL AI반도체TOP2플러스", "region": "KR", "check": True,
        "constituents": ["SK하이닉스", "하이닉스", "삼성전자", "HBM", "HBM4", "메모리", "DRAM", "D램"],
        "focus": "HANARO와 동일 판정 (메모리 사이클)",
        "kill": "DRAM 고정가 2분기 연속 하락 + 가이던스 하향 동시",
    },
    {
        "ticker": "426030", "name": "TIME 미국나스닥100액티브", "region": "KR", "check": False,
        "constituents": [], "focus": "BM 대비 성과만", "kill": "",
    },
    {
        "ticker": "0173Y0", "name": "KODEX 미국AI광통신네트워크", "region": "KR", "check": True,
        "constituents": ["Lumentum", "루멘텀", "Coherent", "코히어런트", "Broadcom", "브로드컴",
                          "광통신", "광모듈", "하이퍼스케일러", "capex", "CAPEX", "데이터센터"],
        "focus": "하이퍼스케일러 capex, 광모듈 ASP",
        "kill": "하이퍼스케일러 2곳 이상 capex 하향 + 광모듈 ASP 급락",
    },
    {
        "ticker": "0118S0", "name": "SOL 미국넥스트테크TOP10액티브", "region": "KR", "check": True,
        "constituents": ["IonQ", "아이온큐", "AST SpaceMobile", "ASTS", "Rocket Lab", "로켓랩",
                          "Oklo", "오클로"],
        "focus": "구성사 실계약/희석",
        "kill": "(구성사 희석·계약 훼손 시)",
    },
    {
        "ticker": "018880", "name": "한온시스템", "region": "KR", "check": True,
        "constituents": ["한온시스템", "한온"],
        "focus": "유상증자/실적만",
        "kill": "추가 유상증자",
    },
    # --- 해외 ---
    {
        "ticker": "SGOV", "name": "iShares 0-3M Treasury", "region": "US", "check": False,
        "constituents": [], "focus": "현금성 — 점검 불필요", "kill": "",
    },
    {
        "ticker": "GOOGL", "name": "Alphabet", "region": "US", "check": True,
        "constituents": ["GOOGL", "GOOG", "Alphabet", "알파벳", "구글", "Google",
                          "검색광고", "클라우드", "애드테크", "AdX", "DFP", "반독점"],
        "focus": "검색광고 성장률, 클라우드, 애드테크 반독점 구제안 판결",
        "kill": "검색광고 2분기 연속 역성장 또는 AdX·DFP 강제매각",
    },
    {
        "ticker": "AAOX", "name": "Tradr 2X Long AAOI", "region": "US", "check": True,
        "constituents": ["AAOI", "Applied Optoelectronics", "어플라이드옵토"],
        "focus": "기초자산 AAOI 실적·고객 주문·희석만",
        "kill": "(AAOI 주문·매출 훼손 또는 희석)",
    },
    {
        "ticker": "DRAM", "name": "Roundhill Memory ETF", "region": "US", "check": True,
        "constituents": ["SK하이닉스", "하이닉스", "삼성전자", "Micron", "마이크론",
                          "DRAM", "D램", "메모리", "HBM"],
        "focus": "하이닉스·삼성·마이크론 메모리 사이클",
        "kill": "DRAM 고정가 2분기 연속 하락 + 가이던스 하향 동시",
    },
]

# 리포트 '보유·관심 섹터 영향' 정리에 쓰는 섹터 가이드 (LLM 프롬프트용)
REPORT_SECTORS = [
    ("AI 반도체·메모리", "SK하이닉스, 삼성전자, 삼성전기, 마이크론(MU), HBM/HBM4, DRAM, 낸드, 메모리 고정가"),
    ("AI 전력 인프라", "LS일렉트릭, 효성중공업, HD현대일렉트릭, 전선, 변압기, 데이터센터 전력, 수주잔고"),
    ("AI 광통신", "Lumentum, Coherent, Broadcom, 광모듈, 실리콘포토닉스, 하이퍼스케일러 capex"),
    ("넥스트테크", "IonQ(양자), AST SpaceMobile, Rocket Lab, Oklo(SMR)"),
    ("빅테크/GOOGL", "Alphabet/구글 검색광고·클라우드·애드테크 반독점"),
    ("기타 보유", "한온시스템(전장), 금(金) 현물"),
]


def sectors_for_prompt():
    return "\n".join(f"- {name}: {desc}" for name, desc in REPORT_SECTORS)


# 포트 최우선 감시: 메모리 사이클 (실질 익스포저 ~45%)
# 이 신호가 잡히면 HANARO·SOL TOP2·DRAM 3종목 동시 판정 → 최우선 보고
MEMORY_CYCLE_TICKERS = ["395270", "0167A0", "DRAM"]
MEMORY_CYCLE_SIGNALS = [
    "DRAM 고정거래가격", "고정거래가", "고정가 하락", "메모리 가격 하락",
    "가이던스 하향", "감산", "재고 증가", "다운사이클",
]


def active_holdings():
    """일상 점검 대상(check=True)만 반환."""
    return [h for h in HOLDINGS if h["check"]]


def all_constituents():
    """모든 활성 보유종목의 구성종목 키워드 집합 → (키워드, 보유종목) 매핑."""
    mapping = {}
    for h in active_holdings():
        for c in h["constituents"]:
            mapping.setdefault(c.lower(), []).append(h)
    return mapping


def match_holdings(text):
    """텍스트에 등장하는 감시 보유종목 리스트 반환 (구성종목 단어 기준)."""
    low = text.lower()
    hit = {}
    for h in active_holdings():
        for c in h["constituents"]:
            if c.lower() in low:
                hit[h["ticker"]] = h
                break
    return list(hit.values())
