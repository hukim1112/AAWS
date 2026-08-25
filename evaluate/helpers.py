import os
import sys
import uuid
import json
import time
from typing import Any, Dict, List
from datetime import datetime
from langchain_core.messages import HumanMessage
from evaluate.scenario_parser import Scenario
from evaluate.evaluator import evaluate_scenario_result, EvaluationFeedback


class StructuredLogger:
    """시나리오 실행 중 발생하는 이벤트를 구조화된 JSON으로 기록합니다.
    
    기록 항목:
    - 도구 호출 시작/종료 (입력, 출력 원문 전체 Full Output, 소요시간)
    - LLM 응답 내용
    - 전체 실행 타임라인
    """
    
    def __init__(self, scenario_id: str, run_id: str):
        self.scenario_id = scenario_id
        self.run_id = run_id
        self.start_time = time.time()
        self.events = []
        self._pending_tools = {}
    
    def _timestamp(self) -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    
    def _elapsed_sec(self) -> float:
        return round(time.time() - self.start_time, 2)
    
    def log_llm_start(self, model_name: str = ""):
        self.events.append({
            "type": "llm_start",
            "timestamp": self._timestamp(),
            "elapsed_sec": self._elapsed_sec(),
            "model": model_name
        })
    
    def log_llm_chunk(self, content: str):
        if self.events and self.events[-1].get("type") == "llm_chunk":
            self.events[-1]["content"] += content
        else:
            self.events.append({
                "type": "llm_chunk",
                "timestamp": self._timestamp(),
                "elapsed_sec": self._elapsed_sec(),
                "content": content
            })
    
    def log_tool_start(self, tool_name: str, tool_input: Any, run_id: str = None):
        t_id = run_id or f"{tool_name}_{len(self.events)}"
        entry = {
            "type": "tool_start",
            "timestamp": self._timestamp(),
            "elapsed_sec": self._elapsed_sec(),
            "tool_name": tool_name,
            "tool_input": tool_input,
            "tool_run_id": t_id
        }
        self.events.append(entry)
        self._pending_tools[t_id] = time.time()
    
    def log_tool_end(self, tool_name: str, tool_output: Any, run_id: str = None):
        t_id = run_id or f"{tool_name}_{len(self.events)}"
        start_t = self._pending_tools.pop(t_id, None)
        duration = round(time.time() - start_t, 2) if start_t else None
        
        # tool_output 원문 전체를 직렬화 가능한 형태로 보존
        if hasattr(tool_output, "content"):
            clean_output = str(tool_output.content)
        else:
            clean_output = str(tool_output)
            
        entry = {
            "type": "tool_end",
            "timestamp": self._timestamp(),
            "elapsed_sec": self._elapsed_sec(),
            "tool_name": tool_name,
            "tool_output": clean_output,
            "duration_sec": duration,
            "tool_run_id": t_id
        }
        self.events.append(entry)
    
    def log_evaluation(self, eval_result: EvaluationFeedback):
        self.events.append({
            "type": "evaluation",
            "timestamp": self._timestamp(),
            "elapsed_sec": self._elapsed_sec(),
            "is_pass": eval_result.is_pass,
            "schema_score": eval_result.schema_score,
            "strategy_score": eval_result.strategy_score,
            "feedback": eval_result.feedback
        })
    
    def save(self, filepath: str):
        total_time = round(time.time() - self.start_time, 2)
        tool_counts = {}
        for ev in self.events:
            if ev.get("type") == "tool_start":
                tn = ev.get("tool_name", "unknown")
                tool_counts[tn] = tool_counts.get(tn, 0) + 1
                
        summary = {
            "scenario_id": self.scenario_id,
            "run_id": self.run_id,
            "total_elapsed_sec": total_time,
            "total_events": len(self.events),
            "tool_call_counts": tool_counts,
            "events": self.events
        }
        
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)


def setup_scenario_context(scenario_file: str, project_root: str, prefix: str = "scraper"):
    """시나리오 파일과 실행 환경 경로를 셋업합니다."""
    scenario = Scenario.from_file(scenario_file)
    run_id = f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    run_dir = os.path.join(project_root, "artifacts", "runs", run_id)
    os.makedirs(run_dir, exist_ok=True)
    
    json_path = os.path.join(run_dir, f"{scenario.scenario_id}_result.json")
    log_path = os.path.join(run_dir, f"{scenario.scenario_id}_run.log")
    structured_log_path = os.path.join(run_dir, f"{scenario.scenario_id}_structured.json")
    
    return scenario, {
        "run_id": run_id,
        "run_dir": run_dir,
        "json_path": json_path,
        "log_path": log_path,
        "structured_log_path": structured_log_path
    }


