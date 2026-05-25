import os
import sys
import json
import asyncio
import uuid
import time
from dotenv import load_dotenv

from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import StrOutputParser

# Project Root Setup
project_root = os.getenv("PROJECT_ROOT", os.getcwd())
if not os.path.exists(os.path.join(project_root, "app")):
    current = os.getcwd()
    for _ in range(5):
        if os.path.exists(os.path.join(current, "app")):
            project_root = current
            break
        current = os.path.dirname(current)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Load environment
load_dotenv(override=True)

from browser_use import Browser

# src 모듈 임포트
from app.agents import create_navigator_agent, create_coder_agent
from app.schemas import NavigatorContext, SeniorCoderContext, NavigatorBlueprintCollection
from app.tools import ARTIFACT_DIR

# 시나리오 평가 및 파서 임포트
from app.scenario_parser import Scenario
from app.evaluator import evaluate_scenario_result

async def run_scenario(scenario_file: str):
    """지정된 시나리오 마크다운 파일을 파싱하여 Sequential 파이프라인(Navigator -> Coder)으로 작업을 수행합니다."""
    print("\n" + "=" * 80)
    print(f"🚀 [Sequential] 시나리오 테스트 시작: {os.path.basename(scenario_file)}")
    print("=" * 80)
    
    scenario = Scenario.from_file(scenario_file)
    scenario_out_dir = os.path.join(project_root, "artifacts", "results", scenario.scenario_id)
    os.makedirs(scenario_out_dir, exist_ok=True)
    json_output_path = os.path.join(scenario_out_dir, "seq_result.json")
    log_output_path = os.path.join(scenario_out_dir, "seq_log.md")

    print(f"📝 진행 상황은 터미널과 함께 다음 파일에도 저장됩니다: {log_output_path}")
    
    with open(log_output_path, "w", encoding="utf-8") as log_file:
        log_file.write(f"# 시나리오 실행 로그 (Sequential): {scenario.scenario_id}\n\n")

    # ──────────────────────────────────────────────────────
    # 1. Navigator 실행 (Blueprint 생성)
    # ──────────────────────────────────────────────────────
    print("=" * 60)
    print("🧪 Navigator Agent 기동 (Blueprint 생성)")
    print("=" * 60)

    navigator_agent = create_navigator_agent()
    
    shared_browser_instance = Browser(
        headless=False,
        disable_security=True,
        keep_alive=True,
    )

    thread_id_nav = f"nav_test_{uuid.uuid4().hex[:8]}"
    nav_config = {"configurable": {"thread_id": thread_id_nav}}
    nav_context = NavigatorContext(shared_browser=shared_browser_instance, response_mode="blueprint")

    nav_prompt = f"""
    아래에 제공된 마크다운 시나리오 문서를 읽고, 데이터 수집을 위한 완벽한 Blueprint를 작성해 주세요.
    텍스트와 링크(URL)의 셀렉터 속성이 명확히 분리된 완벽한 Blueprint를 설계하는 것이 목표입니다.
    
    [대상 사이트 정보]
    - 사이트명: {scenario.site_name}
    - 기준 URL: {scenario.target_url}
    
    [시나리오 문서]
    {scenario.prompt}
    """

    final_messages = []
    chunk = None
    try:
        async for chunk_data in navigator_agent.astream(
            {"messages": [HumanMessage(content=nav_prompt)]},
            config=nav_config,
            context=nav_context,
        ):
            chunk = chunk_data
            for node_name, state_update in chunk.items():
                if "messages" in state_update:
                    msgs = state_update["messages"]
                    if not isinstance(msgs, list):
                        msgs = [msgs]
                    for msg in msgs:
                        msg_type = getattr(msg, "type", type(msg).__name__)
                        content = getattr(msg, "content", str(msg))
                        if content:
                            msg_str = f"\n🧭 [Navigator -> {node_name}] ({msg_type}):\n{content}"
                            print(msg_str)
                            with open(log_output_path, "a", encoding="utf-8") as f:
                                f.write(msg_str + "\n\n")
                        elif hasattr(msg, "tool_calls") and msg.tool_calls:
                            msg_str = f"\n🧭 [Navigator -> {node_name}] ({msg_type}) Calling Tool: {msg.tool_calls[0]['name']}"
                            print(msg_str)
                            with open(log_output_path, "a", encoding="utf-8") as f:
                                f.write(msg_str + "\n\n")
                        final_messages.append(msg)
    except Exception as e:
        err_msg = f"\n❌ Navigator 실행 중 오류 발생: {e}"
        print(err_msg)
        with open(log_output_path, "a", encoding="utf-8") as f:
            f.write(err_msg + "\n\n")
        await shared_browser_instance.stop()
        return

    # 마지막 메시지에서 structured_response 추출
    response_1 = {"structured_response": None}
    if chunk:
        for node_name, state_update in chunk.items():
            if "structured_response" in state_update:
                response_1["structured_response"] = state_update["structured_response"]

    collection_1: NavigatorBlueprintCollection = response_1.get("structured_response")

    if not collection_1:
        print("❌ Blueprint가 생성되지 않아 파이프라인을 종료합니다.")
        await shared_browser_instance.stop()
        return

    success_msg = f"\n✅ 결과: {collection_1.total_jobs}개 Blueprint 생성\n"
    for i, bp in enumerate(collection_1.blueprints):
        success_msg += f"\n  [Blueprint {i+1}]\n"
        success_msg += f"    entry_urls : {bp.entry_urls}\n"
        success_msg += f"    계층 수    : {bp.total_layers}\n"
        success_msg += f"    렌더링 방식: {bp.rendering_type}\n"
    print(success_msg)
    with open(log_output_path, "a", encoding="utf-8") as f:
        f.write(success_msg + "\n")

    print("\n📁 Blueprint 파일 저장:")
    os.makedirs(ARTIFACT_DIR, exist_ok=True)
    
    saved_paths = []
    timestamp = int(time.time())
    for i, bp in enumerate(collection_1.blueprints):
        filename = f"{scenario.scenario_id}_seq_blueprint_{timestamp}_{i+1}.json"
        filepath = os.path.join(ARTIFACT_DIR, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(bp.model_dump_json(indent=2))
        saved_paths.append(filepath)
        print(f"  [Saved] {filepath}")

    print("\n🧹 공유 브라우저 인스턴스를 종료합니다...")
    await shared_browser_instance.stop()

    # ────────────────────────────────────────────────────────
    # 2. Coder 실행 (Blueprint 기반 코딩 및 스크래핑)
    # ────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("🤖 Senior Coder Agent 기동 (웹 스크래핑 모드)")
    print("=" * 60)
    
    coder_agent = create_coder_agent()
    thread_id_coder = f"coder_test_{uuid.uuid4().hex[:8]}"
    coder_config = {"configurable": {"thread_id": thread_id_coder}}
    coder_context = SeniorCoderContext()

    if not saved_paths:
         print("❌ 저장된 Blueprint 파일이 없어 Coder를 실행할 수 없습니다.")
         return

    blueprint_path = saved_paths[0]
    with open(blueprint_path, "r", encoding="utf-8") as f:
        blueprint_content = f.read()

    print(f"📄 Blueprint 정보({blueprint_path}) 획득 완료. Coder에게 전달합니다...\n")

    mission_query = f"""
    다음은 Navigator 에이전트가 탐색하여 넘겨준 크롤링 설계도(Blueprint) JSON 입니다.

    [크롤링 Blueprint JSON]
    {blueprint_content}

    이걸 바탕으로 스크래핑 코드를 작성하고 실행하여 데이터를 수집해 주세요.
    **매우 중요**: 수집된 데이터는 반드시 다음 경로에 JSON 파일로 저장해야 합니다.
    저장 경로: {json_output_path}
    
    데이터 수집의 구체적인 목표는 다음 시나리오 문서와 같습니다.
    [시나리오 문서]
    {scenario.prompt}
    
    모든 작업이 완료되면 코드 내용과 얻어낸 결과를 최종 텍스트로 요약 분석하여 보고하세요.
    """
    
    messages = [HumanMessage(content=mission_query)]

    print("⏳ Coder 가동 중 (코드 작성 및 실행)... 수십 초가 소요될 수 있습니다.")
    final_messages_coder = []
    try:
        async for chunk_coder in coder_agent.astream(
            {"messages": messages},
            config=coder_config,
            context=coder_context
        ):
            for node_name, state_update in chunk_coder.items():
                if "messages" in state_update:
                    msgs = state_update["messages"]
                    if not isinstance(msgs, list):
                        msgs = [msgs]
                    for msg in msgs:
                        msg_type = getattr(msg, "type", type(msg).__name__)
                        content = getattr(msg, "content", str(msg))
                        if content:
                            msg_str = f"\n💻 [Coder -> {node_name}] ({msg_type}):\n{content}"
                            print(msg_str)
                            with open(log_output_path, "a", encoding="utf-8") as f:
                                f.write(msg_str + "\n\n")
                        elif hasattr(msg, "tool_calls") and msg.tool_calls:
                            msg_str = f"\n💻 [Coder -> {node_name}] ({msg_type}) Calling Tool: {msg.tool_calls[0]['name']}"
                            print(msg_str)
                            with open(log_output_path, "a", encoding="utf-8") as f:
                                f.write(msg_str + "\n\n")
                        final_messages_coder.append(msg)
    except Exception as e:
        err_msg = f"\n❌ Coder 실행 중 오류 발생: {e}"
        print(err_msg)
        with open(log_output_path, "a", encoding="utf-8") as f:
            f.write(err_msg + "\n\n")
        return
    
    parser = StrOutputParser()
    final_response = parser.invoke(final_messages_coder[-1]) if final_messages_coder else "No response"

    print("\n✅ 시나리오 에이전트(Sequential) 수행 완료! 평가(Evaluator) 단계로 넘어갑니다...")
    print("-" * 60)
    
    try:
        # Evaluator 실행
        eval_result = await evaluate_scenario_result(
            scenario=scenario,
            json_output_path=json_output_path,
            agent_code=final_response,
            agent_report=final_response
        )
        
        eval_report_text = f"""
\n📊 [평가 리포트]
통과 여부: {'🟢 PASS' if eval_result.is_pass else '🔴 FAIL'}
스키마 점수: {eval_result.schema_score} / 100
전략 점수: {eval_result.strategy_score} / 100
피드백:
{eval_result.feedback}
"""
        print(eval_report_text)
        print("=" * 80)
        with open(log_output_path, "a", encoding="utf-8") as f:
            f.write(eval_report_text + "\n")
    except Exception as e:
        err_msg = f"\n❌ 평가 중 오류 발생: {e}"
        print(err_msg)
        with open(log_output_path, "a", encoding="utf-8") as f:
            f.write(err_msg + "\n")

async def main():
    artifacts_dir = os.path.join(project_root, "artifacts", "scenarios")
    
    # 🎯 여기서 테스트할 시나리오 목록을 명시적으로 관리합니다.
    target_scenarios = [
        # ── Level 1 ──
        "quotes_01_pagination.md",
        # "quotes_02_tag_filter.md",
        # ── Level 2 ~ 2.5 ──
        # "ajax_01_playwright_wait.md",
        # "ajax_02_api_reverse_engineering.md",
        # ── Level 3 ──
        # "github_01_trending_scraping.md",       # 실제 동적 사이트 (GitHub)
        # "quotes_03_multi_step_crawling.md",     # 복합 크롤링 로직
        # ── Level 4 ~ 4.5 ──
        # "danawa_01_filter_search.md",           # AJAX + 필터 UI
        # "danawa_02_deep_table_parsing.md",      # 중첩 테이블 + 동적 버튼
        # ── Level 5 (최고 난이도) ──
        # "danawa_03_bulk_detail_crawling.md",    # 2단계 대량 수집
    ]
    
    scenario_files = []
    for filename in target_scenarios:
        filepath = os.path.join(artifacts_dir, filename)
        if os.path.exists(filepath):
            scenario_files.append(filepath)
        else:
            print(f"⚠️ 파일 없음 (건너뜀): {filepath}")
    
    if not scenario_files:
        print("❌ 실행할 시나리오 파일이 없습니다. target_scenarios 리스트를 확인하세요.")
        return
        
    print(f"총 {len(scenario_files)}개의 순차 워크플로우(Sequential) 시나리오 테스트를 시작합니다.")
    for file_path in scenario_files:
        print(f" - {os.path.basename(file_path)}")
        
    print("\n" + "="*40)
    
    for file_path in scenario_files:
        await run_scenario(file_path)
        
    print("\n🎉 모든 순차 워크플로우 시나리오 테스트 및 평가가 종료되었습니다.")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(main())

