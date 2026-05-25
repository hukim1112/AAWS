import os
import sys
import asyncio
import importlib
from glob import glob
from langchain_core.messages import HumanMessage

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

from app.scenario_parser import Scenario
from app.evaluator import evaluate_scenario_result

# 동적 로드를 통해 숫자로 시작하는 모듈 임포트
supervisor_mod = importlib.import_module("workflows.02_supervisor_workflow")
agent_executor = supervisor_mod.agent_executor

async def run_scenario(scenario_file: str):
    """지정된 시나리오 마크다운 파일을 파싱하여 슈퍼바이저 에이전트에 작업을 요청합니다."""
    scenario = Scenario.from_file(scenario_file)
    scenario_out_dir = os.path.join(project_root, "artifacts", "results", scenario.scenario_id)
    os.makedirs(scenario_out_dir, exist_ok=True)
    json_output_path = os.path.join(scenario_out_dir, "sup_result.json")
    log_output_path = os.path.join(scenario_out_dir, "sup_log.md")
    
    print("\n" + "=" * 80)
    print(f"🚀 [Supervisor] 시나리오 테스트 시작: {os.path.basename(scenario_file)}")
    print(f"📝 진행 상황은 터미널과 함께 다음 파일에도 저장됩니다: {log_output_path}")
    print("=" * 80)
    
    with open(log_output_path, "w", encoding="utf-8") as log_file:
        log_file.write(f"# 시나리오 실행 로그: {scenario.scenario_id}\n\n")

    mission_prompt = f"""
    아래에 제공된 마크다운 시나리오 문서를 읽고, 파이프라인(Navigator 및 Coder 등을 활용)을 사용해 수집 목표를 달성하세요. 
    1. Navigator를 통해 URL 탐색 및 Blueprint를 확보하세요.
    2. Coder에게 지시하여 스크래핑 코드를 작성하고 실행하세요.
    3. **매우 중요**: 수집된 데이터는 반드시 다음 경로에 JSON 파일로 저장해야 합니다.
       저장 경로: {json_output_path}
    4. 모든 작업이 완료되면 코드 내용과 얻어낸 결과를 최종 텍스트로 요약 분석하여 보고하세요.
    
    [대상 사이트 정보]
    - 사이트명: {scenario.site_name}
    - 기준 URL: {scenario.target_url}
    
    [시나리오 문서]
    {scenario.prompt}
    """

    import uuid
    thread_id = f"scenario_test_{uuid.uuid4().hex[:8]}"
    config = {"configurable": {"thread_id": thread_id}}
    
    print("⏳ 에이전트 수행 중 (상당한 시간이 소요될 수 있습니다)...")
    
    final_message = ""
    try:
        async for event in agent_executor.astream_events(
            {"messages": [HumanMessage(content=mission_prompt)]},
            config=config,
            version="v2"
        ):
            kind = event["event"]
            name = event["name"]
            
            if kind == "on_tool_start":
                tool_msg = f"\n🚀 [Tool Start: {name}] Input: {str(event['data'].get('input'))[:200]}...\n"
                print(tool_msg)
                with open(log_output_path, "a", encoding="utf-8") as f:
                    f.write(f"\n### 🛠️ Tool: `{name}`\n**Input:**\n```json\n{event['data'].get('input')}\n```\n\n")
                
            elif kind == "on_chat_model_stream":
                tags = event.get("tags", [])
                if "exclude_from_stream" in tags:
                    continue
                
                chunk = event["data"].get("chunk")
                if chunk and getattr(chunk, "content", None):
                    raw_content = chunk.content
                    if isinstance(raw_content, list):
                        content_str = "".join([c.get("text", "") if isinstance(c, dict) else str(c) for c in raw_content])
                    else:
                        content_str = str(raw_content)
                        
                    if content_str:
                        sys.stdout.write(content_str)
                        sys.stdout.flush()
                        with open(log_output_path, "a", encoding="utf-8") as f:
                            f.write(content_str)
                        
            elif kind == "on_chat_model_end":
                output = event["data"].get("output")
                if output and hasattr(output, "content"):
                    final_message = output.content
                    print()
                    with open(log_output_path, "a", encoding="utf-8") as f:
                        f.write("\n\n---\n")

        print("\n✅ 시나리오 에이전트 수행 완료! 평가(Evaluator) 단계로 넘어갑니다...")
        print("-" * 60)
        
        # Evaluator 실행
        eval_result = await evaluate_scenario_result(
            scenario=scenario,
            json_output_path=json_output_path,
            agent_code=final_message,  # Coder가 작성한 코드가 최종 보고서에 포함되어 있다고 가정
            agent_report=final_message
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
            f.write(eval_report_text)
        
    except Exception as e:
        print(f"\n❌ 시나리오 중 오류 발생: {e}")
        with open(log_output_path, "a", encoding="utf-8") as f:
            f.write(f"\n❌ 시나리오 중 오류 발생: {e}\n")

async def main():
    artifacts_dir = os.path.join(project_root, "artifacts", "scenarios")
    
    # 🎯 여기서 테스트할 시나리오 목록을 명시적으로 관리합니다.
    # 테스트할 시나리오만 주석 해제(Uncomment)하여 사용하세요.
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
        
    print(f"총 {len(scenario_files)}개의 시나리오 테스트를 시작합니다.")
    for file_path in scenario_files:
        print(f" - {os.path.basename(file_path)}")
        
    print("\n" + "="*40)
    
    for file_path in scenario_files:
        await run_scenario(file_path)
        
    print("\n🎉 모든 시나리오 테스트 및 평가가 종료되었습니다.")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(main())

