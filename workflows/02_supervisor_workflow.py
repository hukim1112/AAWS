import sys
import os
import json

from langchain.tools import tool, ToolRuntime
from langchain.chat_models import init_chat_model
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

# Load environment
from dotenv import load_dotenv
load_dotenv(override=True)


def extract_text_content(content) -> str:
    """AIMessage.content에서 순수 텍스트만 추출합니다.
    
    Gemini는 .content를 list[dict|str] 형태(서명 블록 포함)로 반환할 수 있고,
    다른 모델은 plain str을 반환합니다. 이 함수는 두 경우 모두 처리합니다.
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_parts = []
        for part in content:
            if isinstance(part, dict):
                text_parts.append(part.get('text', ''))
            elif isinstance(part, str):
                text_parts.append(part)
        return ''.join(text_parts)
    return str(content)

# Project Root Setup
project_root = os.getenv("PROJECT_ROOT", os.getcwd())
if not os.path.exists(os.path.join(project_root, "workflows")):
    current = os.getcwd()
    for _ in range(5):
        if os.path.exists(os.path.join(current, "workflows")):
            project_root = current
            break
        current = os.path.dirname(current)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.agents import create_navigator_agent, create_coder_agent
from app.schemas import NavigatorContext, SeniorCoderContext
from app.prompts import SUPERVISOR_SYSTEM_PROMPT

# 추가 유틸리티 툴스 (Tool Factory)
from app.tools import tools_supervisor

from browser_use import Agent, Browser, ChatGoogle

# 하위 에이전트는 전역에서 한 번만 생성하고 재사용하여 메모리/맥락(Checkpointer)을 유지합니다.

# =========================================================
# 1. 하위 에이전트 인스턴스 전역 생성 (상태 유지용)
# =========================================================
GLOBAL_NAVIGATOR_AGENT = create_navigator_agent()
GLOBAL_CODER_AGENT = create_coder_agent()

# =========================================================
# 2. 분리된(Context Isolated) Handoff 도구 (Agents as Tools 패턴)
# =========================================================

@tool(parse_docstring=True)
async def chat_to_navigator(request: str, runtime: ToolRuntime, config: RunnableConfig, url: str = "", mode: str = "blueprint") -> str:
    """웹사이트의 구조를 분석하여 데이터를 추출할 수 있는 Blueprint(설계도)를 만들기 위해 웹탐색 전문가인 네비게이터와 대화합니다.
    사용자가 특정 크롤링을 원하거나 질문/인사가 있을 때 가장 먼저 이 도구를 사용하여 네비게이터에게 지시하세요.
    
    Args:
        request: 네비게이터에게 전달할 지시사항, 목표, 질문, 인사말 등 (예: '정치 섹션 메인 기사 5개 제목과 링크', '무신사 사이트 크롤링 어떻게 해?', '안녕하세요')
        url: 분석할 웹페이지의 기본 URL (반드시 http/https 포함). 단순 질문/대화이거나 특정 URL이 필요하지 않은 경우 빈 문자열("")로 둡니다.
        mode: 실행 모드. 청사진 생성이면 'blueprint', 단순 자연어 대화/질문/탐색이면 'chat'
    """

    prompt = f"Request: {request}\nTarget URL: {url}\nMode: {mode}"
    print(f"\n👨‍💼 [Supervisor] Navigator와 대화 중...(Mode: {mode}, URL: {url or '없음'})")

    # Runtime Context용 공유 브라우저 인스턴스 생성
    browser_instance = Browser(
        headless=False,
        disable_security=True,
        keep_alive=True,
    )

    ctx = NavigatorContext(shared_browser=browser_instance, response_mode=mode)
    
    try:
        # FastAPI/UI로 이벤트를 전달하기 위해 원본 config(callbacks 포함)를 그대로 전달해야 합니다.
        # thread_id만 현재의 것을 유지/추가합니다.
        inner_config = config.copy() if config else {}
        inner_config["configurable"] = inner_config.get("configurable", {}).copy()
        inner_config["configurable"]["thread_id"] = config.get("configurable", {}).get("thread_id", "default_thread")
        
        result = await GLOBAL_NAVIGATOR_AGENT.ainvoke(
            {"messages": [("user", prompt)]},
            context=ctx,
            config=inner_config
        )
        return_content = extract_text_content(result["messages"][-1].content)
        print(f"\n🔍 [DEBUG] chat_to_navigator 반환값 길이: {len(return_content)}자")
        print(f"🔍 [DEBUG] chat_to_navigator 반환값 시작 200자: {return_content[:200]}")
        return return_content
    finally:
        if browser_instance:
            await browser_instance.stop()
        

@tool(parse_docstring=True)
async def chat_to_coder(task_description: str, runtime: ToolRuntime, config: RunnableConfig, blueprint_info: str = "") -> str:
    """Coder에게 파이썬 코드 작성, 실행, 디버깅 등의 작업을 지시할 때 사용합니다.
    크롤링 스크립트 기반 코딩 작업을 지시할 때는 Navigator가 생성한 Blueprint를 함께 전달하고, 단순 코딩이나 질문을 할 때는 빈 문자열("")을 넘기고 자연어로 지시하세요.
    
    Args:
        task_description: 작성할 스크립트의 코드 구현 목표 및 구체적 요구사항, 또는 코딩 관련 질문
        blueprint_info: Navigator가 찾아낸 렌더링 방식 및 대상 사이트 구조 정보(Blueprint). 웹 스크래핑 관련 지시가 아니면 빈 문자열("")로 둡니다.
    """
    
    prompt = f"다음 [Task]를 수행하세요.\n\n[Task]\n{task_description}"
    if blueprint_info:
        prompt += f"\n\n[Blueprint]\n{blueprint_info}"
        
    print(f"\n👨‍💼 [Supervisor] Coder와 대화 중...")
    
    inner_config = config.copy() if config else {}
    inner_config["configurable"] = inner_config.get("configurable", {}).copy()
    inner_config["configurable"]["thread_id"] = config.get("configurable", {}).get("thread_id", "default_thread")
    
    result = await GLOBAL_CODER_AGENT.ainvoke(
        {"messages": [("user", prompt)]},
        context=SeniorCoderContext(),
        config=inner_config
    )
    return_content = extract_text_content(result["messages"][-1].content)
    print(f"\n🔍 [DEBUG] chat_to_coder 반환값 길이: {len(return_content)}자")
    print(f"🔍 [DEBUG] chat_to_coder 반환값 시작 200자: {return_content[:200]}")
    print(f"🔍 [DEBUG] chat_to_coder 반환값 끝 200자: ...{return_content[-200:]}")
    return return_content


# =========================================================
# 3. Supervisor Agent 구성
# =========================================================

# SUPERVISOR_SYSTEM_PROMPT is imported from app.prompts

supervisor_model = init_chat_model("google_genai:gemini-2.5-pro", temperature=0.1)
supervisor_checkpointer = InMemorySaver()

supervisor_agent = create_agent(
    model=supervisor_model,
    system_prompt=SUPERVISOR_SYSTEM_PROMPT,
    tools=[chat_to_navigator, chat_to_coder] + tools_supervisor,
    checkpointer=supervisor_checkpointer,
    name="supervisor_agent"
)

# 외부 모듈에서 agent_executor로 접근할 수 있게 alias 지정
agent_executor = supervisor_agent

