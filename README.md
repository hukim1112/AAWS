# 🕷️ AAWS — AI Agent Web Scraper

> **AI가 웹을 읽고, 설계하고, 수집한다.**  
> 브라우저 자동화부터 멀티에이전트 협업까지, 실전 AI 크롤링 파이프라인 구축 핸즈온

---

## 🔍 프로젝트 소개

**AAWS (AI Agent Web Scraper)** 는 LLM 기반 에이전트가 웹 탐색·분석·데이터 수집을 자율적으로 수행하는 시스템을 설계하고 구현하는 핸즈온 프로젝트입니다.

이 프로젝트는 **2일간의 교육 커리큘럼**으로 설계되었습니다:
- **1일차**: 노트북을 따라가며 Navigator, Coder 에이전트 구축 방법을 학습
- **2일차**: 시나리오 기반 자율 프로젝트 — 에이전트를 직접 개선하여 난이도별 시나리오 통과

---

## 🚀 시작하기 (환경 세팅)

```bash
# install 폴더로 이동하여 전체 설치 스크립트 실행
cd install
bash install_all.sh
```

### 환경 변수 설정

`.env_template`을 `.env`로 복사하고 API 키를 입력하세요.

---

## 📂 프로젝트 구조

```
AAWS/
├── notebooks/              # 📗 1일차 핸즈온 실습 노트북 (01~05)
├── app/                    # 🧠 에이전트 시스템 코어
│   ├── agents/             #   ├── 에이전트 팩토리 (navigator, coder, supervisor)
│   ├── tools/              #   ├── 에이전트 도구 모음
│   ├── prompts/            #   ├── 시스템 프롬프트 (모듈화)
│   ├── schemas.py          #   ├── Blueprint 데이터 모델
│   ├── evaluator.py        #   ├── LLM-as-a-Judge 평가기
│   ├── scenario_parser.py  #   ├── 시나리오 파서
│   ├── server.py           #   ├── FastAPI 백엔드 서버
│   ├── client.py           #   ├── 터미널 CLI 클라이언트
│   └── ui.py               #   └── Streamlit 채팅 UI
├── workflows/              # 🔗 파이프라인 정의 (sequential, supervisor)
├── tests/                  # 🧪 시나리오 자동 실행 러너
├── artifacts/scenarios/    # 📋 테스트 시나리오 (9개, Level 1~5)
├── reference/              # 📖 LangChain 아키텍처 매뉴얼
├── docs/                   # 📝 Lessons & 교훈 정리
├── Mission.md              # 🎯 2일차 미션 가이드
└── install/                # 🔧 환경 설치 스크립트
```

## 🧭 커리큘럼 구조

### 1일차: 에이전트 구축 (notebooks/)

| 단계 | 노트북 | 핵심 개념 |
|:---:|--------|-----------|
| 1 | `01_BrowserUse_Basics` | Browser-use, Playwright, 브라우저 자동화 |
| 2 | `02_The_Navigator` | Agent as Tool, 멀티턴 대화, shared browser |
| 3 | `03_The_Coder` | 코드 생성, 실행 피드백 루프, Blueprint 해석 |
| 4 | `04_MultiAgent_Workflow` | Navigator→Coder 파이프라인, LangGraph |
| 5 | `05_Supervised_MultiAgentTeam` | Supervisor 패턴, 팀 자율 수행 |

### 2일차: 시나리오 기반 자율 프로젝트 (Mission.md)

에이전트를 개선하며 난이도별 시나리오를 통과하는 **평가 주도 개발(EDD)** 방식의 자율 프로젝트.

자세한 미션 가이드는 [Mission.md](Mission.md)를 참조하세요.

---

## 🏗️ 시스템 아키텍처

```
👤 사용자
    │ "이 사이트에서 데이터 수집해줘"
    ▼
🧠 Supervisor
    ├── 🗺️ Navigator     ← crawl4ai + browser-use로 HTML 분석, Blueprint 설계
    └── 💻 Coder         ← Blueprint 해석, Playwright 코드 작성 및 실행
```

### 핵심 도구 스택

| 역할 | 도구 |
|------|------|
| LLM / 에이전트 프레임워크 | LangChain `create_agent`, LangGraph |
| 브라우저 자동화 (인터랙션) | [browser-use](https://browser-use.com) |
| HTML 수집 / 렌더링 | [crawl4ai](https://crawl4ai.com) |
| 코드 실행 | Python `subprocess` (Playwright sync) |
| 상태 관리 | LangGraph `InMemorySaver`, `StateGraph` |

---

## ▶️ 앱 실행 가이드

### 1. 백엔드 서버 실행
```bash
python app/server.py --port 8000
```

### 2. CLI 테스트
```bash
python app/client.py
```

### 3. Streamlit UI 실행
```bash
streamlit run app/ui.py
```

### 4. 시나리오 실행 (2일차)
```bash
python -m tests.run_sequential_scenarios
```

---

## 📋 시나리오 목록

| 시나리오 | 난이도 | 주제 |
|----------|:------:|------|
| `quotes_01_pagination` | L1 | 정적 페이지네이션 |
| `quotes_02_tag_filter` | L2 | 태그 필터링 |
| `quotes_03_multi_step_crawling` | L3 | 다단계 크롤링 |
| `ajax_01_playwright_wait` | L2 | AJAX 대기 |
| `ajax_02_api_reverse_engineering` | L3 | API 리버스엔지니어링 |
| `github_01_trending_scraping` | L2 | GitHub 트렌딩 |
| `danawa_01_filter_search` | L4 | 다나와 필터 검색 |
| `danawa_02_deep_table_parsing` | L4.5 | 다나와 테이블 파싱 |
| `danawa_03_bulk_detail_crawling` | L5 | 다나와 대량 상세 크롤링 |
