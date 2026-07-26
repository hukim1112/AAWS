# 🎯 Day 2 Mission: 진화하는 에이전트 팀 구축

> **Agentic AI Hands-on : 데이터 수집·분석·시각화·Q&A 시스템 구축**
> 
> 어제 여러분은 browser-use를 활용한 웹 탐색, 에이전트 구축, 그리고 멀티 에이전트 오케스트레이션의 기초를 다졌습니다.
> 오늘은 그 에이전트 팀을 **실전 시나리오에 투입**하고, 데이터 **수집 → 분석 → 시각화**까지 이어지는 완전한 파이프라인을 완성합니다.

---

## 📋 전체 미션 개요

| 미션 | 주제 | 핵심 키워드 |
|:---:|:---|:---|
| **Mission 1** | 시나리오 도전 & 프롬프트 튜닝 | Prompt Engineering, Evaluation |
| **Mission 2** | Analyst 에이전트 구축 | 새 에이전트 설계, 도구 제작, 시각화 |
| **Mission 3** | 에이전트 고도화 (선택 미션) | Pattern Memory, Model Fallback, Skills |

각 미션은 이전 미션의 결과물 위에 쌓아 올리는 **점진적 빌드업** 구조입니다. 서두르지 말고 각 단계의 "왜?"를 충분히 체감하며 진행하세요.

---

## 🟢 Mission 1: 시나리오 도전 & 프롬프트 튜닝 (~1h)

### 목표
기본 에이전트 팀(Supervisor + Navigator + Coder)을 실전 시나리오에 투입하고, **프롬프트 수정만으로** 성능을 어디까지 끌어올릴 수 있는지 실험합니다.

### 진행 방식

#### Step 1. 시나리오 선택 (`tests/test_config.yaml`)

테스트할 시나리오는 **`tests/test_config.yaml`** 파일에서 간편하게 선택할 수 있습니다.
파일을 열고 테스트하고 싶은 시나리오의 주석(`\#`)을 해제하세요.

```yaml
# tests/test_config.yaml
scenarios:
  # ── Level 1 ──
  - quotes_01_pagination.md       # 실행할 시나리오 (주석 해제)
  # - quotes_02_tag_filter.md     # 주석 처리된 시나리오는 건너뜀
```

#### Step 2. Supervisor 시나리오 실행 (Level 1)

주 세션에서는 감독형 에이전트 팀(**Supervisor Workflow**)을 기반으로 실행합니다:

```bash
# 프로젝트 루트에서 실행 (Supervisor 방식)
python -m tests.run_supervisor_scenarios
```

> **💡 참고 (Sequential 방식):**  
> 개별 에이전트(Navigator ➔ Coder)의 동작을 고정 순서로 단순 검증하고 싶을 때는 `python -m tests.run_sequential_scenarios`를 사용할 수도 있습니다.

**추천 시작 시나리오:**
- `quotes_01_pagination.md` — 정적 사이트의 다중 페이지 수집
- `quotes_02_tag_filter.md` — 태그 필터링 기반 수집

#### Step 3. 결과 분석
실행 후 `artifacts/results/[scenario_id]/` 폴더에 생성된 평가 로그(`sup_log.md`)와 결과 파일(`sup_result.json`)을 확인하세요.

- Supervisor가 하위 에이전트(Navigator, Coder)에게 적절히 역할을 위임했나요?
- Navigator가 올바른 **전략(Strategy)**을 선택했나요?  
- Coder가 효율적인 방식(requests vs playwright)을 채택했나요?  
- 데이터의 Schema가 기대한 것과 일치하나요?

#### Step 4. 프롬프트 튜닝
`app/prompts/` 폴더에서 Supervisor, Navigator, Coder의 시스템 프롬프트를 수정하여 성능을 개선하세요.

