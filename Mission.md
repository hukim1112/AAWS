# 🎯 Day 2 Mission: 진화하는 에이전트 팀 구축

> **Agentic AI Hands-on : 데이터 수집·분석·시각화·Q&A 시스템 구축**
> 
> 어제 여러분은 browser-use를 활용한 웹 탐색, 에이전트 구축, 그리고 멀티 에이전트 오케스트레이션의 기초를 다졌습니다.
> 오늘은 그 에이전트 팀을 **실전 시나리오에 투입**하고, 데이터 **수집 → 분석 → 시각화**까지 이어지는 완전한 파이프라인을 완성합니다.

---

## 📋 전체 미션 개요

| 미션 | 주제 | 핵심 키워드 | 예상 소요 |
|:---:|:---|:---|:---:|
| **Mission 1** | 시나리오 도전 & 프롬프트 튜닝 | Prompt Engineering, Evaluation | ~1h |
| **Mission 2** | Analyst 에이전트 구축 | 새 에이전트 설계, 도구 제작, 시각화 | ~2h |
| **Mission 3** | 에이전트 고도화 (선택 미션) | Pattern Memory, Model Fallback, Skills | ~1h |

각 미션은 이전 미션의 결과물 위에 쌓아 올리는 **점진적 빌드업** 구조입니다. 서두르지 말고 각 단계의 "왜?"를 충분히 체감하며 진행하세요.

---

## 🟢 Mission 1: 시나리오 도전 & 프롬프트 튜닝 (~1h)

### 목표
기본 에이전트 팀(Navigator + Coder)을 실전 시나리오에 투입하고, **프롬프트 수정만으로** 성능을 어디까지 끌어올릴 수 있는지 실험합니다.

### 진행 방식

#### Step 1. 기본 시나리오 실행 (Level 1)
`artifacts/scenarios/` 폴더에 준비된 시나리오 중 **Level 1** 시나리오를 골라 실행해보세요.

```bash
# 프로젝트 루트(AAWS_Eval)에서 실행
python -m tests.run_sequential_scenarios
```

**추천 시작 시나리오:**
- `quotes_01_pagination.md` — 정적 사이트의 다중 페이지 수집
- `quotes_02_tag_filter.md` — 태그 필터링 기반 수집

#### Step 2. 결과 분석
실행 후 `artifacts/` 폴더에 생성된 평가 로그(`*_log.md`)를 확인하세요.

- Navigator가 올바른 **전략(Strategy)**을 선택했나요?  
- Coder가 효율적인 방식(requests vs playwright)을 채택했나요?  
- 데이터의 Schema가 기대한 것과 일치하나요?

#### Step 3. 프롬프트 튜닝
`app/prompts/` 폴더에서 Navigator 또는 Coder의 시스템 프롬프트를 수정하여 성능을 개선하세요.

> **💡 튜닝 포인트 예시:**
> - Navigator에게 "URL 패턴을 먼저 확인하라"는 지침을 더 강하게 강조
> - Coder에게 "Static SSR이면 반드시 requests를 써라"는 제약 조건 추가
> - 에러 발생 시의 행동 지침을 더 구체화

#### Step 4. 난이도 업 (Level 2)
튜닝된 프롬프트로 Level 2 시나리오에 도전하세요.

- `ajax_01_playwright_wait.md` — 동적 로딩 대기가 필요한 AJAX 페이지
- `ajax_02_api_reverse_engineering.md` — 숨겨진 백엔드 API를 찾아내야 하는 시나리오

### ✅ Mission 1 산출물
- [ ] Level 1 시나리오 1개 이상 성공 (평가 로그 확인)
- [ ] 프롬프트 수정 전/후 비교 메모 (어떤 지침을 추가/변경했고, 결과가 어떻게 달라졌는지)
- [ ] Level 2 시나리오 도전 결과 (성공 또는 실패 원인 분석)

### 🤔 생각해볼 질문
> **"데이터를 성공적으로 수집했다면, 그 다음은?"**
>
> JSON 파일에 쌓인 데이터는 그 자체로는 가치가 없습니다.
> 데이터를 읽고, 패턴을 찾고, 인사이트를 뽑아내고, 시각적으로 전달하는 것까지가 진짜 파이프라인입니다.
> 이 역할을 담당할 새로운 팀원이 필요합니다 — **Analyst 에이전트**.

---

## 🟡 Mission 2: Analyst 에이전트 구축 (~2h)

