import os
import sys
import uuid
from langchain_core.messages import HumanMessage
from app.scenario_parser import Scenario
from app.evaluator import evaluate_scenario_result

def setup_scenario_context(scenario_file: str, project_root: str, prefix: str):
    """
    시나리오 파일 및 결과/로그 출력 경로를 초기화합니다.
    """
    scenario = Scenario.from_file(scenario_file)
    scenario_out_dir = os.path.join(project_root, "artifacts", "results", scenario.scenario_id)
    os.makedirs(scenario_out_dir, exist_ok=True)
    
    json_output_path = os.path.join(scenario_out_dir, f"{prefix}_result.json")
    log_output_path = os.path.join(scenario_out_dir, f"{prefix}_log.md")
    
    with open(log_output_path, "w", encoding="utf-8") as log_file:
        log_file.write(f"# 시나리오 실행 로그 ({prefix}): {scenario.scenario_id}\n\n")
        
    return scenario, {
        "out_dir": scenario_out_dir,
        "json_path": json_output_path,
        "log_path": log_output_path
    }

async def stream_agent_execution(agent, mission_prompt: str, log_output_path: str) -> str:
    """
    LangChain 에이전트의 astream_events를 수신하여 터미널 및 로그 파일에 스트리밍 출력하고
    최종 메시지(final_message)를 반환합니다.
    """
    thread_id = f"scenario_test_{uuid.uuid4().hex[:8]}"
    config = {"configurable": {"thread_id": thread_id}}
    final_message = ""

    async for event in agent.astream_events(
        {"messages": [HumanMessage(content=mission_prompt)]},
        config=config,
        version="v2"
    ):
        kind = event["event"]
        name = event["name"]
        
        if kind == "on_tool_start":
            tool_input = str(event['data'].get('input'))
            tool_msg = f"\n🚀 [Tool Start: {name}] Input: {tool_input[:200]}...\n"
            print(tool_msg)
            with open(log_output_path, "a", encoding="utf-8") as f:
                f.write(f"\n### 🛠️ Tool: `{name}`\n**Input:**\n```json\n{tool_input}\n```\n\n")
            
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

    return final_message

async def evaluate_and_log(scenario: Scenario, json_output_path: str, final_message: str, log_output_path: str):
    """
    Evaluator를 실행하여 수집 결과 및 에이전트 리포트를 평가하고 결과를 터미널과 로그에 출력합니다.
    """
    print("\n✅ 시나리오 에이전트 수행 완료! 평가(Evaluator) 단계로 넘어갑니다...")
    print("-" * 60)
    
    eval_result = await evaluate_scenario_result(
        scenario=scenario,
        json_output_path=json_output_path,
        agent_code=final_message,
        agent_report=final_message
    )
    
    eval_report_text = f"""
📊 [평가 리포트]
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
