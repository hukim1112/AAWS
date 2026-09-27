import os
import json
from datetime import date
import aiosqlite
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from app.utils import init_chat_model
from app.tools import tools_chatbot
from app.utils.context import AgentContext

AGENT_METADATA = {
    "name": "chatbot",
    "description": "도구 및 모니터링이 활성화된 기준완성형 챗봇 (서버/UI 테스트용)"
}

CHATBOT_SYSTEM_PROMPT = f"""당신은 귀엽고 친밀한 고양이 페르소나를 가진 챗봇 에이전트입니다.
사용자의 질문에 대해 재치있고 흥미롭게 대화를 하세요. 답변은 한국어로 제공하세요.

[파일 저장 규칙]
사용자의 요청으로 파일이나 코드를 생성/저장하는 경우, 프로젝트 루트가 아닌 `artifacts/` 폴더 하위에 저장하세요.

오늘의 날짜 : {date.today().strftime("%Y-%m-%d")}
"""

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
    # 1. 일원화된 utils의 Universal Chat Model Factory를 활용하여 Gemini 3.7 Flash 모델 초기화
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
                    description_prefix="도구 실행 승인 요청"
                )
            )
    
    # 4. 범용 8대 도구가 탑재된 스마트 챗봇 에이전트 구축
    chatbot_agent = create_agent(
        model=llm,
        tools=tools_chatbot,
        system_prompt=CHATBOT_SYSTEM_PROMPT,
        middleware=middleware,
        checkpointer=checkpointer,
        context_schema=AgentContext
    )
    return chatbot_agent
