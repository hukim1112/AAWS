import os
import sys
import asyncio
from dotenv import load_dotenv

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

from tests.config_loader import load_target_scenarios
from tests.test_helpers import (
    setup_scenario_context,
    stream_agent_execution,
    evaluate_and_log
)
from app.agents import create_navigator_agent, create_coder_agent
from app.schemas import NavigatorContext, SeniorCoderContext, NavigatorBlueprintCollection
from app.tools import ARTIFACT_DIR
from browser_use import Browser

async def run_scenario(scenario_file: str):
    """지정된 시나리오 마크다운 파일을 파싱하여 Sequential 파이프라인(Navigator -> Coder)으로 작업을 수행합니다."""
    scenario, paths = setup_scenario_context(scenario_file, project_root, prefix="seq")
    
    print("\n" + "=" * 80)
    print(f"🚀 [Sequential] 시나리오 테스트 시작: {os.path.basename(scenario_file)}")
    print(f"📂 실행 디렉토리: {paths['run_dir']}")
    print(f"📝 Markdown 로그: {paths['log_path']}")
    print(f"📋 구조화 로그: {paths['structured_log_path']}")
    print("=" * 80)

    # 1. Navigator 실행 (Blueprint 생성)
    print("=" * 60)
    print("🧪 Navigator Agent 기동 (Blueprint 생성)")
    print("=" * 60)

    navigator_agent = create_navigator_agent()
    shared_browser_instance = Browser(headless=False, disable_security=True, keep_alive=True)
    nav_prompt = f"""
    아래에 제공된 마크다운 시나리오 문서를 읽고, 데이터 수집을 위한 완벽한 Blueprint를 작성해 주세요.
    텍스트와 링크(URL)의 셀렉터 속성이 명확히 분리된 완벽한 Blueprint를 설계하는 것이 목표입니다.
    
    [대상 사이트 정보]
    - 사이트명: {scenario.site_name}
    - 기준 URL: {scenario.target_url}
    
    [시나리오 문서]
    {scenario.prompt}
    """

    try:
        final_nav_msg = await stream_agent_execution(
            navigator_agent, nav_prompt, paths['log_path'],
            structured_log_path=paths['structured_log_path'],
            scenario_id=scenario.scenario_id,
            run_id=paths['run_id']
        )
    finally:
        await shared_browser_instance.stop()

    # 2. Coder 실행 (Blueprint 기반 코딩 및 스크래핑)
    print("\n" + "=" * 60)
    print("🤖 Senior Coder Agent 기동 (웹 스크래핑 모드)")
    print("=" * 60)

    coder_agent = create_coder_agent()
    coder_prompt = f"""
    아래 시나리오 목표를 달성하기 위한 파이프라인 수집 코드를 작성하고 실행해주세요.
    **매우 중요**: 수집된 데이터는 반드시 다음 경로에 JSON 파일로 저장해야 합니다.
    저장 경로: {paths['json_path']}
    
    [시나리오 문서]
    {scenario.prompt}
    """

    print("⏳ Coder 가동 중 (코드 작성 및 실행)... 수십 초가 소요될 수 있습니다.")
    try:
        final_coder_msg = await stream_agent_execution(
            coder_agent, coder_prompt, paths['log_path'],
            structured_log_path=paths['structured_log_path'],
            scenario_id=scenario.scenario_id,
            run_id=paths['run_id']
        )
        
        # 3. Evaluator 평가 및 채점
        await evaluate_and_log(
            scenario, paths['json_path'], final_coder_msg, paths['log_path']
        )
    except Exception as e:
        print(f"\n❌ Coder 실행 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        with open(paths['log_path'], "a", encoding="utf-8") as f:
            f.write(f"\n❌ Coder 실행 중 오류 발생: {e}\n")

async def main():
    artifacts_dir = os.path.join(project_root, "artifacts", "scenarios")
    target_scenarios = load_target_scenarios(project_root)
    
    scenario_files = []
    for filename in target_scenarios:
        filepath = os.path.join(artifacts_dir, filename)
        if os.path.exists(filepath):
            scenario_files.append(filepath)
        else:
            print(f"⚠️ 파일 없음 (건너뜀): {filepath}")
    
    if not scenario_files:
        print("❌ 실행할 시나리오 파일이 없습니다. tests/test_config.yaml 설정을 확인하세요.")
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