### 목표
Mission 1에서 수집한 데이터를 **분석하고 시각화하는 Analyst 에이전트**를 직접 설계·구현하여, **수집 → 분석 → 시각화**라는 완전한 데이터 파이프라인을 완성합니다.

### 배경: 왜 Analyst가 필요한가?

```
[현재]  Navigator → Coder → JSON 파일 생성  ← 여기서 끝!
[목표]  Navigator → Coder → JSON → Analyst → 📊 분석 리포트 + 차트
```

수집은 시작일 뿐입니다. 비즈니스 현장에서 진짜 필요한 것은 "이 데이터가 무엇을 말해주는가"에 대한 분석과 시각적 전달입니다. 여러분이 직접 세 번째 에이전트를 설계하고 팀에 합류시켜 보세요.

### 진행 방식

#### Step 1. Analyst 에이전트의 역할과 도구 설계

Analyst는 수집된 데이터(JSON/CSV)를 읽고, 의미 있는 패턴을 발견하고, 시각적으로 전달하는 에이전트입니다. 먼저 이 에이전트에게 **어떤 도구가 필요한지** 설계해보세요.

> **💡 도구 설계 힌트 (자유롭게 변형/추가 가능):**
>
> | 도구 이름 | 역할 | 입력 | 출력 | 난이도 |
> |:---|:---|:---|:---|:---:|
> | `load_json_data` | JSON 파일을 읽어 통계 요약 반환 | filepath | 데이터 프로파일링 텍스트 | ⭐ |
> | `run_analysis_code` | pandas 분석 코드를 실행 | 코드 문자열 | 분석 결과 텍스트 | ⭐ |
> | `create_chart` | matplotlib/seaborn 차트 생성 | 코드 문자열, 파일명 | 저장된 이미지 경로 | ⭐⭐ |
> | `generate_infographic` | 🍌 Nano Banana(Gemini)로 AI 인포그래픽 생성 | 프롬프트, 파일명 | 저장된 이미지 경로 | ⭐⭐ |
> | `write_report` | 마크다운 분석 리포트 작성 | 리포트 내용 | 저장된 파일 경로 | ⭐ |

#### Step 2. 도구 코드 구현

`app/tools/` 폴더에 `analyst.py`를 생성하고 도구를 구현하세요. 아래에 주요 뼈대 코드를 제공합니다.

**📊 데이터 로드 & 분석 도구:**
```python
# app/tools/analyst.py
import os
import json
from langchain.tools import tool
from .common import ARTIFACT_DIR

@tool(parse_docstring=True)
def load_json_data(filepath: str) -> str:
    """수집된 JSON 데이터를 로드하고, 데이터의 구조·통계·품질을 프로파일링합니다.
    
    Args:
        filepath: 분석할 JSON 파일 경로
    """
    import pandas as pd
    
    full_path = os.path.join(ARTIFACT_DIR, os.path.basename(filepath))
    with open(full_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    df = pd.DataFrame(data)
    
    report = f"📊 데이터 프로파일링 결과\n{'='*40}\n"
    report += f"총 {len(df)}건, {len(df.columns)}개 컬럼\n\n"
    
    # 컬럼별 타입과 결측치 분석
    report += "📋 컬럼 상세:\n"
    for col in df.columns:
        dtype = str(df[col].dtype)
        null_count = df[col].isnull().sum()
        unique_count = df[col].nunique()
        report += f"  - {col} ({dtype}): 고유값 {unique_count}개, 결측 {null_count}건\n"
    
    # 숫자형 컬럼이 있으면 기술 통계
    numeric_cols = df.select_dtypes(include='number').columns.tolist()
    if numeric_cols:
        report += f"\n📈 수치 통계:\n{df[numeric_cols].describe().to_string()}\n"
    
    # 텍스트 컬럼의 빈도 분석 (상위 5개)
    text_cols = df.select_dtypes(include='object').columns.tolist()
    for col in text_cols[:3]:
        top5 = df[col].value_counts().head(5)
        report += f"\n🏷️ '{col}' 빈도 Top 5:\n{top5.to_string()}\n"
    
    report += f"\n📝 샘플 데이터 (상위 3건):\n{df.head(3).to_string()}"
    return report

@tool(parse_docstring=True)
def run_analysis_code(code: str) -> str:
    """pandas, numpy 등을 활용한 데이터 분석 코드를 실행하고 결과를 반환합니다.
    코드 내에서 print()로 출력한 내용이 결과로 반환됩니다.
    
    Args:
        code: 실행할 파이썬 분석 코드 문자열
    """
    import io, sys
    
    old_stdout = sys.stdout
    sys.stdout = buffer = io.StringIO()
    
    try:
        exec(code, {"__builtins__": __builtins__})
        output = buffer.getvalue()
        return output if output.strip() else "[실행 완료] 표준 출력 없음"
    except Exception as e:
        return f"[Error] 분석 코드 실행 실패: {e}"
    finally:
        sys.stdout = old_stdout
```