> **💡 튜닝 포인트 예시:**
> - `app/prompts/supervisor.py`: Coder 실패 시 Navigator에게 cross-validation을 지시하도록 로직 강화
> - `app/prompts/navigator.py`: "URL 패턴을 먼저 확인하라"는 지침을 더 강하게 강조
> - `app/prompts/coder.py`: 코드 버그와 외부 사이트 요인(차단/구조 변경) 구분 지침 추가

#### Step 5. 난이도 업 (Level 2)
`tests/test_config.yaml`에서 Level 2 시나리오를 활성화하고 다시 도전하세요.

- `ajax_01_playwright_wait.md` — 동적 로딩 대기가 필요한 AJAX 페이지
- `ajax_02_api_reverse_engineering.md` — 숨겨진 백엔드 API를 찾아내야 하는 시나리오

### ✅ Mission 1 산출물
- [ ] Level 1 시나리오 1개 이상 성공 (평가 로그 확인)
- [ ] 프롬프트 수정 전/후 비교 메모 (어떤 지침을 추가/변경했고, 결과가 어떻게 달라졌는지)
- [ ] Level 2 시나리오 도전 결과 (성공 또는 실패 원인 분석)

---

## 🟡 Mission 2: Analyst 에이전트 구축 (~2h)

### 목표
Mission 1에서 수집한 데이터를 **분석하고 시각화하는 Analyst 에이전트**를 직접 설계·구현하여, **수집 → 분석 → 시각화**라는 완전한 데이터 파이프라인을 완성합니다.

### 배경: 왜 Analyst가 필요한가?

```
[현재]  Supervisor → Navigator & Coder → JSON 파일 생성  ← 여기서 끝!
[목표]  Supervisor → Navigator & Coder → Analyst → 📊 분석 리포트 + 차트
```

수집은 시작일 뿐입니다. 비즈니스 현장에서 진짜 필요한 것은 "이 데이터가 무엇을 말해주는가"에 대한 분석과 시각적 전달입니다. 여러분이 직접 세 번째 에이전트를 설계하고 팀에 합류시켜 보세요.

### 진행 방식

#### Step 1. Analyst 에이전트의 역할과 도구 설계

Analyst는 수집된 데이터(JSON/CSV)를 읽고, 의미 있는 패턴을 발견하고, 시각적으로 전달하는 에이전트입니다. 먼저 이 에이전트에게 **어떤 도구가 필요한지** 설계해보세요.

> **💡 도구 설계 예시 (자유롭게 변형/추가 가능):**
>
> | 도구 이름 | 역할 | 입력 | 출력 | 난이도 |
> |:---|:---|:---|:---|:---:|
> | `load_json_data` | JSON 파일을 읽어 통계 요약 반환 | filepath | 데이터 프로파일링 텍스트 | ⭐ |
> | `run_analysis_code` | pandas 분석 코드를 실행 | 코드 문자열 | 분석 결과 텍스트 | ⭐ |
> | `create_chart` | matplotlib/seaborn 차트 생성 | 코드 문자열, 파일명 | 저장된 이미지 경로 | ⭐⭐ |
> | `generate_infographic` | 🍌 Nano Banana(Gemini)로 AI 인포그래픽 생성 | 프롬프트, 파일명 | 저장된 이미지 경로 | ⭐⭐ |
> | `write_report` | 마크다운 분석 리포트 작성 | 리포트 내용 | 저장된 파일 경로 | ⭐ |

#### Step 2. 도구 코드 구현

`app/tools/` 폴더에 `analyst.py`를 생성하고 도구를 구현하세요.

#### Step 3. Analyst 에이전트 생성

`app/agents/` 폴더에 `analyst.py`를 생성하고, 도구와 프롬프트를 조립하여 에이전트 인스턴스를 만드세요.

