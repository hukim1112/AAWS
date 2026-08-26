# 🎯 Mission 04: 나만의 커스텀 서브 에이전트(Custom Sub-Agent) 기획·개발 및 Supervisor 연동

본 미션은 지금까지 배운 에이전트 설계 기법(ReAct, Tool 바인딩, System Prompt, Context Isolation)을 종합하여, **여러분만의 창의적인 전문 서브 에이전트(Custom Sub-Agent)를 직접 기획·구현하고 `supervisor`에 연결하여 2단계 이상의 자율 협업 파이프라인을 완성**하는 최종 캡스톤 실습 과제입니다.

Supervisor 아래에 어떤 전문 영역의 에이전트를 둘 것인지는 **여러분의 자유로운 선택**에 달려 있습니다!

---

## 📂 실습 대상 및 핵심 파일
* **신규 서브 에이전트 파일**: `app/agents/[자신만의_에이전트명].py` (직접 구현)
* **총괄 오케스트레이터 파일**: `app/agents/supervisor.py` (하위 에이전트 분기 연결)
* **활용 도구 모음**: `app/tools/common.py` 및 커스텀 도구
* **산출물 보관소**: `artifacts/` (리포트, 정제 데이터, 콘텐츠 등)

---

## 📋 미션 목표
1. **[도메인 선택 및 기획]**: 해결하고 싶은 문제에 맞는 서브 에이전트의 역할(Persona), 도구(Tools), 기대 산출물을 정의합니다.
2. **[서브 에이전트 모듈 구현]**: `app/agents/` 디렉토리에 독립된 에이전트 모듈을 작성합니다.
3. **[Supervisor 위임 분기 연동]**: `app/agents/supervisor.py`의 `invoke_sub_agent` 도구에 신규 에이전트 분기 로직을 연결합니다.
4. **[End-to-End 멀티에이전트 통합 검증]**: Chat UI에서 Supervisor에게 복합 지시를 내려 **`Supervisor ➔ Scraper(수집) ➔ Custom Sub-Agent(가공/분석/창작)`**의 전체 파이프라인이 매끄럽게 동작하는지 확인합니다.

---

## 💡 서브 에이전트 트랙 선택 가이드 (자유 선택)

여러분의 관심사나 실무 도메인에 맞는 트랙을 하나 선택하거나, 완전히 새로운 아이디어를 구현해 보세요:

| 트랙 옵션 | 에이전트 페르소나 | 주요 임무 및 핵심 기능 | 최종 산출물 (Artifacts) |
|:---|:---|:---|:---|
| **트랙 A (분석 & 시각화)** | 📊 **Data Analyst** | 수집 데이터 통계 집계(Pandas), 차트 이미지(.png) 생성, 인사이트 분석 | `artifacts/reports/*.png`, `*_report.md` |
| **트랙 B (콘텐츠 창작)** | ✍️ **Content Creator** | 수집된 데이터를 가공하여 블로그 포스팅, 카드뉴스 카피, 마케팅 슬로건 제작 | `artifacts/reports/marketing_post.md` |
| **트랙 C (데이터 품질 QA)** | 🔍 **Data Validator** | 수집된 데이터의 스키마 일치도, 결측치, 중복값 정제 및 데이터 품질 리포트 발행 | `artifacts/data/cleaned_data.json` |
| **트랙 D (요약 & 브리핑)** | 📑 **Executive Briefer** | 방대한 데이터를 바쁜 의사결정자를 위한 1페이지 핵심 불릿 브리핑 문서로 요약 | `artifacts/reports/executive_summary.md` |
| **트랙 E (자유 트랙)** | 🎨 **Custom Specialist** | 번역/로컬라이저, 법률/규정 검토기, 이메일 드래프터 등 자유 기획 | 자유 형식의 산출물 |

---

## 🛠️ 단계별 수행 가이드

### 1단계: 서브 에이전트 모듈 구현 (`app/agents/[에이전트명].py`)

`app/agents/` 디렉토리에 원하는 이름의 파일(예: `analyst.py`, `creator.py`, `validator.py` 등)을 생성하고, 아래의 기본 뼈대를 바탕으로 도구와 시스템 프롬프트를 구성합니다:

```python
# app/agents/custom_worker.py (예시 뼈대)

import os
import json
import asyncio
from langchain.agents import create_agent
from app.utils import init_chat_model
from app.tools.common import file_read, file_writer, bash_command, glob_search
from app.utils.context import AgentContext

AGENT_METADATA = {
    "name": "custom_worker",  # 여러분의 에이전트 이름
    "description": "특정 전문 작업을 수행하는 서브 에이전트"
}

# 1. 서브 에이전트 전용 시스템 프롬프트 정의
WORKER_SYSTEM_PROMPT = """
당신은 [전문 역할명] 에이전트입니다.
당신의 임무는 전달받은 대상 파일(`target_file_list`)의 데이터를 가공/분석하여 요구된 산출물을 생성하는 것입니다.

[행동 수칙]
1. `file_read` 등으로 입력 데이터를 확인하세요.
2. 필요한 도구(`bash_command`, `file_writer` 등)를 활용하여 작업을 수행하고 결과 산출물을 `artifacts/` 폴더에 파일로 저장하세요.
3. 작업 완료 후 Supervisor에게는 다음 5줄 요약 포맷으로만 간결히 보고하세요:
   [TASK REPORT]
   - Status: SUCCESS | FAILED | BLOCKER
   - Target Files: (대상 파일 경로)
   - Artifacts Created: (생성한 산출물 파일 경로)
   - Summary: (핵심 결과 요약 1~2줄)
   - Issues: None
"""

# 2. 에이전트 팩토리 함수
async def create_agent_executor():
    llm = init_chat_model(model="gemini-3.7-flash", temperature=0.0)
    
    # 에이전트에게 필요한 도구 목록 선택
    tools = [file_read, file_writer, bash_command, glob_search]
    
    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt=WORKER_SYSTEM_PROMPT,
        context_schema=AgentContext
    )
    return agent
```

