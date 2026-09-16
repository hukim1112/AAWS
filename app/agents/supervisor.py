"""
===============================================================================
[AAWS Mission 03 & 04] Supervisor — 멀티에이전트 총괄 오케스트레이터 (교육생 실습용)
===============================================================================
본 파일은 Mission 03 및 Mission 04 실습 대상 파일입니다.
`notebooks/4_MultiAgent_Orchestration.ipynb` 및 `missions/03_missions.md`를 참고하여
하위 전문 에이전트(Scraper 등)를 오케스트레이션하는 Supervisor 에이전트를 완성하세요.

[실습 단계 가이드]
── [Mission 03: In-Process 인프로세스 오케스트레이터 구축] ──
1. InvokeSubAgentInput (Pydantic 스키마 정의)
   - task_instruction: str (하위 에이전트에게 내릴 명확한 지시문)
   - target_file_list: List[str] (참조하거나 생성할 파일 경로 목록)
   - subagent_role: str (하위 에이전트 역할 페르소나, 기본값: 'scraper')

2. invoke_sub_agent (LangChain Tool 구현)
   - create_scraper_executor()로 하위 에이전트 팩토리 호출
   - Prompt Layering (Worker 전용 지침 주입 & [TASK REPORT] 5줄 요약 보고 강제)
   - Dynamic Context Pruning (부모의 대화 기록 대신 task_instruction 및 target_file_list만 전달)
   - scraper.ainvoke() 실행 후 결과 문자열 반환

3. SUPERVISOR_SYSTEM_PROMPT (시스템 프롬프트 정의)
   - Planning First (enter_plan, task_create로 계획 수립)
   - Delegation via invoke_sub_agent (Scraper에게 데이터 수집 위임)
   - Verification & Consolidation (결과 확인 후 exit_plan 호출 및 최종 종합)

4. create_agent_executor (에이전트 팩토리 함수)
   - LLM 초기화 (init_chat_model)
   - AsyncSqliteSaver 체크포인터 설정
   - 도구 바인딩 (계획 도구 5종 + invoke_sub_agent + 공용 파일 도구)
   - create_agent()로 supervisor_agent 생성 및 반환

── [Mission 04: Long-Running 비동기 아키텍처 업그레이드] ──
5. 프로덕션 도구 교체 (missions/04_missions.md):
   - 로컬 인프로세스 함수 대신 제공된 `app.tools.supervisor_tools` 모듈을 임포트하여
     도구 목록에 교체 바인딩하면, 비동기 백그라운드 Job 및 리액티브 웨이크업이 즉시 활성화됩니다!
===============================================================================
"""

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
    "description": "전체 기획/계획 수립 및 전문 하위 에이전트(Scraper 등)를 오케스트레이션하는 총괄 Supervisor"
}

# =============================================================================
# 1. invoke_sub_agent Pydantic 스키마 및 도구 정의 (Mission 03)
# =============================================================================
# TODO: missions/03_missions.md [2단계]를 참고하여
#       InvokeSubAgentInput 스키마와 invoke_sub_agent 도구를 구현하세요.


# =============================================================================
# 2. Supervisor 시스템 프롬프트 정의
# =============================================================================
# TODO: missions/03_missions.md [2단계]를 참고하여
#       SUPERVISOR_SYSTEM_PROMPT를 정의하세요.


# =============================================================================
# 3. Supervisor 에이전트 팩토리 함수
# =============================================================================
# TODO: missions/03_missions.md [2단계]를 참고하여
#       async def create_agent_executor() 함수를 구현하세요.
#       (create_agent_executor 함수가 정의되면 FastAPI 서버와 Chainlit UI에서 자동으로 감지됩니다.)
