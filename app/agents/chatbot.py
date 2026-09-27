import os
from datetime import date
import aiosqlite
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langchain.agents import create_agent
from app.utils import init_chat_model
from app.tools import tools_chatbot
from app.tools.custom_tools import read_user_memory, update_user_memory
from app.utils.context import AgentContext

AGENT_METADATA = {
    "name": "chatbot",
    "description": "도구 및 모니터링이 활성화된 기준완성형 챗봇 (서버/UI 테스트용)"
}

CHATBOT_SYSTEM_PROMPT = f"""당신은 귀엽고 친밀한 고양이 페르소나를 가진 챗봇 에이전트입니다.
사용자의 질문에 대해 재치있고 흥미롭게 대화를 하세요. 답변은 한국어로 제공하세요.

[파일 저장 규칙]
사용자의 요청으로 파일이나 코드를 생성/저장하는 경우, 프로젝트 루트가 아닌 `artifacts/` 폴더 하위에 저장하세요.

[행동 규칙 - 기억 관리]
1. 사용자와의 대화가 시작되면 가장 먼저 `read_user_memory`를 호출하여 사용자의 프로필을 확인하고 맞춤 인사를 건네세요.
2. 사용자가 대화 중에 새로운 취미, 경력 변동, 전문 분야 변경 등 자신의 프로필 정보를 알려주면,
   기존 프로필 내용에 해당 변경 사항을 자연스럽게 반영/통합하여 `update_user_memory` 도구를 호출해 USER.md를 최신 상태로 갱신하세요.

오늘의 날짜 : {date.today().strftime("%Y-%m-%d")}
"""


async def create_agent_executor():
    # 1. 일원화된 utils의 Universal Chat Model Factory를 활용하여 Gemini 3.8 Flash 모델 초기화
    llm = init_chat_model(model="gemini-3.8-flash", temperature=0.0)
    
    # 2. AsyncSqliteSaver 기반 체크포인터 (SQLite 영구 메모리)
    db_dir = "app/database"
    os.makedirs(db_dir, exist_ok=True)
    checkpoints_path = os.path.join(db_dir, "checkpoints.db")

    conn = await aiosqlite.connect(checkpoints_path, check_same_thread=False)
    checkpointer = AsyncSqliteSaver(conn)
    await checkpointer.setup()
    
    # 3. 범용 8대 도구 + 커스텀 기억 도구 2종이 탑재된 스마트 챗봇 에이전트 구축
    active_tools = tools_chatbot + [read_user_memory, update_user_memory]
    chatbot_agent = create_agent(
        model=llm,
        tools=active_tools,
        system_prompt=CHATBOT_SYSTEM_PROMPT,
        checkpointer=checkpointer,
        context_schema=AgentContext,
    )
    return chatbot_agent
