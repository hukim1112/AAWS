from datetime import date
from langgraph.checkpoint.memory import MemorySaver
from langchain.chat_models import init_chat_model
from langchain.agents import create_agent

# 오늘 날짜
today_date = date.today().strftime("%Y-%m-%d")

# System Prompt
system_prompt = f"""
당신은 친절한 AI 어시스턴트입니다.
사용자의 질문에 대해 명확하고 도움이 되는 답변을 제공하세요.

오늘의 날짜 : {today_date}
"""

def get_agent_executor():
    llm = init_chat_model(model="gpt-4o", model_provider="openai")
    memory = MemorySaver()
    
    # 도구가 없는 순수 LLM 챗봇
    basic_agent = create_agent(
        model=llm,
        tools=[],
        system_prompt=system_prompt,
        checkpointer=memory
    )
    return basic_agent

agent_executor = get_agent_executor()