**📈 차트 생성 도구:**
```python
@tool(parse_docstring=True)
def create_chart(chart_code: str, filename: str = "chart.png") -> str:
    """matplotlib/seaborn 코드를 실행하여 차트를 이미지로 저장합니다.
    코드 내에서 plt.savefig()를 호출하지 마세요 — 자동으로 처리됩니다.
    
    Args:
        chart_code: 차트를 생성하는 파이썬 코드 (plt.show() 대신 이 도구가 저장 처리)
        filename: 저장할 이미지 파일명 (예: author_frequency.png)
    """
    import matplotlib
    matplotlib.use('Agg')  # 비GUI 백엔드
    import matplotlib.pyplot as plt
    
    save_path = os.path.join(ARTIFACT_DIR, filename)
    
    try:
        exec(chart_code, {"__builtins__": __builtins__})
        plt.savefig(save_path, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close('all')
        return f"[Success] 차트 저장 완료: {filename}"
    except Exception as e:
        plt.close('all')
        return f"[Error] 차트 생성 실패: {e}"
```

**🍌 Nano Banana — AI 인포그래픽 생성 도구 (보너스!):**

Gemini의 이미지 생성 기능을 활용하면, 단순한 matplotlib 차트를 넘어 **AI가 그린 인포그래픽**을 만들 수 있습니다.
(`samples/nano_banana_image_gen.py`에 전체 샘플 코드가 준비되어 있습니다)

```python
@tool(parse_docstring=True)
def generate_infographic(prompt: str, filename: str = "infographic.png") -> str:
    """Gemini 이미지 생성(Nano Banana)을 사용하여 데이터 분석 결과를 
    시각적으로 매력적인 AI 인포그래픽으로 변환합니다.
    
    Args:
        prompt: 생성할 인포그래픽을 설명하는 상세 프롬프트
        filename: 저장할 이미지 파일명
    """
    from google import genai
    from google.genai import types
    from PIL import Image
    from io import BytesIO
    
    client = genai.Client(
        api_key=os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    )
    save_path = os.path.join(ARTIFACT_DIR, filename)
    
    try:
        response = client.models.generate_content(
            model="gemini-3.1-flash-image-preview",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"],
            ),
        )
        for part in response.candidates[0].content.parts:
            if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                image = Image.open(BytesIO(part.inline_data.data))
                image.save(save_path)
                return f"[Success] AI 인포그래픽 생성 완료: {filename}"
        return "[Warning] 이미지 생성 응답이 없습니다."
    except Exception as e:
        return f"[Error] 인포그래픽 생성 실패: {e}"
```

> **💡 활용 예시:** Analyst가 데이터를 분석한 후, 핵심 인사이트를 요약하여
> `generate_infographic("Top 5 인용구 저자의 빈도를 보여주는 귀여운 인포그래픽. Albert Einstein이 1위이고...")` 
> 처럼 호출하면, AI가 시각적으로 아름다운 인포그래픽을 그려줍니다!

**그리고 `app/tools/__init__.py`에 새 도구를 등록하는 것을 잊지 마세요!**

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

**Analyst의 시스템 프롬프트(`app/prompts/analyst.py`)도 직접 작성**해야 합니다!
> - Analyst는 어떤 성격을 가져야 하나요? (꼼꼼한 데이터 사이언티스트? 비즈니스 인사이트 전문가?)
> - 어떤 분석을 우선적으로 수행해야 하나요? (기술 통계? 빈도 분석? 트렌드?)
> - 시각화 스타일에 대한 가이드라인이 필요할까요?

#### Step 4. 파이프라인 연동 — 수집 데이터를 Analyst에게 전달

이제 가장 중요한 부분입니다. Mission 1에서 수집한 JSON 데이터를 Analyst에게 넘겨 분석을 요청하세요.

**방법 A (간단):** 수동으로 Analyst 에이전트를 호출하는 테스트 스크립트 작성
```python
# tests/run_analyst_test.py
analyst = create_analyst_agent()
result = await analyst.ainvoke(
    {"messages": [("user", "artifacts/code/quotes_5pages.json 파일을 분석하고 시각화해주세요.")]},
    config={"configurable": {"thread_id": "analyst_test"}}
)
```

