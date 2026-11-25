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
   └── skills/       (anti_bot_stealth, api_reverse_engineering 등)
===============================================================================
"""

import json
import os
from langchain.agents import create_agent
from app.utils import init_chat_model
from app.utils.database import get_shared_checkpointer
from app.context import AgentContext

from app.middleware import AgentLogTracer, SkillCatalogMiddleware
from .prompt import BASE_SCRAPER_SYSTEM_PROMPT, get_skill_prompt_builder
from .tools import tools_scraper

AGENT_METADATA = {
    "name": "scraper",
    "description": "사이트 분석 + 크롤링 코드 생성/실행 + 데이터 수집을 수행하는 Scraper 에이전트",
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
    # 1. LLM 설정 — Universal Chat Model Factory 기반 gemini-3.8-flash 사용
    llm = init_chat_model(model="gemini-3.8-flash", temperature=0.0)

    # 2. 공유 SQLite 체크포인터 SSOT
    if checkpointer is None:
        checkpointer = await get_shared_checkpointer()

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

    # 4. Scraper 에이전트 구축
    return create_agent(
        model=llm,
        tools=tools_scraper,
        system_prompt=BASE_SCRAPER_SYSTEM_PROMPT,
        middleware=middleware,
        checkpointer=checkpointer,
        context_schema=AgentContext,
    )
