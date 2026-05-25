from langchain.chat_models import init_chat_model
from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langgraph.checkpoint.memory import InMemorySaver

from app.schemas import NavigatorBlueprintCollection, NavigatorContext
from app.prompts import NAVIGATOR_SYSTEM_PROMPT
from app.tools import tools_navigator
from .utils import dynamic_response_format

def create_navigator_agent(model_name: str = "google_genai:gemini-2.5-pro", temperature: float = 0.1):
    """구조화된 정보 수집 및 탐색용 에이전트 생성"""
    nav_model = init_chat_model(model_name, temperature=temperature)
    nav_checkpointer = InMemorySaver()
    
    agent = create_agent(
        model=nav_model,
        system_prompt=NAVIGATOR_SYSTEM_PROMPT,
        context_schema=NavigatorContext,
        tools=tools_navigator,
        checkpointer=nav_checkpointer,
        response_format=ToolStrategy(NavigatorBlueprintCollection),
        middleware=[dynamic_response_format]
    )
    return agent
