"""
app/agents/chatbot/agent.py — 도구 및 모니터링이 활성화된 기준완성형 챗봇

패키지 구조:
  app/agents/chatbot/
   ├── __init__.py    (create_agent_executor, AGENT_METADATA, CHATBOT_SYSTEM_PROMPT, tools_chatbot)
   ├── agent.py       (에이전트 조립 및 팩토리)
   ├── prompt.py      (CHATBOT_SYSTEM_PROMPT)
   └── tools.py       (범용 9대 도구 바인딩)
"""

from langchain.agents import create_agent

from app.utils import init_chat_model
from app.utils.database import get_shared_checkpointer
from app.tools.custom_tools import read_user_memory, update_user_memory
from app.context import AgentContext
from .prompt import CHATBOT_SYSTEM_PROMPT
from .tools import tools_chatbot

AGENT_METADATA = {
    "name": "chatbot",
    "description": "도구 및 모니터링이 활성화된 기준완성형 챗봇 (서버/UI 테스트용)",
    "roles": ["main"],
}


async def create_agent_executor(checkpointer=None):
    # 1. 일원화된 utils의 Universal Chat Model Factory를 활용하여 Gemini 3.8 Flash 모델 초기화
    llm = init_chat_model(model="gemini-3.8-flash", temperature=0.0)

    # 2. 공유 SQLite 체크포인터 SSOT
    if checkpointer is None:
        checkpointer = await get_shared_checkpointer()

    # 3. 범용 9대 도구 + 커스텀 기억 도구 2종이 탑재된 스마트 챗봇 에이전트 구축
    active_tools = list(tools_chatbot) + [read_user_memory, update_user_memory]
    chatbot_agent = create_agent(
        model=llm,
        tools=active_tools,
        system_prompt=CHATBOT_SYSTEM_PROMPT,
        checkpointer=checkpointer,
        context_schema=AgentContext,
    )
    return chatbot_agent
