# 🕷️ AAWS — AI Agent Web Scraper

> **AI가 웹을 읽고, 설계하고, 수집한다.**  
> LLM 에이전트 구축부터 브라우저 자동화, 멀티에이전트 협업 및 자동 평가까지 — 실전 프로덕션 AI 에이전트 핸즈온

---

## 📢 v2.0 업데이트 안내 (2026.08)

최신 AI 에이전트 아키텍처와 생태계에 맞춰 전면 개편했습니다.

| 구분 | v1.0 (Legacy) | v2.0 (Current) |
| :--- | :--- | :--- |
| **웹 UI 프론트엔드** | Streamlit (`app/ui.py`) | **Chainlit (`app/chainlit_ui.py`, 포트 `8080`)** |
| **에이전트 구성** | Navigator / Coder 분리 구조 | **Scraper 단일 전문 에이전트로 통합** |
| **Supervisor 패턴** | 단순 메시지 라우팅 방식 | **Blackboard 패턴 (Planning 문서 공유로 정보격차 해소)** |
| **브라우저 제어** | 개별 Playwright 인스턴스 | **`PlaywrightManager` CDP 공유 싱글턴 (세션/쿠키 유지)** |
| **에이전트 프레임워크** | LangChain 구버전 파이프라인 | **LangChain 1.3+ / LangGraph 1.2+ / Python 3.12** |

> 💡 **v1.0 (구버전) 코드가 필요한 경우:**  
> 학생용: `git checkout v1-legacy-main` | 강사용: `git checkout v1-legacy-instructor`

---

## 🔍 프로젝트 소개

**AAWS (AI Agent Web Scraper)** 는 LLM 기반 에이전트가 웹 탐색·분석·데이터 수집을 자율적으로 수행하는 시스템을 설계하고 구현하는 핸즈온 프로젝트입니다.

전통적인 크롤링은 개발자가 직접 HTML 구조를 분석하고, 셀렉터를 찾고, 코드를 작성해야 합니다. 사이트 구조가 바뀌면 모든 코드를 처음부터 다시 고쳐야 하죠. AAWS는 이 과정을 지능형 AI 에이전트들에게 전적으로 위임합니다.

본 프로젝트에서 교육생은 **4개의 핸즈온 노트북**으로 에이전트의 핵심 원리를 학습한 뒤, **4개의 실습 미션**을 통해 프로덕션 수준의 에이전트 시스템을 직접 조립·고도화하고, **9개 난이도별 시나리오 자동 평가**로 성능을 객관적으로 검증합니다.

> *"AI 에이전트들이 복잡한 웹 환경에서 어떻게 상호작용하고, 스스로의 오류를 정정하며 완결된 결과물을 만들어 낼 수 있을까?"*

---

## 🚀 시작하기 (환경 세팅)

Codespaces 또는 로컬 WSL2(우분투) 환경을 처음 열었다면, 터미널에서 다음 명령어를 실행하여 필요한 모든 패키지 및 브라우저 환경을 한 번에 설치하세요.

```bash
# install 폴더로 이동하여 전체 설치 스크립트 실행
cd install
bash install_all.sh
```

설치가 완료되면 Python 패키지, Playwright Chromium 브라우저, 가상 디스플레이(noVNC), 한글 폰트 설정이 모두 자동으로 마무리됩니다.

### 환경 변수 설정

프로젝트 루트에 `.env` 파일을 생성하고 아래 키를 설정하세요. (`.env.example`을 복사해 사용하실 수 있습니다.)

```env
GOOGLE_API_KEY="your-google-api-key"
OPENAI_API_KEY="your-openai-api-key"
DISPLAY=":1"          # 가상 디스플레이(noVNC)에서 GUI 브라우저를 실시간 시청하기 위한 필수 설정
HEADLESS="true"       # true: headless 모드 / false: headed 모드 (VNC로 시각 확인 시 false)
```

