# 🕷️ AAWS — AI Agent Web Scraper

> **AI가 웹을 읽고, 설계하고, 수집한다.**  
> 브라우저 자동화부터 멀티에이전트 협업 및 자동 평가까지, 실전 AI 크롤링 파이프라인 구축 핸즈온

---

## 🔍 프로젝트 소개

**AAWS (AI Agent Web Scraper)** 는 LLM 기반 에이전트가 웹 탐색·분석·데이터 수집을 자율적으로 수행하는 시스템을 설계하고 구현하는 핸즈온 프로젝트입니다. 

전통적인 크롤링은 개발자가 직접 HTML 구조를 분석하고, 셀렉터를 찾고, 코드를 작성해야 합니다. 사이트 구조가 바뀌면 모든 코드를 처음부터 다시 고쳐야 하죠. AAWS는 이 과정을 지능형 AI 에이전트들에게 전적으로 위임합니다.

이 프로젝트는 실전 프로덕션 수준의 강건성(Robustness) 확보 및 **에이전트 간 협업 로직 최적화**를 직접 설계하고, 스스로의 한계를 평가할 수 있는 통합 실습 플랫폼입니다.

> *"AI 에이전트들이 복잡한 웹 환경에서 어떻게 상호작용하고, 스스로의 오류를 정정하며 완결된 결과물을 만들어 낼 수 있을까?"*

이 핸즈온 프로젝트는 그 질문에 답하기 위해 Navigator(웹 탐색 및 청사진 설계), Coder(스크립트 작성 및 디버깅), Supervisor(워크플로우 총괄 및 조정) 등 다양한 전문 에이전트들의 **협업 로직을 최적화하고 진화시키는 여정**입니다. 

에이전트들이 서로 역할을 나누어 유기적으로 협업하는 **자율 수집 팀**을 구축하고, 9가지의 난이도별 시나리오 테스트를 통과하기 위한 최적의 아키텍처 규칙을 직접 설계해 보세요.

---

## 🚀 시작하기 (환경 세팅)

Codespaces 또는 로컬 WSL2(우분투) 환경을 처음 열었다면, 터미널에서 다음 명령어를 실행하여 필요한 모든 패키지 및 브라우저 환경을 한 번에 설치하세요.

```bash
# install 폴더로 이동하여 전체 설치 스크립트 실행
cd install
bash install_all.sh
```

설치가 완료되면 Python 패키지, headless 브라우저(Playwright), 가상 디스플레이(noVNC), 한글 폰트 설정이 모두 자동으로 마무리되며 스크립트 실행 권한이 부여됩니다.

### 환경 변수 설정

프로젝트 루트에 `.env` 파일을 생성하고 아래 키를 설정하세요. (`.env_template`을 복사해 사용하실 수 있습니다.)

```env
OPENAI_API_KEY="your-api-key"
GOOGLE_API_KEY="your-api-key"
TAVILY_API_KEY="your-api-key"
DISPLAY=":1" # 가상 디스플레이(noVNC)에서 GUI 브라우저를 실시간 시청하기 위한 필수 설정
```

### 🔍 LangSmith 트레이싱 설정 (권장)

