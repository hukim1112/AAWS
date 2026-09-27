"""
===============================================================================
[AAWS Tools] Supervisor — 오케스트레이션 및 계획 도구 14종 통합 바인딩
===============================================================================
Planning(계획 및 태스크 5종) + Orchestration(서브에이전트 위임 3종) + Common(공통 6종) = 14종
===============================================================================
"""

from app.tools.plan import (
    enter_plan,
    exit_plan,
    task_create,
    task_list,
    task_update,
)

from app.tools.supervisor_tools import (
    list_sub_agents,
    invoke_sub_agent,
    get_sub_agent_job_status,
    InvokeSubAgentInput,
)

from app.tools.common import (
    file_read,
    file_writer,
    file_edit,
    grep_search,
    glob_search,
    web_search,
)

# 👑 Supervisor용 도구 바인딩: 계획(5종) + 오케스트레이션(3종) + 범용(6종) = 14종
tools_supervisor = [
    # 1. Planning & Task Board (5종)
    enter_plan,
    exit_plan,
    task_create,
    task_list,
    task_update,
    # 2. Sub-Agent Orchestration (3종)
    list_sub_agents,
    invoke_sub_agent,
    get_sub_agent_job_status,
    # 3. Common File & Search (6종)
    file_read,
    file_writer,
    file_edit,
    grep_search,
    glob_search,
    web_search,
]

__all__ = [
    "tools_supervisor",
    "list_sub_agents",
    "invoke_sub_agent",
    "get_sub_agent_job_status",
    "InvokeSubAgentInput",
]
