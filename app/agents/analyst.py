"""
app/agents/analyst.py
=====================
데이터 수집 결과 및 실행 관찰(Observability) 분석 전문 에이전트 (Analyst Agent)
"""

from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver

from app.prompts import ANALYST_SYSTEM_PROMPT
from app.tools import tools_analyst
from app.utils import get_llm

def create_analyst_agent(model_name: str = "gemini-2.5-pro", temperature: float = 0.1):
    """데이터 품질/비용 진단, 시각화, 인포그래픽, 수집 전략 저장을 전담하는 Analyst 에이전트 생성"""
    analyst_model = get_llm(model_name, temperature=temperature)
    analyst_checkpointer = InMemorySaver()

    agent = create_agent(
        model=analyst_model,
        system_prompt=ANALYST_SYSTEM_PROMPT,
        tools=tools_analyst,
        checkpointer=analyst_checkpointer,
        name="analyst_agent"
    )
    return agent
