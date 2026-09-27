"""
Supervisor Agent Tools (Trainee Mission 03 & 04)
===============================================================================
하위 전문 에이전트(Scraper 등)를 호출하는 invoke_sub_agent 도구 및
Supervisor가 사용하는 전체 도구 목록(tools_supervisor)을 정의합니다.
===============================================================================
"""

from typing import List
from pydantic import BaseModel, Field
from langchain_core.tools import tool

from app.tools.plan import enter_plan, exit_plan, task_create, task_list, task_update
from app.tools.common import file_read, file_writer, glob_search, grep_search, file_edit, web_search
from app.agents.scraper import create_agent_executor as create_scraper_executor

# =============================================================================
# 1. invoke_sub_agent Pydantic 스키마 및 도구 정의 (Mission 03)
# =============================================================================
# TODO: missions/03_missions.md [2단계]를 참고하여
#       InvokeSubAgentInput 스키마와 invoke_sub_agent 도구를 구현하세요.
#
# class InvokeSubAgentInput(BaseModel):
#     task_instruction: str = Field(description="하위 에이전트에게 내릴 명확하고 구체적인 작업 지시문")
#     target_file_list: List[str] = Field(default_factory=list, description="참조하거나 생성할 대상 파일 경로 목록")
#     subagent_role: str = Field(default="scraper", description="작업을 수행할 전문 에이전트 역할 (기본값: 'scraper')")
#
# @tool(args_schema=InvokeSubAgentInput)
# async def invoke_sub_agent(task_instruction: str, target_file_list: List[str] = [], subagent_role: str = "scraper") -> str:
#     ...

# =============================================================================
# 2. Supervisor 도구 바인딩 목록 (tools_supervisor)
# =============================================================================
# TODO: invoke_sub_agent 도구를 구현한 후 아래 리스트에 추가하세요.
#       (Mission 04에서는 app.tools.supervisor_tools의 프로덕션 비동기 도구로 교체할 수 있습니다.)

tools_supervisor = [
    # Planning & Task Board (5종)
    enter_plan, exit_plan, task_create, task_list, task_update,
    # 공용 파일/검색 도구 (6종)
    file_read, file_writer, file_edit, glob_search, grep_search, web_search,
    # TODO: invoke_sub_agent,
]
