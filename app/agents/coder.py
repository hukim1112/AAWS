import os
from langchain.chat_models import init_chat_model
from langchain.agents import create_agent
from langchain.agents.middleware import FilesystemFileSearchMiddleware
from langgraph.checkpoint.memory import InMemorySaver

from app.schemas import SeniorCoderContext
from app.prompts import CODER_SYSTEM_PROMPT
from app.tools import tools_coder, ARTIFACT_DIR

def create_coder_agent(model_name: str = "google_genai:gemini-flash-latest", temperature: float = 0.2):
    """데이터 청사진을 코드로 제작/수행하는 Coder 에이전트 생성"""
    model = init_chat_model(model_name, temperature=temperature)
    checkpointer = InMemorySaver()
    
    # artifacts 폴더 전체 컨텍스트용 검색 미들웨어
    test_root_dir = os.path.dirname(ARTIFACT_DIR)
    
    middleware = [
        FilesystemFileSearchMiddleware(
            root_path=test_root_dir,
            use_ripgrep=True,
            max_file_size_mb=10,
        )
    ]
    
    agent = create_agent(
        model=model,
        system_prompt=CODER_SYSTEM_PROMPT,
        context_schema=SeniorCoderContext,
        tools=tools_coder,
        checkpointer=checkpointer,
        middleware=middleware
    )
    return agent
