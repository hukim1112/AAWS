# 🎯 Mission 03: Supervisor 멀티에이전트 구축 및 Scraper 위임 실습

본 미션은 `notebooks/4_MultiAgent_Orchestration.ipynb`에서 학습한 **Supervisor & Worker (Agent-as-Tool) 멀티에이전트 오케스트레이션 패턴**을 실제 프로덕션 서버에 구현하는 실습 과제입니다.

노트북에서 배운 **`invoke_sub_agent` 도구 규격(Pydantic 스키마, `target_file_list`, `[TASK REPORT]` 반환 프로토콜)**을 그대로 적용하여 `app/agents/supervisor.py`를 완성하고, **Chainlit Chat UI에서 Supervisor에게 웹 데이터 수집을 지시하여 Scraper가 자율 수집해오는 전체 협업 파이프라인을 성공시키는 것**이 최종 목표입니다.

---

## 📂 실습 대상 및 핵심 파일
* **사전 학습 노트북**: `notebooks/4_MultiAgent_Orchestration.ipynb`
* **멀티에이전트 구축 대상 파일**: `app/agents/supervisor.py` (직접 구현)
* **하위 전문 에이전트 / 도구**: `app/agents/scraper.py` / `app/tools`
* **계획 및 태스크 도구**: `app/tools/plan.py` (`enter_plan`, `task_create`, `task_list`, `task_update`, `exit_plan`)
* **공용 파일 도구**: `app/tools/common.py`
* **시스템 프롬프트**: `app/prompts/`

---

## 📋 미션 목표
1. **[노트북 학습]**: `notebooks/4_MultiAgent_Orchestration.ipynb`를 실행하며 정보 격리(Context Isolation), 5대 협업 프로토콜, Planning 도구 및 `invoke_sub_agent` 패턴을 완벽히 이해합니다.
2. **[Supervisor 에이전트 구현]**: 노트북의 `InvokeSubAgentInput` Pydantic 스키마와 `invoke_sub_agent` 도구를 그대로 탑재한 `app/agents/supervisor.py`를 작성합니다.
3. **[서버 & Chat UI 연동]**: FastAPI 서버와 Chainlit UI를 띄워 `supervisor` 프로필이 정상 등록되는지 확인합니다.
4. **[멀티에이전트 오케스트레이션 검증]**: Chat UI에서 사용자로서 Supervisor에게 데이터 수집을 요청하고, Supervisor가 계획을 세워 `invoke_sub_agent`로 Scraper에게 위임한 뒤 최종 결과 요약을 보고하는지 확인합니다.

---

## 🛠️ 단계별 수행 가이드

### 1단계: `notebooks/4_MultiAgent_Orchestration.ipynb` 핵심 패턴 복습

노트북 Part 3~4에서 다룬 **멀티에이전트 협업 핵심 원칙**을 확인하세요:
1. **`InvokeSubAgentInput` (Pydantic 스키마)**:
   - `task_instruction: str`: 구체적인 작업 지시문
   - `target_file_list: List[str]`: 하위 에이전트가 참조하거나 생성할 파일 목록
   - `subagent_role: str`: 하위 에이전트의 역할 페르소나 (기본값 `"scraper"`)
2. **서브에이전트 프로토콜 오버레이 (3-Layer Protocol Overlay)**:
   - 부모의 전체 대화 히스토리를 넘기지 않고, `[SUB-AGENT MODE - STRICT PROTOCOL]` 헤더와 함께 인계 파일 및 지시문만 `HumanMessage`로 격리 주입
3. **원칙 중심 프롬프팅 (Principle-over-Micromanagement)**:
   - 시스템 프롬프트에 도구 호출 절차(Call enter_plan 등)를 마이크로매니징하지 않고, **계획 수립 및 공유, 장애 자가 치유(Backtracking), 결과 중심 브리핑**이라는 상위 원칙만 주입
4. **계획에 대한 단일 수정자 원칙 (Single Writer Principle)**:
   - 하위 에이전트는 인계받은 계획을 읽어 맥락만 파악하고, 직접 계획표를 수정하지 않고 제안만 하도록 규약화
5. **`[TASK REPORT]` 반환 프로토콜**:
   - 세부 수집 데이터는 디스크(`artifacts/data/`)에 파일로 저장하고, 부모에게는 **5줄 요약 포인터**만 반환

---

### 2단계: `app/agents/supervisor.py` 구현하기

> 💡 **[안내] 테스트 및 코드 수정 권장**:
> 아래에 제공된 코드는 여러분의 구현을 돕기 위한 **참고용 예시 코드(Reference Implementation)**입니다.
> 그대로 사용하기보다는, **직접 서버와 Chat UI에서 테스트를 돌려보며 시스템 프롬프트, 위임 로직, 파라미터 등을 필요에 맞게 능동적으로 수정하고 튜닝**해 보세요!

`app/agents/supervisor.py` 파일을 생성하고, 노트북의 `invoke_sub_agent` 도구 패턴을 반영하여 아래와 같이 작성합니다:

