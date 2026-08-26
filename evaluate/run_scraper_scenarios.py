import os
import sys
import asyncio
from dotenv import load_dotenv

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

load_dotenv(override=True)

from evaluate.config_loader import load_target_scenarios
from evaluate.helpers import (
    setup_scenario_context,
    stream_agent_execution,
    evaluate_and_log
)
from app.agents.scraper import create_agent_executor


async def run_scenario(scenario_file: str) -> dict:
    """단일 시나리오를 Scraper 에이전트로 실행하고 평가합니다."""
    scenario, paths = setup_scenario_context(scenario_file, project_root, prefix="scraper")
    
    print("\n" + "=" * 80)
    print(f"🚀 [Scraper Scenario Test] 시작: {os.path.basename(scenario_file)}")
    print(f"🎯 대상 사이트: {scenario.site_name} ({scenario.target_url})")
    print(f"📊 난이도: {scenario.difficulty}")
    print(f"📂 실행 디렉토리: {paths['run_dir']}")
    print(f"📝 Markdown 로그: {paths['log_path']}")
    print(f"📋 구조화 로그: {paths['structured_log_path']}")
    print(f"💾 결과 JSON 목표: {paths['json_path']}")
    print("=" * 80)
    
    scraper_agent = await create_agent_executor()
    
    mission_prompt = f"""
다음 마크다운 시나리오의 요구사항을 분석하고, 필요한 네비게이팅 도구를 활용하여 완벽한 데이터 수집 코드를 작성/실행한 뒤 결과를 저장하세요.

[대상 사이트 정보]
- 사이트명: {scenario.site_name}
- 기준 URL: {scenario.target_url}

[시나리오 요구사항]
{scenario.prompt}

[⚠️ 매우 중요 준수사항]
1. 사이트의 DOM 구조를 파악(extract_dom_skeleton, get_page_section 등)하고 셀렉터를 검증(verify_selectors)하세요.
2. 이번 평가 실행에서 생성하는 모든 파일(추출 계획서, 스크래핑 코드, 로그 등)은 **반드시** 다음 실행 디렉토리 내에 저장하세요:
   - 실행 디렉토리: {paths['run_dir']}
   - 추출 계획서: {paths['run_dir']}/extraction_plan.json
   - 스크래핑 코드: {paths['run_dir']}/scraper.py (또는 {paths['run_dir']}/scrape_{scenario.scenario_id}.py)
3. 수집된 최종 데이터는 **반드시** 다음 경로에 JSON 파일로 저장해야 합니다:
   저장 경로: {paths['json_path']}
4. 저장이 완료되면 수집된 건수와 샘플을 확인하고 최종 완료 보고를 작성하세요.
"""

    print("\n⏳ Scraper 에이전트 수행 중...\n")
    
    try:
        final_report, agent_code = await stream_agent_execution(
            agent_executor=scraper_agent,
            mission_prompt=mission_prompt,
            log_path=paths['log_path'],
            structured_log_path=paths['structured_log_path'],
            scenario_id=scenario.scenario_id,
            run_id=paths['run_id'],
            recursion_limit=100
        )
        
        # 평가 및 채점
        feedback = await evaluate_and_log(
            scenario=scenario,
            json_path=paths['json_path'],
            final_report=final_report,
            agent_code=agent_code,
            log_path=paths['log_path'],
            structured_log_path=paths['structured_log_path']
        )
    finally:
        # SQLite 체크포인터 워커 스레드 정리 (종료 블로킹 방지)
        if hasattr(scraper_agent, "checkpointer") and hasattr(scraper_agent.checkpointer, "conn"):
            try:
                await scraper_agent.checkpointer.conn.close()
            except Exception:
                pass
    
    return {
        "scenario_id": scenario.scenario_id,
        "difficulty": scenario.difficulty,
        "is_pass": feedback.is_pass,
        "schema_score": feedback.schema_score,
        "strategy_score": feedback.strategy_score,
        "feedback": feedback.feedback,
        "run_dir": paths['run_dir']
    }


async def main():
    artifacts_dir = os.path.join(project_root, "artifacts", "scenarios")
    target_scenarios = load_target_scenarios(project_root)
    
    scenario_files = []
    for filename in target_scenarios:
        filepath = os.path.join(artifacts_dir, filename)
        if os.path.exists(filepath):
            scenario_files.append(filepath)
        else:
            print(f"⚠️ 시나리오 파일 없음 (건너뜀): {filepath}")
            
    if not scenario_files:
        print("❌ 실행할 시나리오 파일이 없습니다. evaluate/evaluate_config.yaml 설정을 확인하세요.")
        return
        
    print(f"\n총 {len(scenario_files)}개의 시나리오 테스트 및 평가를 시작합니다.")
    
    results = []
    try:
        for i, file in enumerate(scenario_files, 1):
            print(f"\n\n{'#' * 80}")
            print(f"📌 [진행률: {i}/{len(scenario_files)}] {os.path.basename(file)}")
            print(f"{'#' * 80}")
            
            res = await run_scenario(file)
            results.append(res)
    finally:
        from app.tools.navigator import PlaywrightManager
        if PlaywrightManager._instance:
            await PlaywrightManager._instance.close()
            print("\n🛑 [PlaywrightManager] 브라우저 및 CDP 리소스 정리 완료")
        
    # 종합 결과 성적표 출력
    print("\n\n" + "=" * 90)
    print("📊 [전체 시나리오 자동 평가 종합 성적표 (Evaluation Scoreboard)]")
    print("=" * 90)
    
    header = f"{'시나리오 ID':<35} | {'난이도':<10} | {'결과':<8} | {'스키마':<8} | {'전략':<8}"
    print(header)
    print("-" * 90)
    
    pass_count = 0
    total_schema = 0
    total_strategy = 0
    
    for r in results:
        status_str = "✅ PASS" if r['is_pass'] else "❌ FAIL"
        if r['is_pass']:
            pass_count += 1
        total_schema += r['schema_score']
        total_strategy += r['strategy_score']
        print(f"{r['scenario_id']:<35} | {r['difficulty']:<10} | {status_str:<8} | {r['schema_score']:<8} | {r['strategy_score']:<8}")
        
    n = len(results)
    avg_schema = round(total_schema / n, 1) if n > 0 else 0
    avg_strategy = round(total_strategy / n, 1) if n > 0 else 0
    
    print("=" * 90)
    print(f"🎯 최종 결과: {pass_count}/{n} 통과 ({round(pass_count/n*100, 1)}%) | 평균 스키마 점수: {avg_schema}점 | 평균 전략 점수: {avg_strategy}점")
    print("=" * 90)


if __name__ == "__main__":
    asyncio.run(main())