```python
# app/agents/analyst.py — 뼈대 코드 예시
from langchain.chat_models import init_chat_model
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver
from app.prompts import ANALYST_SYSTEM_PROMPT
from app.tools.analyst import load_json_data, create_chart  # 여러분이 만든 도구들

def create_analyst_agent(model_name="google_genai:gemini-flash-latest", temperature=0.2):
    """데이터 분석 및 시각화 전문 에이전트 생성"""
    model = init_chat_model(model_name, temperature=temperature)
    checkpointer = InMemorySaver()
    
    agent = create_agent(
        model=model,
        system_prompt=ANALYST_SYSTEM_PROMPT,
        tools=[load_json_data, create_chart],  # + 여러분이 추가한 도구들
        checkpointer=checkpointer
    )
    return agent
```

#### Step 4. 파이프라인 연동 — Supervisor에 Analyst 추가하기

**방법 A (간단):** 수동으로 Analyst 에이전트를 호출하는 테스트 스크립트 작성
```python
# tests/run_analyst_test.py
analyst = create_analyst_agent()
result = await analyst.ainvoke(
    {"messages": [("user", "artifacts/results/quotes_01/sup_result.json 파일을 분석하고 시각화해주세요.")]},
    config={"configurable": {"thread_id": "analyst_test"}}
)
```

**방법 B (권장):** `app/agents/supervisor.py`에 `chat_to_analyst` 도구를 추가하여 Supervisor가 `Navigator → Coder → Analyst` 3단계 팀을 종합 지휘하도록 확장

#### Step 5. 분석 결과 확인

Analyst가 생성한 산출물을 확인하세요:
- `artifacts/code/` 또는 결과 폴더에 차트 이미지(`.png`)가 생성되었나요?
- 분석 리포트(`.md`)에 의미 있는 인사이트가 담겨 있나요?

---

## 🔴 Mission 3: 에이전트 고도화 — 선택 미션 (~1h)

아래 네 가지 트랙 중 **하나 이상**을 선택하여 도전하세요.

### 트랙 A: 🧠 학습하는 에이전트 (Pattern Memory)
**목표:** 에이전트가 시나리오 실행 경험(성공/실패)을 `pattern_memory.json`에 자동 기록하고, 다음 실행 시 미들웨어를 통해 시스템 프롬프트에 자동 주입하는 "지속적 학습 체계"를 구현합니다.

### 트랙 B: 🔄 Model Fallback 미들웨어
**목표:** 에이전트가 어려운 문제를 만나거나 API 사용량 초과 시, 자동으로 더 강력한(또는 대체) 모델로 전환하는 미들웨어를 구현합니다.

### 트랙 C: 📚 Skill System 적용
**목표:** 에이전트에게 도메인별 전문 스킬을 동적으로 로드하는 구조를 구현합니다 (`app/skills/`).

### 트랙 D: 🆕 나만의 시나리오 작성 & 도전
**목표:** 본인이 실무에서 실제로 수집하고 싶은 데이터 소스를 정하고 시나리오 파일(`artifacts/scenarios/my_scenario.md`)을 작성하여 도전합니다.

---

## 📎 빠른 참조 (Quick Reference)

### 프로젝트 실행 명령어
```bash
# 1. 실행 대상 시나리오 선택
# tests/test_config.yaml 파일 편집 (주석 해제)

# 2. Supervisor 워크플로우 테스트 실행 (주 테스트 방법)
python -m tests.run_supervisor_scenarios

# 3. (선택) 순차 워크플로우 테스트 실행
python -m tests.run_sequential_scenarios
```

### 핵심 파일 위치
| 용도 | 경로 |
|:---|:---|
| 시나리오 선택 설정 | `tests/test_config.yaml` |
| Supervisor 프롬프트 | `app/prompts/supervisor.py` |
| Navigator 프롬프트 | `app/prompts/navigator.py` |
| Coder 프롬프트 | `app/prompts/coder.py` |
| Supervisor 에이전트 | `app/agents/supervisor.py` |
| Navigator 도구 | `app/tools/navigator.py` |
| Coder 도구 | `app/tools/coder.py` |
| 시나리오 실행 로그 | `artifacts/results/[scenario_id]/sup_log.md` |
