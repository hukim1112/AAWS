"""
===============================================================================
[AAWS Agent] Scraper — 사이트 분석 + 크롤링 코드 생성/실행 + 데이터 수집
===============================================================================
Navigator(사이트 분석) + Coder(코드 생성/실행) 기능을 통합한 전문 서브 에이전트.
동일 컨텍스트에서 사이트 분석 → 셀렉터 결정 → 스크립트 작성 → 실행 → 검증까지 수행.

패키지 구조:
  app/agents/scraper/
   ├── agent.py      (에이전트 조립 및 팩토리)
   ├── prompt.py     (SCRAPER_SYSTEM_PROMPT 및 6단계 워크플로우 규약)
   ├── tools.py      (14종 네비게이팅 및 코딩 도구 바인딩)
   └── skills/       (anti_bot_stealth, api_reverse_engineering)
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

from .prompt import SCRAPER_SYSTEM_PROMPT
from .tools import tools_scraper

AGENT_METADATA = {
    "name": "scraper",
    "description": "사이트 분석 + 크롤링 코드 생성/실행 + 데이터 수집을 수행하는 Scraper 에이전트",
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
    # 1. LLM 설정 — Universal Chat Model Factory 기반 gemini-3.7-flash 사용
    llm = init_chat_model(model="gemini-3.7-flash", temperature=0.0)

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
                    description_prefix="도구 실행 승인 요청",
                )
            )

    # 4. Scraper 에이전트 구축
    scraper_agent = create_agent(
        model=llm,
        tools=tools_scraper,
        system_prompt=SCRAPER_SYSTEM_PROMPT,
        middleware=middleware,
        checkpointer=checkpointer,
        context_schema=AgentContext,
    )

    return scraper_agent