### 🔍 LangSmith 트레이싱 설정 (선택적용)

**[LangSmith](https://smith.langchain.com)** 는 LangChain/LangGraph 에이전트의 실행 흐름을 시각적으로 추적하고 디버깅할 수 있는 공식 모니터링 플랫폼입니다.
사용을 위해 발급 받은 api key를 .env에 기입하고, LANGCHAIN_TRACING_V2=true 로 세팅합니다.

```env
LANGCHAIN_API_KEY="your-langsmith-key"
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=AAWS
```

---

## 🖥️ VNC 서버 실행 (브라우저 시각화)

에이전트가 실제 크롬 브라우저를 띄워 마우스를 조작하고 클릭하는 과정을 실시간 화면으로 확인하려면 VNC 서버를 가동하세요.

```bash
./start_vnc.sh
```

1. Codespaces의 **포트(Ports)** 탭에서 **`6080` 포트**의 지구본 아이콘(Open in browser)을 클릭합니다.
2. 열린 페이지 목록에서 **`vnc.html`** 을 선택합니다.
3. 파란색 noVNC 화면에서 **`Connect`** 버튼을 누르면 가상 데스크톱 화면이 나타나며, 에이전트가 움직이는 브라우저 창을 실시간으로 시청할 수 있습니다.

---

## 🧭 커리큘럼: 노트북 → 미션 2단계 구조

학습 흐름은 **노트북(개념 학습)** → **미션(프로덕션 코드 실습)**의 점진적 빌드업 형태입니다.

### 📗 핸즈온 노트북 (학습)

```
notebooks/
├── 1_Create_agent.ipynb           # 🤖 LangChain 에이전트 구축 기초 (ReAct, Tool, Prompt)
├── 2_Coder.ipynb                  # 💻 코딩 도구 설계 및 자가 디버깅(Self-Healing) 루프
├── 3_Navigator.ipynb              # 🗺️ Playwright 기반 웹 탐색 도구 6종 및 브라우저 세션 관리
└── 4_MultiAgent_Orchestration.ipynb  # 🔗 Supervisor + Worker 멀티에이전트 협업 아키텍처
```

| 단계 | 노트북 | 핵심 학습 목표 |
|:---:|--------|------------|
| **1** | `1_Create_agent` | LangChain 1.x `create_agent` 팩토리, ReAct 루프, 커스텀 도구 바인딩 |
| **2** | `2_Coder` | `file_writer` + `bash_command` 기반 코드 자동 생성 및 디버깅 루프 |
| **3** | `3_Navigator` | DOM 스켈레톤 추출, 셀렉터 검증, 페이지 인터랙션, browser-use 자율 탐색 |
| **4** | `4_MultiAgent_Orchestration` | Agent-as-Tool 패턴, Context Isolation, Planning 도구, `invoke_sub_agent` |

### 🎯 실습 미션 (프로덕션 코드 구축)

```
missions/
├── 01_missions.md    # 🧠 커스텀 기억 도구(읽기/갱신) 구현 및 Chatbot 연결
├── 02_missions.md    # 🧪 Scraper 시나리오 자동 평가 실행 및 분석
├── 03_missions.md    # 👑 Supervisor 멀티에이전트 오케스트레이터 구축
└── 04_missions.md    # 🎨 나만의 커스텀 서브 에이전트 기획·개발 및 연동
```

---

## 📂 프로젝트 구조

학습 코드(Jupyter Notebook), 프로덕션 에이전트 서빙 코드(FastAPI + Chainlit), 자동 평가 프레임워크(evaluate)가 단일 저장소로 통합된 **모노레포 아키텍처**입니다.

```
AAWS/
├── notebooks/              # 📗 핸즈온 실습 노트북 (1~4)
├── missions/               # 🎯 실습 미션 가이드 (01~04)
├── lessons_summary/        # 📚 실전 에이전트 아키텍처 & 설계 패턴 교훈 바이블
│   ├── Subagent.md                     # Dynamic Context Pruning, Blackboard 패턴, Sub-Agent Protocol
│   ├── Long_running_agent.md           # Event-Driven Reactive Wakeup & 비동기 롱러닝 아키텍처
│   └── Agent_Engineering_Principles.md # 도구 설계(Curated View), Prompt-as-Code, EDD 평가 하네스
├── app/                    # 🧠 에이전트 시스템 코어 패키지
│   ├── agents/             #   ├── 에이전트 팩토리 (chatbot, scraper, supervisor, analyst)
│   ├── tools/              #   ├── 에이전트 도구 모음
│   │   ├── common.py       #   │   ├── 범용 코딩/파일/검색 도구 10종
│   │   ├── navigator.py    #   │   ├── Playwright 웹 탐색 도구 6종 + PlaywrightManager
│   │   ├── plan.py         #   │   ├── Supervisor 계획 도구 5종
│   │   ├── supervisor_tools.py #   │├── 서브에이전트 오케스트레이션 도구
│   │   └── analyst.py      #   │   └── 데이터 분석 도구 6종
│   ├── prompts/            #   ├── 에이전트별 시스템 프롬프트 (CHATBOT, SCRAPER, SUPERVISOR, ANALYST)
│   ├── database/           #   ├── 사용자 기억(USER.md), 대화 DB
│   ├── middleware/         #   ├── HITL 미들웨어
│   ├── utils/              #   ├── LLM 초기화, 메시지 유틸, DB 레이어
│   ├── server.py           #   ├── FastAPI 에이전트 API 서버
│   ├── chainlit_ui.py      #   ├── Chainlit 채팅 프론트엔드
│   ├── streamlit_ui.py     #   ├── Streamlit 채팅 프론트엔드
│   └── client.py           #   └── 터미널 테스트 CLI 클라이언트
├── public/                 # 🎨 프론트엔드 커스텀 UI 에셋 (HtmlDashboard.jsx)
├── skills/                 # 📚 에이전트 스킬 정의
├── evaluate/               # 🧪 시나리오 자동 평가 프레임워크
│   ├── run_scraper_scenarios.py  #   ├── 평가 러너 (전체 시나리오 순차 실행)
│   ├── evaluator.py              #   ├── LLM-as-a-Judge 채점 엔진
│   ├── evaluate_config.yaml      #   ├── 실행할 시나리오 목록 설정
│   └── scenario_parser.py        #   └── 시나리오 마크다운 파서
├── artifacts/              # 📂 에이전트 산출물 저장소
│   ├── scenarios/          #   ├── 9개 난이도별 시나리오 명세서 (.md)
│   ├── runs/               #   ├── 평가 실행 결과 (실험별 격리 저장, gitignored)
│   ├── data/               #   ├── 에이전트가 수집한 데이터 (gitignored)
│   └── code/, notebooks/   #   └── 노트북 실습용 샘플 데이터
├── configs/                # ⚙️ HITL, 로깅 등 런타임 설정
├── install/                # 🔧 환경 설치 스크립트 모음
├── start_vnc.sh            # 🖥️ VNC + noVNC 구동 스크립트
└── README.md               # 📖 프로젝트 메인 명세서
```

---

## ▶️ 실시간 서빙 및 채팅 UI 가동 가이드

노트북 학습이 완료되면, 에이전트 팀을 실제 웹 채팅 UI로 구동합니다. **터미널 2개**를 열어 백엔드와 프론트엔드를 각각 실행하세요.

### 1. 백엔드 서버 (FastAPI) 가동 — 터미널 ①
```bash
python app/server.py --port 8000
```
* 에이전트 API 백엔드가 `:8000`에서 서빙됩니다.
* `http://localhost:8000/docs`에서 API 상태를 확인할 수 있습니다.

### 2. Chainlit 채팅 UI 가동 — 터미널 ②
```bash
chainlit run app/chainlit_ui.py --port 8080
```
* 웹 브라우저에서 `http://localhost:8080`에 접속하여 에이전트를 선택하고 대화합니다.
* 로그인: `user` / `1234`
* Chainlit UI는 내부적으로 `:8000`의 FastAPI 서버에 API 요청을 보내므로, **반드시 서버를 먼저 실행**해야 합니다.

### 3. 터미널 테스트 CLI (선택)
```bash
python app/client.py
```

---

## 🧪 시나리오 자동 평가

에이전트의 웹 데이터 수집 성능을 **9개 난이도별 시나리오**로 정량 평가합니다.

### 시나리오 구성

| 난이도 | 시나리오 | 대상 사이트 |
|:---:|----------|-----------|
| **Lv.1** | 정적 다중 페이지 수집, 태그 필터링 | Quotes to Scrape |
| **Lv.2** | 동적 AJAX 대기, 백엔드 API 역공학 | Quotes AJAX |
| **Lv.3** | 실시간 외부 사이트, 다단계 크롤링 | GitHub Trending, Quotes 멀티스텝 |
| **Lv.4~5** | 복합 필터, 테이블 파싱, 100개 대량 수집 | 다나와 |

### 평가 실행

```bash
# 전체 시나리오 자동 평가 실행
python -m evaluate.run_scraper_scenarios
```

> 💡 `evaluate/evaluate_config.yaml`에서 실행할 시나리오를 선택적으로 활성화/비활성화할 수 있습니다.

### 채점 기준

* **Schema Score (100점)**: 수집 데이터의 형식 정합성, 속성 매칭도, 결측치 비율
* **Strategy Score (100점)**: 에이전트 동작 경로의 지능성, 토큰 효율성, 최적 도구 선택

평가 결과는 `artifacts/runs/[실험ID]/` 폴더에 실험별로 격리 저장됩니다.

---

## 🔒 향후 연구과제: Anti-Bot 대응

이번 핸즈온에서는 **공개된 연습용 사이트**를 대상으로 실습하므로 Anti-Bot 방어 우회 기법은 의도적으로 다루지 않았습니다.

### 주요 Anti-Bot 기법과 대응 방향

| 방어 기법 | 증상 | 대응 방향 |
|-----------|------|-----------|
| **Cloudflare / Akamai 봇 감지** | 빈 페이지 또는 CAPTCHA 반환 | Playwright stealth 플러그인, 지연 시간 무작위화 |
| **CAPTCHA (reCAPTCHA, hCaptcha)** | 로봇 확인 팝업 | CapSolver, 2captcha 등 CAPTCHA 해결 서비스 연동 |
| **IP 차단 / Rate Limiting** | 403, 429 오류 | 프록시 로테이션 (Bright Data 등), 요청 간 delay |
| **Headless 브라우저 탐지** | `navigator.webdriver` 등 JS 속성 검사 | `playwright-stealth` 라이브러리로 위장 |
| **로그인 필요 페이지** | 세션 없이 접근 시 리다이렉트 | 쿠키 파일 저장/재사용, CDP 세션 공유 |

> ⚠️ Anti-Bot 우회 기법은 대상 서비스의 **이용약관(ToS)을 반드시 확인**한 후 적용해야 합니다.  
> 연습은 항상 **공식 허용된 테스트 사이트**나 **본인이 운영하는 서버**에서 진행하세요.

---

## 📚 참고 자료

- [LangChain 공식 문서](https://python.langchain.com)
- [LangGraph 공식 문서](https://langchain-ai.github.io/langgraph)
- [Playwright 공식 문서](https://playwright.dev/python)
- [browser-use](https://browser-use.com): AI 비전 기반 브라우저 자율 제어
- [Chainlit](https://chainlit.io): LLM 에이전트 채팅 UI 프레임워크
- [LangSmith](https://smith.langchain.com): 에이전트 실행 추적 및 디버깅