**방법 B (도전):** 기존 Sequential 워크플로우(`workflows/01_sequential_workflow.py`)를 확장하여 `Navigator → Coder → Analyst` 3단계 파이프라인으로 연결

#### Step 5. 분석 결과 확인

Analyst가 생성한 산출물을 확인하세요:
- `artifacts/code/` 에 차트 이미지(`.png`)가 생성되었나요?
- 분석 리포트(`.md`)에 의미 있는 인사이트가 담겨 있나요?
- 데이터의 패턴이나 이상치를 잘 포착했나요?

### ✅ Mission 2 산출물
- [ ] `app/tools/analyst.py` — Analyst 전용 도구 최소 2개 이상
- [ ] `app/prompts/analyst.py` — Analyst 시스템 프롬프트
- [ ] `app/agents/analyst.py` — Analyst 에이전트 팩토리 함수
- [ ] Mission 1에서 수집한 데이터를 Analyst에게 전달하여 생성된 **차트 이미지 1개 이상**
- [ ] (보너스) `Navigator → Coder → Analyst` 3단계 파이프라인 연동

### 🤔 생각해볼 질문
> **"에이전트 1개를 새로 추가하는 데 필요한 것은 무엇이었나요?"**
>
> 도구(Tools) + 프롬프트(Prompt) + 에이전트 팩토리(Agent Factory) + 패키지 등록(__init__.py)
> 이 패턴을 이해했다면, 앞으로 어떤 역할의 에이전트든 동일한 방식으로 확장할 수 있습니다.
> QA 에이전트, 번역 에이전트, 마케팅 에이전트... 구조는 동일합니다.

---

## 🔴 Mission 3: 에이전트 고도화 — 선택 미션 (~1h)

아래 네 가지 트랙 중 **하나 이상**을 선택하여 도전하세요.  
여러분의 관심사와 시간 상황에 맞게 자유롭게 진행합니다.

### 트랙 A: 🧠 학습하는 에이전트 (Pattern Memory)

**목표:** 에이전트가 시나리오 실행 경험(성공/실패)을 `pattern_memory.json`에 자동 기록하고, 다음 실행 시 미들웨어를 통해 시스템 프롬프트에 자동 주입하는 "지속적 학습 체계"를 구현합니다.

**핵심 구현 요소:**
1. 경험 기록 JSON 스키마 설계 (도메인, 전략, 핵심 학습, 실패 패턴)
2. 평가 완료 후 자동 기록 로직 (Evaluator 확장 또는 별도 스크립트)
3. Dynamic System Prompt 미들웨어 — 관련 경험을 자동 검색하여 프롬프트에 주입

```python
# 미들웨어 핵심 아이디어
@wrap_model_call
async def inject_pattern_memory(request, handler):
    memories = load_pattern_memory()
    relevant = find_relevant_patterns(memories, current_context)
    if relevant:
        augmented = request.system_prompt + format_memories(relevant)
        request = request.override(system_prompt=augmented)
    return await handler(request)
```

**산출물:** `pattern_memory.json` + 미들웨어 코드 + 주입 전/후 성능 비교

---

### 트랙 B: 🔄 Model Fallback 미들웨어

**목표:** 에이전트가 어려운 문제를 만나거나 API 사용량 초과 시, 자동으로 더 강력한(또는 대체) 모델로 전환하는 미들웨어를 구현합니다.

```python
@wrap_model_call
async def model_fallback(request, handler):
    try:
        response = await handler(request)
        if detect_low_quality(response):
            upgraded = request.override(model="gemini-pro-latest")
            return await handler(upgraded)
        return response
    except RateLimitError:
        fallback = request.override(model="gpt-4o-mini")
        return await handler(fallback)
```

**산출물:** 동작하는 Model Fallback 미들웨어 코드 + 전환이 발생한 로그 캡처

---

### 트랙 C: 📚 Skill System 적용

**목표:** 에이전트에게 도메인별 전문 스킬을 동적으로 로드하는 구조를 구현합니다.

**아이디어:**
- `app/skills/ecommerce/` — 이커머스 사이트 전용 셀렉터 패턴 + 가격 파싱 도구
- `app/skills/news/` — 뉴스 사이트 전용 기사 추출 패턴 + 날짜 정규화 도구
- 에이전트가 타겟 사이트의 유형을 파악한 후, 해당 스킬을 동적 장착

**산출물:** 최소 1개의 스킬 폴더(`SKILL.md` + `tools.py`) + 스킬 로딩 미들웨어

---