---

### 2단계: `app/agents/supervisor.py`에 서브 에이전트 분기 연결

[`app/agents/supervisor.py`](file:///c:/Users/hyoun/Desktop/working_project/basic_agent/app/agents/supervisor.py) 파일을 열고, `invoke_sub_agent` 함수에 새로 만든 서브 에이전트를 호출할 수 있도록 분기 로직을 추가합니다:

```python
# app/agents/supervisor.py 수정 예시

from app.agents.scraper import create_agent_executor as create_scraper_executor
from app.agents.custom_worker import create_agent_executor as create_custom_worker_executor  # 👈 추가!

@tool(args_schema=InvokeSubAgentInput)
async def invoke_sub_agent(task_instruction: str, target_file_list: List[str] = [], subagent_role: str = "scraper") -> str:
    """하위 전문 에이전트를 동적으로 분기 실행합니다."""
    
    file_list_str = ", ".join(target_file_list) if target_file_list else "지정 파일 없음"
    role_normalized = subagent_role.lower()
    
    # 💡 역할(Role) 키워드에 따른 동적 에이전트 라우팅
    if "custom" in role_normalized or "analyst" in role_normalized or "creator" in role_normalized:
        worker = await create_custom_worker_executor()
        worker_type = subagent_role
    else:
        worker = await create_scraper_executor()
        worker_type = "Scraper"
        
    prompt = f"""Target File List: {file_list_str}
Instruction: {task_instruction}

[수행 지침]
1. 역할을 성실히 수행하고, 결과 산출물을 디스크(artifacts/)에 저장하세요.
2. 작업 완료 후 반드시 [TASK REPORT] 규격(Status, Target Files, Artifacts Created, Summary, Issues)으로 보고하세요.
"""

    config = {"configurable": {"thread_id": f"{worker_type.lower()}_{int(asyncio.get_event_loop().time() * 1000)}"}}
    response = await worker.ainvoke(
        {"messages": [HumanMessage(content=prompt)]},
        config=config
    )
    
    return normalize_content(response["messages"][-1].content)
```

---

### 3단계: 서버 및 Chat UI 가동

```bash
# 터미널 1 (FastAPI 서버 가동)
python app/server.py --port 8000

# 터미널 2 (Chainlit UI 가동)
chainlit run app/chainlit_ui.py -w --port 8080
```

---

### 4단계: Chat UI에서 복합 파이프라인 통합 테스트

1. 웹 브라우저(`http://localhost:8080`)에 접속하여 **`supervisor`** 에이전트를 선택합니다.
2. 채팅창에 **수집과 여러분의 서브 에이전트 작업이 결합된 복합 미션**을 요청합니다.

#### 💬 요청 프롬프트 예시 (선택한 트랙에 맞게 변형 가능):
* **[분석 트랙 선택 시]**:
  > *"http://quotes.toscrape.com 에서 명언을 수집해 `artifacts/data/quotes.json`에 저장하고, 수집된 데이터를 바탕으로 저자/태그별 통계 차트와 분석 리포트를 작성해줘."*
* **[콘텐츠 창작 트랙 선택 시]**:
  > *"http://quotes.toscrape.com 에서 명언을 수집하고, 이를 바탕으로 직장인을 위한 인스타그램 카드뉴스용 마케팅 카피 5편을 `artifacts/reports/sns_copies.md`로 작성해줘."*
* **[품질 QA 트랙 선택 시]**:
  > *"http://quotes.toscrape.com 에서 데이터를 수집하고, 결측치와 태그 데이터의 정합성을 검증하여 정제된 `artifacts/data/quotes_clean.json` 파일과 품질 검증 리포트를 발행해줘."*

#### 🧪 실행 궤적(Trajectory) 관찰:
1. **Supervisor 계획 수립**: `enter_plan` ➔ [Task 1: 수집] 및 [Task 2: 서브 에이전트 가공] 태스크 생성
2. **Task 1 위임**: `invoke_sub_agent(subagent_role="scraper")`로 데이터 수집 완수
3. **Task 2 위임**: `invoke_sub_agent(subagent_role="[여러분의_서브에이전트]")`로 데이터 2차 가공 및 산출물 생성
4. **Supervisor 최종 종합**: `exit_plan` 호출 및 사용자에게 최종 결과 브리핑 완료!

---

## ✅ 성공 검증 체크리스트
- [ ] 해결하고자 하는 목표에 맞는 서브 에이전트의 역할과 프롬프트가 잘 설계되었는가?
- [ ] `app/agents/`에 신규 서브 에이전트 모듈이 성공적으로 작성되었는가?
- [ ] `app/agents/supervisor.py`에서 `invoke_sub_agent`의 라우팅 분기가 정상 작동하는가?
- [ ] `artifacts/` 디렉토리에 서브 에이전트가 생성한 최종 산출물(JSON, PNG, MD 등)이 올바르게 저장되었는가?
- [ ] Chat UI에서 `Supervisor ➔ Scraper ➔ Custom Sub-Agent`로 이어지는 다단계 오케스트레이션이 완벽히 성공했는가?

축하합니다! 이제 여러분은 단순한 에이전트 사용자를 넘어, **원하는 전문 에이전트를 자유자재로 설계·추가하고 복잡한 엔터프라이즈 워크플로우를 자율 오케스트레이션하는 진정한 AI 에이전트 아키텍트**로 거듭났습니다! 🎓👑🚀