```python
# app/agents/supervisor.py

import os
import json
import asyncio
from typing import List
from pydantic import BaseModel, Field
import aiosqlite

from langchain_core.tools import tool
from langchain.agents import create_agent
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langchain_core.messages import HumanMessage

from app.utils import init_chat_model, normalize_content
from app.utils.context import AgentContext
from app.tools.plan import enter_plan, exit_plan, task_create, task_list, task_update
from app.tools.common import file_read, file_writer, glob_search, grep_search
from app.agents.scraper import create_agent_executor as create_scraper_executor

AGENT_METADATA = {
    "name": "supervisor",
    "description": "사용자의 요청을 수행하며 필요 시 계획을 수립하고 전문 에이전트(Scraper 등)에게 위임하는 메인 어시스턴트"
}

# =============================================================================
# 1. invoke_sub_agent Pydantic 스키마 및 도구 정의
# =============================================================================

class InvokeSubAgentInput(BaseModel):
    task_instruction: str = Field(
        description="A clear, actionable step-by-step instruction detailing what the worker agent should crawl, calculate, and report."
    )
    target_file_list: List[str] = Field(
        default_factory=list,
        description="List of relative file paths that the sub-agent needs to inspect or generate (e.g. ['artifacts/data/quotes_multiagent.json'])."
    )
    subagent_role: str = Field(
        default="scraper",
        description="The persona and specialty of the sub-agent (e.g. 'scraper', 'analyst')."
    )

@tool(args_schema=InvokeSubAgentInput)
async def invoke_sub_agent(task_instruction: str, target_file_list: List[str] = [], subagent_role: str = "scraper") -> str:
    """Forks an isolated, sandboxed sub-agent with a dedicated worker persona to execute focused web scraping, discovery, or data analysis tasks.

    The sub-agent operates in an isolated ReAct loop, writes detailed artifacts directly to disk, and returns only a concise 5-line summary report.

    Args:
        task_instruction: Specific task directive for the sub-agent.
        target_file_list: List of file paths for the sub-agent to inspect or write.
        subagent_role: Role persona assigned to the sub-agent.

    Returns:
        A formatted `[TASK REPORT]` string containing Status (SUCCESS/BLOCKER), Target files, Artifacts Created, Summary, and Issues.
    """
    scraper = await create_scraper_executor()
    
    file_list_str = ", ".join(target_file_list) if target_file_list else "None"
    
    # 🌟 [3-Layer Architecture] 범용 Sub-Agent Protocol Overlay 주입
    # (특정 도메인을 하드코딩하지 않고, 침묵 실행/계획 참조 및 단일 수정자 원칙/블로커/보고서 규약만 주입)
    prompt = f"""[SUB-AGENT MODE - STRICT PROTOCOL]
You are operating as a sub-agent under a Main Agent. You MUST follow these rules:
1. NO greetings or conversational responses. Execute the task immediately.
2. Context & Plan: If a plan is shared, refer to it to understand the broader context.
   Do NOT modify the plan yourself. If adjustments are needed, propose them in your report.
3. On ANY blocker (site blocked / selector failure / access denied):
   STOP immediately and return EXACTLY:
   [BLOCKER: <concise reason>]
4. On success: write all detailed results to disk first, then return EXACTLY:
   [TASK REPORT]
   - Status: SUCCESS
   - Target Files: {file_list_str}
   - Artifacts Created: <created file paths>
   - Summary: <1-2 sentence core finding>
   - Issues: None (or proposed plan adjustments)
══════════════════════════════════════════════════════════
Target Files: {file_list_str}
Instruction: {task_instruction}"""
    
    config = {"configurable": {"thread_id": f"sub_{int(asyncio.get_event_loop().time() * 1000)}"}}
    response = await scraper.ainvoke(
        {"messages": [HumanMessage(content=prompt)]},
        config=config
    )
    
    return normalize_content(response["messages"][-1].content)


# =============================================================================
# 2. Supervisor 시스템 프롬프트 정의 (원칙 중심 프롬프팅: Principle-over-Micromanagement)
# =============================================================================

SUPERVISOR_SYSTEM_PROMPT = """당신은 사용자의 요청을 편안하게 도와드리는 유능한 AI 어시스턴트입니다.
질문에 답하고, 정보를 검색하고, 코드를 작성하고, 파일을 다루는 등 다양한 범용 작업을 직접 수행합니다.
필요한 경우에는 전문 에이전트를 활용하여 웹 데이터 수집 같은 복잡한 작업도 해결합니다.

═══════════════════════════════════════════════════════════════
[작업 원칙]
═══════════════════════════════════════════════════════════════

1. **작업 규모에 맞게 처리하기**:
   - 간단한 질의나 즉시 처리가 가능한 작업은 곧바로 수행하세요.
   - 여러 단계가 필요한 복잡한 작업은 계획을 먼저 세우고 수행하세요.
   - 전문가에게 작업을 위임할 때는 수립한 계획도 함께 공유하여 전체 맥락을 파악하고 일할 수 있게 하세요.

2. **전문가 활용하기**:
   - 웹 데이터 수집, 스크래핑 등 전문 작업은 `invoke_sub_agent` 도구를 통해 전문 에이전트에게 위임하세요.
   - 상세 위임 절차 및 파라미터는 `invoke_sub_agent` 도구의 설명을 참고하세요.

3. **실패해도 멈추지 않기**:
   - 위임한 작업이 막히거나 장애([BLOCKER])가 발생하더라도 포기하지 마세요.
   - 원인을 파악하고 대안 경로를 찾아 끝까지 완수하세요.

═══════════════════════════════════════════════════════════════
[답변 방식]
═══════════════════════════════════════════════════════════════

- 친근하고 명확한 어조로 답변하며, 불필요한 장황한 설명보다는 결과 중심으로 답변하세요.
- 수집된 데이터나 상세 산출물은 파일(artifacts/)로 저장하고, 사용자에게는 핵심 요약과 파일 경로를 깔끔하게 전달하세요.
"""


# =============================================================================
# 3. Supervisor 에이전트 팩토리 함수
# =============================================================================

async def create_agent_executor():
    llm = init_chat_model(model="gemini-3.7-flash", temperature=0.0)
    
    db_dir = "app/database"
    os.makedirs(db_dir, exist_ok=True)
    checkpoints_path = os.path.join(db_dir, "checkpoints.db")
    
    conn = await aiosqlite.connect(checkpoints_path, check_same_thread=False)
    checkpointer = AsyncSqliteSaver(conn)
    await checkpointer.setup()
    
    tools = [
        enter_plan, exit_plan, task_create, task_list, task_update,
        invoke_sub_agent,
        file_read, file_writer, glob_search, grep_search
    ]
    
    supervisor_agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt=SUPERVISOR_SYSTEM_PROMPT,
        checkpointer=checkpointer,
        context_schema=AgentContext
    )
    return supervisor_agent
```

