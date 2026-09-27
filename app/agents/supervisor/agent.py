"""
Supervisor Agent Executor Factory (Trainee Mission 03 & 04)
===============================================================================
Supervisor 에이전트 인스턴스를 조립하고 반환하는 팩토리 모듈입니다.
===============================================================================
"""

import os
import aiosqlite
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langchain.agents import create_agent

from app.utils import init_chat_model
from app.utils.context import AgentContext
from .prompt import SUPERVISOR_SYSTEM_PROMPT
from .tools import tools_supervisor

AGENT_METADATA = {
    "name": "supervisor",
    "description": "사용자의 요청을 수행하며 필요 시 계획을 수립하고 전문 에이전트(Scraper 등)에게 위임하는 메인 어시스턴트"
}

# =============================================================================
# Supervisor 에이전트 팩토리 함수 (Mission 03 & 04)
# =============================================================================
# TODO: missions/03_missions.md [2단계]를 참고하여
#       async def create_agent_executor() 함수를 구현하세요.
#       1. init_chat_model(model="gemini-3.8-flash", temperature=0.0)
#       2. AsyncSqliteSaver 체크포인터 설정 (app/database/checkpoints.db)
#       3. create_agent(model=llm, tools=tools_supervisor, system_prompt=SUPERVISOR_SYSTEM_PROMPT, ...)
#       (create_agent_executor 함수가 정의되면 FastAPI 서버와 Chainlit UI에서 자동으로 감지됩니다.)

# async def create_agent_executor():
#     llm = init_chat_model(model="gemini-3.8-flash", temperature=0.0)
#     ...
#     return supervisor_agent
