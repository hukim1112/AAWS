import os
import sys
import json
import asyncio
from dotenv import load_dotenv

from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import StrOutputParser

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

# Load environment
load_dotenv(override=True)

from browser_use import Browser

# `test` 폴더 내의 src.agents, src.schemas 임포트
from app.agents import create_navigator_agent, create_coder_agent
from app.schemas import NavigatorContext, SeniorCoderContext, NavigatorBlueprintCollection
from app.tools import ARTIFACT_DIR

def save_blueprints(collection: NavigatorBlueprintCollection, prefix: str = "blueprint") -> list[str]:
    """수집된 Blueprint를 JSON 파일로 저장하고 경로 목록을 반환"""
    import time
    saved_paths = []
    timestamp = int(time.time())
    
    for i, bp in enumerate(collection.blueprints):
        filename = f"{prefix}_{timestamp}_{i+1}.json"
        filepath = os.path.join(ARTIFACT_DIR, filename)
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(bp.model_dump_json(indent=2))
        
        saved_paths.append(filepath)
        print(f"  [Saved] {filepath}")
        
    return saved_paths

async def run_pipeline():
    """Navigator가 Blueprint를 구조화하고 Coder가 이를 바탕으로 스크래핑을 실행하는 파이프라인"""
    
    # ──────────────────────────────────────────────────────
    # 1. Navigator 실행 (Blueprint 생성)
    # ──────────────────────────────────────────────────────
    print("=" * 60)
    print("🧪 Navigator Agent 기동 (정치 섹션 기사 제목 수집 Blueprint 생성)")
    print("=" * 60)

    navigator_agent = create_navigator_agent()
    
    shared_browser_instance = Browser(
        headless=False,
        disable_security=True,
        keep_alive=True,
    )

    nav_config = {"configurable": {"thread_id": "nav_sequential_test"}}
    nav_context = NavigatorContext(shared_browser=shared_browser_instance, response_mode="blueprint")

    final_messages = []
    async for chunk in navigator_agent.astream(
        {"messages": [HumanMessage(
            "https://news.naver.com에서 정치 섹션의 "
            "최신 기사 제목 5개와 각 기사의 상세 URL을 수집하는 Blueprint를 치밀하게 작성해 주세요. "
            "탐색은 이 URL에서 시작하되, 텍스트(제목)와 링크(URL)의 셀렉터 속성이 명확히 분리된 "
            "완벽한 Blueprint를 설계하는 것이 목표입니다."
        )]},
        config=nav_config,
        context=nav_context,
    ):
        for node_name, state_update in chunk.items():
            if "messages" in state_update:
                msgs = state_update["messages"]
                if not isinstance(msgs, list):
                    msgs = [msgs]
                for msg in msgs:
                    msg_type = getattr(msg, "type", type(msg).__name__)
                    content = getattr(msg, "content", str(msg))
                    if content:
                        print(f"\n🧭 [Navigator -> {node_name}] ({msg_type}):\n{content}")
                    elif hasattr(msg, "tool_calls") and msg.tool_calls:
                        print(f"\n🧭 [Navigator -> {node_name}] ({msg_type}) Calling Tool: {msg.tool_calls[0]['name']}")
                    final_messages.append(msg)
                    
    # 마지막 메시지에서 structured_response 추출
    # LangGraph 상태를 얻기 위해서는 state_update["structured_response"]를 찾거나 해야 함
    response_1 = {"structured_response": None}
    # astream을 쓰면 마지막 state_update에 최종 상태가 담겨있을 것임
    # chunk 변수가 마지막 업데이트를 가리킴
    for node_name, state_update in chunk.items():
        if "structured_response" in state_update:
            response_1["structured_response"] = state_update["structured_response"]

    collection_1: NavigatorBlueprintCollection = response_1["structured_response"]

    print(f"\n✅ 결과: {collection_1.total_jobs}개 Blueprint 생성")
    for i, bp in enumerate(collection_1.blueprints):
        print(f"\n  [Blueprint {i+1}]")
        print(f"    entry_urls : {bp.entry_urls}")
        print(f"    계층 수    : {bp.total_layers}")
        print(f"    렌더링 방식: {bp.rendering_type}")
        print(f"    안티봇 주의: {bp.anti_bot_notes}")

    print("\n📁 파일 저장:")
    os.makedirs(ARTIFACT_DIR, exist_ok=True)
    paths_1 = save_blueprints(collection_1, prefix="test_sequential")

    print("\n🧹 공유 브라우저 인스턴스를 종료합니다...")
    await shared_browser_instance.stop()

    # ────────────────────────────────────────────────────────
    # 2. Coder 실행 (Blueprint 기반 코딩 및 스크래핑)
    # ────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("🤖 Senior Coder Agent 기동 (웹 스크래핑 모드)")
    print("=" * 60)
    
    coder_agent = create_coder_agent()
    coder_config = {"configurable": {"thread_id": "coder_sequential_session"}}
    coder_context = SeniorCoderContext()

    if not paths_1:
         print("❌ Blueprint가 생성되지 않아 파이프라인을 종료합니다.")
         return

    blueprint_path = paths_1[0]
    with open(blueprint_path, "r", encoding="utf-8") as f:
        blueprint_content = f.read()

    print(f"📄 Blueprint 정보({blueprint_path}) 획득 완료. Coder에게 전달합니다...\n")

    mission_query = f"""
    다음은 Navigator 에이전트가 탐색하여 넘겨준 크롤링 설계도(Blueprint) JSON 입니다.

    [크롤링 Blueprint JSON]
    {blueprint_content}

    이걸 바탕으로 데이터를 수집해주세요.
    """
    
    messages = [
        HumanMessage(content=mission_query)
    ]

    print("⏳ Coder 가동 중 (코드 작성 및 실행)... 수십 초가 소요될 수 있습니다.")
    final_messages = []
    async for chunk in coder_agent.astream(
        {"messages": messages},
        config=coder_config,
        context=coder_context
    ):
        for node_name, state_update in chunk.items():
            if "messages" in state_update:
                msgs = state_update["messages"]
                if not isinstance(msgs, list):
                    msgs = [msgs]
                for msg in msgs:
                    msg_type = getattr(msg, "type", type(msg).__name__)
                    content = getattr(msg, "content", str(msg))
                    if content:
                        print(f"\n💻 [Coder -> {node_name}] ({msg_type}):\n{content}")
                    elif hasattr(msg, "tool_calls") and msg.tool_calls:
                        print(f"\n💻 [Coder -> {node_name}] ({msg_type}) Calling Tool: {msg.tool_calls[0]['name']}")
                    final_messages.append(msg)
    
    parser = StrOutputParser()
    final_response = parser.invoke(final_messages[-1]) if final_messages else "No response"

    print("\n" + "=" * 60)
    print("✅ Coder 작업 완료 보고서:")
    print("=" * 60)
    print(final_response)
    return final_response

if __name__ == "__main__":
    asyncio.run(run_pipeline())