async def stream_agent_execution(
    agent_executor,
    mission_prompt: str,
    log_path: str,
    structured_log_path: str = None,
    scenario_id: str = "unknown",
    run_id: str = "unknown",
    recursion_limit: int = 100
) -> tuple[str, str]:
    """
    에이전트 astream_events를 실행하여 스트리밍 출력, 로그 파일 작성,
    작성된 파이썬 코드 및 최종 보고서를 추출하여 반환합니다.
    
    Returns:
        (final_report, extracted_code)
    """
    structured_logger = StructuredLogger(scenario_id, run_id) if structured_log_path else None
    
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    log_file = open(log_path, "w", encoding="utf-8")
    
    def log_write(text: str):
        print(text)
        log_file.write(text + "\n")
        log_file.flush()
        
    final_report = ""
    extracted_codes = []
    
    thread_id = str(uuid.uuid4())
    config = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": recursion_limit
    }
    
    try:
        async for event in agent_executor.astream_events(
            {"messages": [HumanMessage(content=mission_prompt)]},
            config=config,
            version="v2"
        ):
            event_type = event.get("event")
            name = event.get("name", "")
            run_item_id = event.get("run_id")
            
            if event_type == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk")
                if chunk and hasattr(chunk, "content") and isinstance(chunk.content, str):
                    print(chunk.content, end="", flush=True)
                    log_file.write(chunk.content)
                    log_file.flush()
                    final_report += chunk.content
                    if structured_logger:
                        structured_logger.log_llm_chunk(chunk.content)
                        
            elif event_type == "on_tool_start":
                tool_input = event.get("data", {}).get("input")
                # file_writer 코드 추출
                if name == "file_writer" and isinstance(tool_input, dict):
                    content = tool_input.get("content", "")
                    if content:
                        extracted_codes.append(content)
                        
                input_str = json.dumps(tool_input, ensure_ascii=False) if isinstance(tool_input, dict) else str(tool_input)
                log_write(f"\n\n🛠️ [도구 호출 시작] {name} | 입력: {input_str[:300]}")
                if structured_logger:
                    structured_logger.log_tool_start(name, tool_input, run_id=run_item_id)
                    
            elif event_type == "on_tool_end":
                tool_output = event.get("data", {}).get("output")
                out_str = str(tool_output)
                log_write(f"📦 [도구 결과 완료] {name} | 결과: {out_str[:300]}...\n")
                if structured_logger:
                    structured_logger.log_tool_end(name, tool_output, run_id=run_item_id)
                    
    except Exception as e:
        log_write(f"\n❌ 실행 중 예외 발생: {e}")
        import traceback
        traceback.print_exc()
    finally:
        log_file.close()
        if structured_logger and structured_log_path:
            structured_logger.save(structured_log_path)
            
    best_code = extracted_codes[-1] if extracted_codes else ""
    return final_report, best_code


async def evaluate_and_log(
    scenario: Scenario,
    json_path: str,
    final_report: str,
    agent_code: str,
    log_path: str,
    structured_log_path: str = None
) -> EvaluationFeedback:
    """결과물을 평가하고 마크다운 로그 및 구조화 로그에 기록합니다."""
    feedback = await evaluate_scenario_result(
        scenario=scenario,
        json_output_path=json_path,
        agent_code=agent_code,
        agent_report=final_report
    )
    
    report_md = f"""

{'=' * 80}
🏆 [Evaluator 채점 결과 리포트]
{'=' * 80}
- 시나리오 ID: {scenario.scenario_id} ({scenario.difficulty})
- 최종 판정: {'✅ PASS' if feedback.is_pass else '❌ FAIL'}
- 스키마 준수 점수: {feedback.schema_score} / 100
- 전략 준수 점수: {feedback.strategy_score} / 100
- 상세 피드백:
{feedback.feedback}
{'=' * 80}
"""
    print(report_md)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(report_md + "\n")
        
    if structured_log_path and os.path.exists(structured_log_path):
        try:
            with open(structured_log_path, "r", encoding="utf-8") as f:
                s_data = json.load(f)
            s_data["evaluation"] = {
                "is_pass": feedback.is_pass,
                "schema_score": feedback.schema_score,
                "strategy_score": feedback.strategy_score,
                "feedback": feedback.feedback
            }
            with open(structured_log_path, "w", encoding="utf-8") as f:
                json.dump(s_data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
            
    return feedback