---

### 3단계: 서버 및 Chainlit UI 가동

터미널 2개에서 백엔드 서버와 프론트엔드 UI를 실행합니다:

#### 🖥️ 터미널 1 (FastAPI 백엔드 가동):
```bash
python app/server.py --port 8000
```
*(성공 로그: `✅ Loaded agent module: app.agents.supervisor` 및 `Uvicorn running on http://0.0.0.0:8000`)*

#### 🌐 터미널 2 (Chainlit UI 가동):
```bash
chainlit run app/chainlit_ui.py --port 8080
```

---

### 4단계: Chat UI에서 멀티에이전트 수집 지시 및 성공 검증

1. 웹 브라우저에서 `http://localhost:8080` 접속 후 로그인(`user` / `1234`).
2. 좌측 상단 프로필 선택창에서 **`supervisor`** 에이전트를 선택합니다.
3. 채팅 입력창에 다음 메시지를 전송합니다:

```text
http://quotes.toscrape.com 사이트에서 1~2페이지의 명언(text, author, tags)을 수집해서 
'artifacts/data/quotes_multiagent.json' 파일로 저장하고, 수집된 결과 요약을 보고해줘.
```

#### 🧪 실행 궤적(Trajectory) 관찰 포인트:
1. **Supervisor의 자율적 계획 수립**: 작업 규모를 판단하여 Task Board에 계획 및 세부 태스크 등록
2. **하위 Scraper 위임**: 수립한 계획 및 타겟 파일(`target_file_list=['artifacts/data/quotes_multiagent.json']`)과 함께 `invoke_sub_agent` 호출 (맥락 인계)
3. **Scraper의 독립 실행**:
   - 인계받은 계획을 참조하여 DOM 탐색 (`extract_dom_skeleton` / `verify_selectors`)
   - `file_writer`로 수집 스크립트 작성 및 `bash_command`로 실행하여 JSON 파일 생성
   - 직접 계획표를 수정하지 않고 규격화된 `[TASK REPORT]`로 결과 보고
4. **Supervisor의 태스크 완료 및 최종 보고**:
   - `task_update` (`COMPLETED`) ➔ `exit_plan` ➔ 사용자에게 깔끔한 수집 통계 및 샘플 보고 완료!

---

## ✅ 성공 검증 체크리스트
- [ ] `notebooks/4_MultiAgent_Orchestration.ipynb`를 확인하고 원칙 중심 프롬프팅 및 `invoke_sub_agent` 규약을 이해했는가?
- [ ] `app/agents/supervisor.py`에 원칙 중심의 `SUPERVISOR_SYSTEM_PROMPT`와 `invoke_sub_agent` 도구가 정확히 구현되었는가?
- [ ] Chainlit UI에서 `supervisor` 프로필이 정상적으로 나타나고 선택 가능한가?
- [ ] Supervisor가 `invoke_sub_agent`로 Scraper에게 작업을 위임하여 실제 `artifacts/data/quotes_multiagent.json` 파일이 생성되었는가?
- [ ] 전체 멀티에이전트 실행 루프가 에러 없이 성공적으로 마무리되었는가?

축하합니다! 이제 여러분은 단일 에이전트의 한계를 넘어, **복잡한 엔지니어링 및 데이터 분석 작업을 여러 전문 에이전트에게 자율적으로 분배하고 통제하는 멀티에이전트 오케스트레이터**를 완성했습니다. 👑🚀
