"""
===============================================================================
[AAWS Agent] Analyst — 데이터 분석·시각화·보고서 전문 에이전트
===============================================================================
데이터 파일(JSON/CSV/Excel 등)을 분석하고, 차트/그래프를 생성하며,
전문적인 Excel 보고서와 인터랙티브 HTML 대시보드를 생성합니다.

패키지 구조:
  app/agents/analyst/
   ├── agent.py      (에이전트 조립 및 팩토리)
   ├── prompt.py     (ANALYST_SYSTEM_PROMPT 및 UI 렌더링 태그 가이드)
   ├── tools.py      (6종 분석/출력 도구 + 6종 공통 도구 바인딩)
   └── skills/       (xlsx_guide, chart_patterns, design_tokens, data_analysis)
===============================================================================
"""

import json
import os
import aiosqlite
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langchain.agents import create_agent
from app.middleware import AgentLogTracer, SkillCatalogMiddleware
from app.utils import init_chat_model
from app.context import AgentContext

from .prompt import BASE_ANALYST_SYSTEM_PROMPT, get_skill_prompt_builder
from .tools import tools_analyst

AGENT_METADATA = {
    "name": "analyst",
    "description": "데이터 분석·시각화·보고서 전문 에이전트 — 데이터 프로파일링, 차트 생성, Excel/HTML 보고서를 생성합니다.",
    "roles": ["main", "sub"],
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

    # 2. AsyncSqliteSaver 기반 체크포인터 (SQLite 영구 메모리)
    conn = None
    if checkpointer is None:
        db_dir = "app/database"
        os.makedirs(db_dir, exist_ok=True)
        checkpoints_path = os.path.join(db_dir, "checkpoints.db")

        conn = await aiosqlite.connect(checkpoints_path, check_same_thread=False)

        await conn.execute("PRAGMA journal_mode=WAL;")

        await conn.execute("PRAGMA busy_timeout=5000;")
        checkpointer = AsyncSqliteSaver(conn)
        await checkpointer.setup()

    # 3. 미들웨어 구성 (AgentLogTracer + SkillCatalogMiddleware)
    logging_cfg = _load_config("./configs/logging.config", {"logging_enabled": False})
    disk_logging_enabled = bool(logging_cfg.get("logging_enabled", False))
    log_dir = logging_cfg.get("log_dir")
    tracer = (
        AgentLogTracer(log_dir=log_dir, disk_enabled=disk_logging_enabled)
        if log_dir
        else AgentLogTracer(disk_enabled=disk_logging_enabled)
    )
    middleware = [tracer, SkillCatalogMiddleware(get_skill_prompt_builder())]

    # 4. Analyst 에이전트 구축
    return create_agent(
        model=llm,
        tools=tools_analyst,
        system_prompt=BASE_ANALYST_SYSTEM_PROMPT,
        middleware=middleware,
        checkpointer=checkpointer,
        context_schema=AgentContext,
    )
