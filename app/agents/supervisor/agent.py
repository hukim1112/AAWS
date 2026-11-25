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
   └── tools.py      (계획 5종 + 오케스트레이션 4종 + 범용 8종 도구 바인딩)
===============================================================================
"""

import json
import os
from langchain.agents import create_agent
from app.middleware import AgentLogTracer
from app.utils import init_chat_model
from app.utils.database import get_shared_checkpointer
from app.context import AgentContext

from .prompt import SUPERVISOR_SYSTEM_PROMPT
from .tools import tools_supervisor

AGENT_METADATA = {
    "name": "supervisor",
    "description": "멀티에이전트 총괄 오케스트레이터 — 계획 수립 후 Scraper/Analyst 등 전문 에이전트에게 작업을 위임하고 결과를 종합하여 보고합니다.",
    "roles": ["main"],
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


async def create_agent_executor(checkpointer=None):
    # 1. LLM 설정
    llm = init_chat_model(model="gemini-3.8-flash", temperature=0.0)

    # 2. 공유 SQLite 체크포인터 SSOT
    if checkpointer is None:
        checkpointer = await get_shared_checkpointer()

    # 3. 미들웨어 & Supervisor 에이전트 구축
    #    tools_supervisor = Planning(5) + Orchestration(4) + Common(8) = 17종
    logging_cfg = _load_config("./configs/logging.config", {"logging_enabled": False})
    disk_logging_enabled = bool(logging_cfg.get("logging_enabled", False))
    log_dir = logging_cfg.get("log_dir")
    tracer = (
        AgentLogTracer(log_dir=log_dir, disk_enabled=disk_logging_enabled)
        if log_dir
        else AgentLogTracer(disk_enabled=disk_logging_enabled)
    )
    return create_agent(
        model=llm,
        tools=tools_supervisor,
        system_prompt=SUPERVISOR_SYSTEM_PROMPT,
        middleware=[tracer],
        checkpointer=checkpointer,
        context_schema=AgentContext,
    )
