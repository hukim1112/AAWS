"""
===============================================================================
[AAWS Agent] Supervisor — 멀티에이전트 총괄 오케스트레이터
===============================================================================
Planning 도구로 계획을 수립하고, invoke_sub_agent로 전문 sub-agent(Scraper,
Analyst 등)에게 작업을 위임하여 복잡한 멀티스텝 미션을 완수한다.

패키지 구조:
  app/agents/supervisor/
   ├── agent.py      (에이전트 조립 및 팩토리)
   ├── prompt.py     (SUPERVISOR_SYSTEM_PROMPT 및 위임/보고 원칙)
   └── tools.py      (계획 5종 + 오케스트레이션 3종 + 공통 6종 도구 바인딩)
===============================================================================
"""

import os
import json
import aiosqlite
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from app.utils import init_chat_model
from app.utils.context import AgentContext

from .prompt import SUPERVISOR_SYSTEM_PROMPT
from .tools import tools_supervisor

AGENT_METADATA = {
    "name": "supervisor",
    "description": "멀티에이전트 총괄 오케스트레이터 — 계획 수립 후 Scraper/Analyst 등 전문 에이전트에게 작업을 위임하고 결과를 종합하여 보고합니다.",
}


def _load_config(path: str, default: dict) -> dict:
    """설정 파일을 로드합니다. 실패 시 기본값을 반환합니다."""
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return default


async def create_agent_executor():
    # 1. LLM 설정
    llm = init_chat_model(model="gemini-3.8-flash", temperature=0.0)

    # 2. AsyncSqliteSaver 기반 체크포인터 (SQLite 영구 메모리)
    db_dir = "app/database"
    os.makedirs(db_dir, exist_ok=True)
    checkpoints_path = os.path.join(db_dir, "checkpoints.db")

    conn = await aiosqlite.connect(checkpoints_path, check_same_thread=False)
    checkpointer = AsyncSqliteSaver(conn)
    await checkpointer.setup()

    # 3. HITL 미들웨어 동적 구성 (configs/hitl.config 기반)
    hitl_cfg = _load_config("./configs/hitl.config", {"hitl_enabled": False})
    middleware = []
    if hitl_cfg.get("hitl_enabled"):
        interrupt_on = hitl_cfg.get("interrupt_on", {})
        if interrupt_on:
            middleware.append(
                HumanInTheLoopMiddleware(
                    interrupt_on=interrupt_on,
                    description_prefix="Supervisor 도구 실행 승인 요청",
                )
            )

    # 4. Supervisor 에이전트 구축
    #    tools_supervisor = Planning(5) + Orchestration(3) + Common(6) = 14종
    supervisor_agent = create_agent(
        model=llm,
        tools=tools_supervisor,
        system_prompt=SUPERVISOR_SYSTEM_PROMPT,
        middleware=middleware,
        checkpointer=checkpointer,
        context_schema=AgentContext,
    )
    return supervisor_agent