**[LangSmith](https://smith.langchain.com)** 는 LangChain/LangGraph 에이전트의 실행 흐름을 시각적으로 추적하고 디버깅할 수 있는 공식 모니터링 플랫폼입니다.  
에이전트가 어떤 도구를 호출했는지, LLM에 어떤 프롬프트가 들어갔는지, 응답 시간과 토큰 비용은 얼마나 들었는지를 웹 UI에서 한눈에 확인하고 디버깅 시간을 크게 줄일 수 있습니다.

```env
LANGCHAIN_API_KEY="your-langsmith-key"
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=AAWS  # 프로젝트 이름
```

---

## 🖥️ VNC 서버 실행 (브라우저 시각화)

자율 탐색 에이전트가 실제 크롬 브라우저를 띄워 마우스를 조작하고 클릭하는 과정을 실시간 화면으로 확인하려면 VNC 서버를 가동하세요.

```bash
./start_vnc.sh
```

1. Codespaces의 **포트(Ports)** 탭에서 **`6080` 포트**의 지구본 아이콘(Open in browser)을 클릭합니다.
2. 열린 페이지 목록에서 **`vnc.html`** 을 선택합니다.
3. 파란색 noVNC 화면에서 **`Connect`** 버튼을 누르면 가상 데스크톱 화면이 나타나며, 에이전트가 움직이는 브라우저 창을 실시간으로 시청할 수 있습니다.

---

## 🧭 커리큘럼 및 노트북 구조

학습 흐름은 점진적 빌드업(Step-by-step) 형태로 구성되어 있습니다.

```
notebooks/
├── 01_playwright_test_with_noVNC.ipynb # 🌐 Playwright 및 VNC 가상 화면 동작성 검증
├── 02_browser-use.ipynb                # 🕷️ browser-use의 동작 기본 원리 및 네이버 뉴스 실습
├── 03_The_Navigator.ipynb              # 🗺️ 웹 탐색 에이전트 (Navigator) 및 shared_browser 설계
├── 04_The_Coder.ipynb                  # 💻 자가 디버깅(Self-Healing)이 탑재된 Coder 에이전트 설계
└──  05_MultiAgent_Workflow.ipynb        # 🔗 Navigator + Coder 파이프라인 자동화 (StateGraph)
```

| 단계 | 노트북 | 핵심 학습 목표 |
|:---:|--------|-----------|
| **1** | `01_playwright_test_with_noVNC` | 가상 데스크톱 디스플레이 환경과 Playwright 정상 구동 테스트 |
| **2** | `02_browser-use` | AI 비전(Vision) 기술을 통한 웹 페이지 자율 탐색 및 브라우저 제어 |
| **3** | `03_The_Navigator` | Agent as Tool 패턴, 멀티턴 대화, shared browser 기반 브라우저 세션 유지 |
| **4** | `04_The_Coder` | 코드 자동 생성, Python subprocess 기반 자가 오류 디버깅 루프 |
| **5** | `05_MultiAgent_Workflow` | Navigator(구조 분석/검증) ➔ Coder(크롤러 구현/실행) 파이프라인 자동화 |

---

## 📂 프로젝트 구조

학습 코드(Jupyter Notebook)와 서빙 코드(fastapi/streamlit), 평가 코드(evaluator/tests)가 단일 저장소 하위로 완벽하게 병합된 **통합 아키텍처**입니다.

```
AAWS/
├── notebooks/              # 📗 핸즈온 실습 노트북 (01~05)
├── app/                    # 🧠 에이전트 시스템 코어 패키지
│   ├── agents/             #   ├── 에이전트 팩토리 (navigator, coder, supervisor)
│   ├── tools/              #   ├── 에이전트 도구 모음 (navigator, coder, supervisor_tools, common)
│   ├── prompts/            #   ├── 시스템 프롬프트 (모듈화)
│   ├── schemas.py          #   └── PageLayer, NavigatorBlueprint 등 스키마 정의
│   ├── evaluator.py        #   └── LLM-as-a-Judge 기반 시나리오 평가 엔진
│   ├── scenario_parser.py  #   └── 시나리오 마크다운 파서
│   ├── server.py           #   └── 에이전트 API 서빙 백엔드 (FastAPI)
│   ├── client.py           #   └── 터미널용 테스트 CLI 클라이언트
│   └── ui.py               #   └── 에이전트 실시간 채팅 프론트엔드 (Streamlit)
├── workflows/              # 🔗 시나리오 자동 실행을 위한 워크플로우 정의
├── tests/                  # 🧪 평가 자동화 및 러너 스크립트
├── artifacts/              # 📂 시나리오 명세 및 수집된 데이터 산출물
│   ├── scenarios/          #   └── 9개의 난이도별 시나리오 명세서 (.md)
│   └── results/            #   └── 시나리오별 평가 리포트 및 크롤링 결과 JSON
├── docs/                   # 📖 Lessons Summary 및 강의 교재 지원 문서
├── reference/              # 📚 LangChain/LangGraph 규칙 매뉴얼 및 핵심 가이드
├── samples/                # 🍌 AI 이미지 생성(Nano Banana) 테스트 코드
├── install/                # 환경 설치 스크립트 모음
├── start_vnc.sh            # VNC + noVNC 구동 스크립트
└── README.md               # 프로젝트 메인 명세서
```

---

## ▶️ 실시간 서빙 및 채팅 UI 가동 가이드

노트북 실습이 완료되면, 에이전트 팀을 실제 서비스 웹 UI 형태로 구동할 수 있습니다. 

### 1. 백엔드 서버(FastAPI) 가동
에이전트들을 API로 서빙하는 엔드포인트를 노출시킵니다.
```bash
python app/server.py --port 8000
```
* 서버 실행 후 `http://localhost:8000/docs` 에서 에이전트 API(Invoke / Stream) 작동 상태를 테스트해 볼 수 있습니다.

### 2. 터미널 테스트 CLI 가동
```bash
python app/client.py
# /switch navigator_agent 명령어 등을 입력하여 동작 에이전트를 스위칭할 수 있습니다.
```

### 3. Streamlit 웹 채팅 UI 가동
```bash
streamlit run app/ui.py
```
* 브라우저에서 `http://localhost:8501`에 접속한 뒤 사이드바에서 **`supervisor_agent`** 또는 **`navigator_agent`**를 선택하고 자연어로 대화를 나누어 보세요. VNC 화면을 함께 띄워놓으면 에이전트가 내 말에 따라 사이트를 자율 탐색하는 과정을 입체적으로 관찰할 수 있습니다.

---

## 🧪 2일차 자율 개선 프로젝트 및 시나리오 자동 평가

1일차 실습을 마친 교육생들은 **2일차 자율 에이전트 개선 프로젝트**에 본격적으로 돌입합니다.  
교육생들은 프로젝트 루트의 **Mission.md** 가이드라인을 정독한 후, **`app/` 폴더 내부에 있는 `agents/`, `tools/`, `prompts/` 코드를 직접 분석하고 튜닝**하여 난이도별 실전 웹 탐색 및 크롤링 시나리오를 돌파해야 합니다.

---

### 1. 시나리오 자동 평가 작동 프로세스

이 통합 플랫폼은 Navigator, Coder, Supervisor 에이전트가 복잡한 웹 환경에서 상호작용하고 스스로 에러를 디버깅하는 모든 과정을 실시간 기록하고 채점하는 **시나리오 기반 평가 프레임워크**를 내장하고 있습니다.

1. **시나리오 명세 로드**: `artifacts/scenarios/` 하위의 난이도별 마크다운 문서에 저장된 수집 목표 URL, 예상 스키마(Expected Schema), 평가 기준을 파싱합니다.
2. **에이전트 구동 및 수집**: Navigator와 Coder가 연동하여 타겟 웹사이트에 접속하고, CSS 셀렉터를 찾아 크롤링 코드를 자율 생성·수정한 뒤 지정된 경로에 JSON 결과 데이터를 파일로 추출합니다.
3. **LLM-as-a-Judge 평가**: 에이전트가 작성을 완료한 리포트, 소스 코드, 수집한 JSON 파일을 종합 분석하여 객관적으로 채점합니다.

#### 📊 채점 기준 및 스코어 매트릭스
* **Schema Score (100점 만점)**: 수집된 데이터의 형식(Pydantic 스키마) 정합성, 속성 매칭도, 결측치 비율 등을 채점합니다.
* **Strategy Score (100점 만점)**: 에이전트가 동작한 경로의 지능성, 토큰 소모량, 불필요한 자원 낭비 최소화(예: 정적 페이지임에도 무거운 Playwright를 썼는지 등)를 종합 평가합니다.

---

### 2. 시나리오 테스트 실행 명령어

동일한 시나리오를 **두 가지 아키텍처**로 실행하여 성능을 비교할 수 있습니다.

```bash
# A. 순차형 파이프라인 (Navigator ➔ Coder) 시나리오 평가 실행
python -m tests.run_sequential_scenarios

# B. 감독형 협업 팀 (Supervisor 중심 동적 위임) 시나리오 평가 실행
python -m tests.run_supervisor_scenarios
```

#### A vs B: 두 가지 아키텍처의 차이

| 비교 항목 | **A. Sequential (순차형)** | **B. Supervisor (감독형)** |
|:---|:---|:---|
| **제어 흐름** | 확정적(Deterministic) — Navigator → Coder 순서 고정 | 동적(Dynamic) — Supervisor LLM이 상황에 따라 판단 |
| **실행 주체** | Python 코드가 직접 에이전트를 순서대로 호출 | Supervisor 에이전트가 도구(Tool)로 하위 에이전트를 호출 |
| **Blueprint 전달** | 파일 저장 후 Coder에게 경로 전달 | Supervisor가 Navigator 응답을 받아 Coder에게 직접 전달 |
| **사용 코드** | `tests/run_sequential_scenarios.py` | `workflows/02_supervisor_workflow.py` |
| **장점** | 단순하고 예측 가능, 디버깅 용이 | 유연한 분기 가능 (재시도, 추가 탐색 등) |
| **적합한 상황** | 구조가 단순한 사이트, 개별 에이전트 성능 검증 | 복잡한 시나리오, 에이전트 간 동적 협업 필요 시 |

```
# A. Sequential — 확정적 파이프라인
👤 시나리오 → 🗺️ Navigator → [Blueprint JSON 파일] → 💻 Coder → 📄 결과

# B. Supervisor — 동적 위임
👤 시나리오 → 👨‍💼 Supervisor ──┬── 🗺️ chat_to_navigator() → Blueprint 획득
                               └── 💻 chat_to_coder()     → 코드 작성·실행
```

> 💡 **Tip**: 특정 시나리오만 집중적으로 테스트하고 싶다면, `tests/run_sequential_scenarios.py` (혹은 `run_supervisor_scenarios.py`) 파일 하단의 `target_scenarios` 리스트에서 타겟 시나리오 파일명의 주석을 해제하여 간편하게 관리할 수 있습니다.

---

### 3. 결과물 및 평가 피드백 리포트 분석

테스트가 완료되면 에이전트들이 생성한 샌드박스 결과물과 평가 로그가 시나리오 ID별로 격리되어 `artifacts/results/[scenario_id]/` 폴더에 실시간 저장됩니다.

* **`[시나리오명]_result.json`**: Coder 에이전트가 실제 크롤러 코드를 짜서 수집하는 데 성공한 원시 데이터 파일입니다.
* **`[시나리오명]_log.md`**: LLM 평가 인공지능이 매긴 최종 점수(Schema/Strategy), 상세 채점 사유, 에이전트가 실패한 원인 분석 및 개선 방향 피드백이 담긴 **마크다운 상세 평가 리포트**입니다.
* **`artifacts/code/`**: Coder가 디버깅 루프를 돌며 작성하고 런타임에 직접 실행했던 `.py` 파이썬 크롤링 소스 코드 원문입니다.

---

## 🛠️ 미션 수행 및 에이전트 고도화 가이드

성공적인 미션 클리어를 위해 교육생들은 다음의 핵심 영역을 집중적으로 개선해야 합니다.

1. **시스템 프롬프트 튜닝 (`app/prompts/`)**:
   * Navigator가 타겟 사이트의 로딩 속도를 분석하고 대기 시간을 동적으로 인지하게 하거나, Coder가 더욱 안정적인 에러 핸들링 코드를 작성하도록 페르소나와 제약조건을 고도화합니다.
2. **에이전트 조립 구조 개선 (`app/agents/`)**:
   * LLM 파라미터(온도 조절 등)를 미세조정하거나, 에이전트 간 주고받는 맥락(Context Schema) 정보에 튜닝된 데이터를 추가해 협업 품질을 향상시킵니다.
3. **전문 도구 확장 (`app/tools/`)**:
   * DOM 트리를 축약하여 토큰 소모를 방지하는 `extract_dom_skeleton` 같은 신규 고성능 도구를 직접 개발하고 장착해 에이전트의 물리적 능력을 강화합니다.

자세한 미션 빌드업 절차는 **[Mission.md]** 파일을 열어 Step-by-step 지침에 따라 차근차근 도전을 완료하세요!

---

## 🔒 향후 연구과제: Anti-Bot 대응

이번 핸즈온 커리큘럼에서는 **공개된 연습용 사이트**([Quotes to Scrape](http://quotes.toscrape.com), 네이버 뉴스 등 로그인 불필요 영역)를 대상으로 실습했기 때문에, **Anti-Bot 방어 우회 기법은 의도적으로 다루지 않았습니다.**

실제 서비스 환경에서는 다양한 봇 차단 기술이 적용되어 있으며, 이를 해결하지 않으면 크롤러가 즉시 차단됩니다. 자체 학습 또는 다음 단계 심화 과정을 위해 주요 도전 과제와 접근 방향을 소개합니다.

### 주요 Anti-Bot 기법과 대응 방향

| 방어 기법 | 증상 | 대응 방향 |
|-----------|------|-----------|
| **Cloudflare / Akamai 봇 감지** | 접속 시 빈 페이지 또는 CAPTCHA 페이지 반환 | Playwright stealth 플러그인, 지연 시간 무작위화 |
| **CAPTCHA (reCAPTCHA, hCaptcha)** | 로봇 확인 요청 팝업 | [2captcha](https://2captcha.com), [CapSolver](https://capsolver.com) 등 CAPTCHA 해결 서비스 연동 |
| **IP 차단 / Rate Limiting** | 일정 횟수 이후 403, 429 오류 | 프록시 로테이션 (Bright Data, Oxylabs 등), 요청 간 delay 적용 |
| **JS 렌더링 감지** | Headless 브라우저 탐지 (navigator.webdriver 등) | `playwright-stealth` 라이브러리로 headless 특성 숨기기 |
| **로그인 필요 페이지** | 세션 없이 접근 시 리다이렉트 | 쿠키/세션 파일 저장 후 재사용, browser-use의 `shared_browser` 활용 |
| **동적 토큰 / CSRF** | API 요청 시 토큰 검증 실패 | 브라우저로 토큰 먼저 획득 후 API 호출 |

---

### ⚠️ 주의사항

> ⚠️ Anti-Bot 우회 기법은 대상 서비스의 **이용약관(ToS)을 반드시 확인**한 후 적용해야 합니다.  
> 허가 없는 크롤링은 법적 책임이 따를 수 있습니다.  
> 연습은 항상 **공식 허용된 테스트 사이트**나 **본인이 운영하는 서버**에서 진행하세요.

### 📚 참고 자료

- [Playwright Stealth](https://github.com/AtuboDad/playwright_stealth): Headless 탐지 우회
- [crawl4ai Anti-Detection 가이드](https://docs.crawl4ai.com): crawl4ai의 스텔스 옵션
- [CapSolver](https://capsolver.com): CAPTCHA 자동 해결 API
- [Bright Data 프록시](https://brightdata.com): IP 로테이션 상용 서비스
- [browser-use 로그인 세션 유지](https://browser-use.com): `keep_alive=True` 패턴

---

### 🛠️ 기법별 구체적 접근 방법 및 예제 코드

#### 1. Headless 브라우저 탐지 우회 — `playwright-stealth`

사이트는 `navigator.webdriver`, `chrome.runtime` 같은 JS 속성으로 Headless 브라우저를 감지합니다. `playwright-stealth`는 이 속성들을 일반 브라우저처럼 위장합니다.

```python
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    stealth_sync(page)                     # ← Headless 특성 숨기기
    page.goto("https://target-site.com")
```

crawl4ai를 사용할 경우 `BrowserConfig`에서 스텔스 설정과 실제 사용자 환경 헤더를 주입합니다:

```python
from crawl4ai import BrowserConfig

browser_cfg = BrowserConfig(
    headless=True,
    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ...",  # 실제 브라우저 UA
    headers={"Accept-Language": "ko-KR,ko;q=0.9"},
)
```

---

#### 2. IP 차단 방어 — 프록시 로테이션 + 요청 딜레이

동일 IP에서 짧은 시간에 대량 요청을 보내면 차단됩니다. 두 가지 전략을 병행하여 유기적으로 차단을 방어합니다.

**① 요청 간 무작위 딜레이 (가장 단순하지만 확실한 방법)**

```python
import random, time

for url in url_list:
    page.goto(url)
    time.sleep(random.uniform(1.5, 4.0))  # 1.5~4초 무작위 대기
```

**② 프록시 로테이션 (IP 분산)**

```python
from crawl4ai import BrowserConfig
import random

proxy_list = [
    "http://user:pass@proxy1.example.com:8080",
    "http://user:pass@proxy2.example.com:8080",
]

browser_cfg = BrowserConfig(
    proxy=random.choice(proxy_list),   # 요청마다 다른 IP 적용
)
```

---

#### 3. CAPTCHA 자동 해결 — CapSolver API 연동

CAPTCHA가 나타나면 수동 입력 없이 외부 서비스 API를 통해 정답 토큰을 발급받아 주입합니다.

```python
import capsolver

capsolver.api_key = "YOUR_CAPSOLVER_KEY"

solution = capsolver.solve({
    "type": "ReCaptchaV2Task",          # CAPTCHA 종류
    "websiteURL": "https://target.com",
    "websiteKey": "6Le-..."             # 대상 사이트의 reCAPTCHA 고유 키
})

token = solution["gRecaptchaResponse"]  # 해결된 토큰
page.evaluate(f'document.getElementById("g-recaptcha-response").value = "{token}"')
page.click("#submit-button")
```

---

#### 4. 로그인 세션 유지 — 쿠키 저장 & 재사용

로그인 상태를 쿠키 파일로 로컬에 로드/덤프해두면, 매 실행마다 로그인 비밀번호를 입력할 필요가 전혀 없습니다.

```python
from playwright.sync_api import sync_playwright
import json

# ① 최초 로그인 후 쿠키 저장
with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto("https://target.com/login")
    page.fill("#username", "my_id")
    page.fill("#password", "my_pw")
    page.click("#login-btn")
    page.wait_for_load_state("networkidle")

    cookies = page.context.cookies()
    with open("session.json", "w") as f:
        json.dump(cookies, f)           # 세션 파일 저장

# ② 이후 실행 시 쿠키 불러와서 로그인 없이 다이렉트 접근
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context()
    with open("session.json") as f:
        context.add_cookies(json.load(f))
    page = context.new_page()
    page.goto("https://target.com/my-page")   # 로그인 상태가 자동으로 승계되어 열림
```

browser-use에서는 `shared_browser`와 `keep_alive=True` 세션 유지 옵션을 활용하여 동일한 영속성을 획득할 수 있습니다. (03 노트북 참고)

---

#### 5. AI 에이전트를 활용한 시각적 CAPTCHA·팝업 자율 처리

browser-use의 비전(Vision) 기능이 켜진 멀티모달 에이전트는, 화면 상에 뜬 방해물 팝업이나 캡차를 스스로 시각적으로 식별하여 똑똑하게 닫아내거나 해결 프로세스를 자율 진행할 수 있습니다.

```python
agent = Agent(
    task="로그인 페이지에서 CAPTCHA가 나타나면 화면 스크린샷 이미지를 분석해서 텍스트를 입력하고, 팝업은 닫아주세요.",
    llm=bu_llm,
    use_vision=True,   # 비전 분석 활성화
)
```

다만 고난이도 행동 차단(예: 지능형 동적 reCAPTCHA v3 등)에는 AI 비전만으로는 우회가 한계가 있으므로, **CapSolver 등의 기계적 해결 API를 적절하게 병행하여 도구로 장착해 주는 것**이 현업에서 가장 안전하고 추천되는 방식입니다.