### 트랙 D: 🆕 나만의 시나리오 작성 & 도전

**목표:** 본인이 실무에서 실제로 수집하고 싶은 데이터 소스를 정하고, 처음부터 끝까지 도전합니다.

**진행:**
1. `artifacts/scenarios/` 에 새 시나리오 `.md` 파일을 YAML Frontmatter 형식으로 작성
2. 에이전트 팀을 투입하여 실행
3. 실패 시 원인을 분석하고 프롬프트를 개선하여 재도전
4. 수집 성공 시 Mission 2의 Analyst에게 분석까지 시켜보기

**산출물:** 작성한 시나리오 파일 + 실행 결과 + 시행착오 회고 기록

---

## 🏆 최종 발표 & 회고

모든 미션을 마친 후, 팀별로 다음 내용을 공유합니다:

1. **완성된 파이프라인 시연**
   - Navigator → Coder → Analyst 파이프라인이 실제로 동작하는 모습
   - Analyst가 생성한 차트와 리포트 시각적 공유
   
2. **가장 인상 깊었던 실패와 해결 과정**
   - 에이전트가 어디서 막혔고, 어떻게 돌파했는가?
   
3. **에이전트 확장의 패턴**
   - "에이전트 1개를 추가하는 데 필요한 것: 도구 + 프롬프트 + 팩토리 + 등록"
   - 이 패턴으로 어떤 새 에이전트를 만들 수 있을까?
   
4. **현업 적용 아이디어**
   - 오늘 구축한 멀티 에이전트 파이프라인을 본인의 업무에 어떻게 적용할 수 있을까?

---

## 📎 빠른 참조 (Quick Reference)

### 프로젝트 실행 명령어
```bash
# 순차 워크플로우 테스트
python -m tests.run_sequential_scenarios

# 슈퍼바이저 워크플로우 테스트
python -m tests.run_supervisor_scenarios
```

### 핵심 파일 위치
| 용도 | 경로 |
|:---|:---|
| Navigator 프롬프트 | `app/prompts/navigator.py` |
| Coder 프롬프트 | `app/prompts/coder.py` |
| Supervisor 프롬프트 | `app/prompts/supervisor.py` |
| Navigator 도구 | `app/tools/navigator.py` |
| Coder 도구 | `app/tools/coder.py` |
| 에이전트 미들웨어 | `app/agents/utils.py` |
| 테스트 시나리오 | `artifacts/scenarios/*.md` |
| 평가 결과 로그 | `artifacts/[scenario_id]/*_log.md` |

### 에이전트 추가 체크리스트 (Mission 2 참고)
```
□ app/tools/[역할].py          ← 도구 구현
□ app/tools/__init__.py        ← 도구 등록 (export)
□ app/prompts/[역할].py        ← 시스템 프롬프트 작성
□ app/prompts/__init__.py      ← 프롬프트 등록 (export)
□ app/agents/[역할].py         ← 에이전트 팩토리 함수
□ app/agents/__init__.py       ← 에이전트 등록 (export)
```

### 시나리오 난이도 가이드
| 난이도 | 시나리오 | 핵심 도전 |
|:---:|:---|:---|
| ⭐ Level 1 | `quotes_01_pagination` | URL 패턴 인식, 정적 페이지 파싱 |
| ⭐ Level 1 | `quotes_02_tag_filter` | 태그 기반 필터링, 경로 조합 |
| ⭐⭐ Level 2 | `ajax_01_playwright_wait` | 동적 렌더링 대기, Playwright 제어 |
| ⭐⭐½ Level 2.5 | `ajax_02_api_reverse_engineering` | 숨겨진 API 발견, 역공학 |
| ⭐⭐⭐ Level 3 | `github_01_trending_scraping` | 실제 동적 사이트, JS 렌더링 DOM 분석 |
| ⭐⭐⭐ Level 3 | `quotes_03_multi_step_crawling` | 다단계 워크플로우, 에이전트 간 데이터 전달 |
| ⭐⭐⭐⭐ Level 4 | `danawa_01_filter_search` | AJAX 동적 로딩, 복잡한 필터 UI, 광고/본문 구분 |
| ⭐⭐⭐⭐½ Level 4.5 | `danawa_02_deep_table_parsing` | 중첩 테이블, 동적 버튼 클릭, 스펙 텍스트 정규화 |
| ⭐⭐⭐⭐⭐ Level 5 | `danawa_03_bulk_detail_crawling` | 2단계(목록→상세) 대량 수집, 페이지네이션, 봇 차단 대응 |

