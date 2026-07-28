import os
import sys
import uuid
import json
import time
import logging
from datetime import datetime
from langchain_core.messages import HumanMessage
from app.scenario_parser import Scenario
from app.evaluator import evaluate_scenario_result


# ═══════════════════════════════════════════════════════════
# 구조화된 로그를 위한 StructuredLogger 클래스
# ═══════════════════════════════════════════════════════════

class StructuredLogger:
    """시나리오 실행 중 발생하는 이벤트를 구조화된 JSON으로 기록합니다.
    
    기록 항목:
    - 도구 호출 시작/종료 (입력, 출력, 소요시간)
    - 에이전트 식별 (Supervisor/Navigator/Coder)
    - LLM 응답 내용
    - 전체 실행 타임라인
    """
    
    def __init__(self, scenario_id: str, run_id: str):
        self.scenario_id = scenario_id
        self.run_id = run_id
        self.start_time = time.time()
        self.events = []
        self._pending_tools = {}  # tool_run_id → start_event (소요시간 계산용)
    
    def _timestamp(self) -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    
    def _elapsed_sec(self) -> float:
        return round(time.time() - self.start_time, 2)
    
    def _identify_agent(self, event: dict) -> str:
        """이벤트의 tags, metadata, name 등에서 에이전트 계층을 식별합니다."""
        tags = event.get("tags", [])
        name = event.get("name", "")
        metadata = event.get("metadata", {})
        
        # tags에서 에이전트 식별
        tag_str = " ".join(tags).lower()
        if "supervisor" in tag_str:
            return "Supervisor"
        if "navigator" in tag_str:
            return "Navigator"
        if "coder" in tag_str:
            return "Coder"
        
        # name에서 에이전트 식별
        name_lower = name.lower()
        if "supervisor" in name_lower:
            return "Supervisor"
        if "navigator" in name_lower or "nav" in name_lower:
            return "Navigator"
        if "coder" in name_lower:
            return "Coder"
        
        # 도구 이름으로 에이전트 추론
        tool_to_agent = {
            "chat_to_navigator": "Supervisor",
            "chat_to_coder": "Supervisor",
            "read_image_and_analyze": "Supervisor",
            "web_search_custom_tool": "Supervisor",
            "get_page_structure": "Navigator",
            "extract_dom_skeleton": "Navigator",
            "verify_selectors_with_samples": "Navigator",
            "browse_web": "Navigator",
            "read_code_file": "Coder",
            "edit_code_file": "Coder",
            "create_new_file": "Coder",
            "write_text_file": "Coder",
            "run_python_script": "Coder",
            "validate_collected_data": "Coder",
            "glob_search": "Coder",
            "ripgrep_search": "Coder",
        }
        if name in tool_to_agent:
            return tool_to_agent[name]
        
        # langgraph_name 메타데이터에서 추론
        lg_name = metadata.get("langgraph_name", "")
        if lg_name:
            if "supervisor" in lg_name.lower():
                return "Supervisor"
            if "navigator" in lg_name.lower():
                return "Navigator"
            if "coder" in lg_name.lower():
                return "Coder"
        
        return "Unknown"
    
    def _truncate(self, text: str, max_len: int = 500) -> str:
        """텍스트가 max_len을 초과하면 잘라냅니다."""
        if not isinstance(text, str):
            text = str(text)
        if len(text) <= max_len:
            return text
        return text[:max_len] + f"... (총 {len(text)}자 중 {max_len}자 표시)"
    
    def log_tool_start(self, event: dict):
        """도구 호출 시작을 기록합니다."""
        run_id = event.get("run_id", "")
        tool_input = event["data"].get("input", {})
        tool_input_str = str(tool_input)
        
        entry = {
            "type": "tool_start",
            "agent": self._identify_agent(event),
            "tool": event["name"],
            "input_summary": self._truncate(tool_input_str),
            "input_full": tool_input_str if len(tool_input_str) <= 2000 else self._truncate(tool_input_str, 2000),
            "timestamp": self._timestamp(),
            "elapsed_sec": self._elapsed_sec(),
        }
        self.events.append(entry)
        self._pending_tools[run_id] = time.time()
    
    def log_tool_end(self, event: dict):
        """도구 호출 종료를 기록합니다."""
        run_id = event.get("run_id", "")
        output = event["data"].get("output", "")
        output_str = str(output)
        
        # 소요시간 계산
        start_time = self._pending_tools.pop(run_id, None)
        duration = round(time.time() - start_time, 2) if start_time else None
        
        entry = {
            "type": "tool_end",
            "agent": self._identify_agent(event),
            "tool": event["name"],
            "output_summary": self._truncate(output_str),
            "output_length": len(output_str),
            "duration_sec": duration,
            "timestamp": self._timestamp(),
            "elapsed_sec": self._elapsed_sec(),
        }
        self.events.append(entry)
    
    def log_llm_response(self, event: dict, content: str):
        """LLM 최종 응답을 기록합니다."""
        entry = {
            "type": "llm_response",
            "agent": self._identify_agent(event),
            "model": event.get("name", ""),
            "content_summary": self._truncate(content, 300),
            "content_length": len(content),
            "timestamp": self._timestamp(),
            "elapsed_sec": self._elapsed_sec(),
        }
        self.events.append(entry)
    
    def finalize(self) -> dict:
        """최종 구조화 로그를 반환합니다."""
        total_duration = round(time.time() - self.start_time, 2)
        
        # 요약 통계 계산
        tool_starts = [e for e in self.events if e["type"] == "tool_start"]
        tool_ends = [e for e in self.events if e["type"] == "tool_end"]
        
        # 에이전트별 도구 호출 횟수
        agent_tool_counts = {}
        for e in tool_starts:
            agent = e["agent"]
            agent_tool_counts[agent] = agent_tool_counts.get(agent, 0) + 1
        
        # 도구별 평균 소요시간
        tool_durations = {}
        for e in tool_ends:
            tool = e["tool"]
            if e["duration_sec"] is not None:
                if tool not in tool_durations:
                    tool_durations[tool] = []
                tool_durations[tool].append(e["duration_sec"])
        
        tool_avg_durations = {
            tool: round(sum(durs) / len(durs), 2) 
            for tool, durs in tool_durations.items()
        }
        
        return {
            "scenario_id": self.scenario_id,
            "run_id": self.run_id,
            "start_time": datetime.fromtimestamp(self.start_time).strftime("%Y-%m-%d %H:%M:%S"),
            "total_duration_sec": total_duration,
            "summary": {
                "total_tool_calls": len(tool_starts),
                "agent_tool_counts": agent_tool_counts,
                "tool_avg_duration_sec": tool_avg_durations,
                "total_llm_responses": len([e for e in self.events if e["type"] == "llm_response"]),
            },
            "events": self.events,
        }
    
    def save(self, filepath: str):
        """구조화 로그를 JSON 파일로 저장합니다."""
        data = self.finalize()
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"📋 구조화 로그 저장: {filepath}")


# ═══════════════════════════════════════════════════════════
# 기존 헬퍼 함수 (개선 버전)
# ═══════════════════════════════════════════════════════════

def setup_scenario_context(scenario_file: str, project_root: str, prefix: str):
    """
    시나리오 파일 및 결과/로그 출력 경로를 초기화합니다.
    모든 산출물은 runs/{run_id}/ 하위에 저장되어 실행별로 독립 보관됩니다.
    """
    scenario = Scenario.from_file(scenario_file)
    scenario_out_dir = os.path.join(project_root, "artifacts", "results", scenario.scenario_id)
    
    # run_id: 타임스탬프 기반 (정렬/식별 가능)
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 모든 결과물을 runs/{run_id}/ 하위에 저장
    run_dir = os.path.join(scenario_out_dir, "runs", run_id)
    os.makedirs(run_dir, exist_ok=True)
    
    json_output_path = os.path.join(run_dir, f"{prefix}_result.json")
    log_output_path = os.path.join(run_dir, f"{prefix}_log.md")
    structured_log_path = os.path.join(run_dir, f"{prefix}_structured_log.json")
    
    # Markdown 로그 초기화
    with open(log_output_path, "w", encoding="utf-8") as log_file:
        log_file.write(f"# 시나리오 실행 로그 ({prefix}): {scenario.scenario_id}\n")
        log_file.write(f"**Run ID**: `{run_id}`\n")
        log_file.write(f"**시작 시간**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
    return scenario, {
        "out_dir": scenario_out_dir,
        "run_dir": run_dir,
        "json_path": json_output_path,
        "log_path": log_output_path,
        "structured_log_path": structured_log_path,
        "run_id": run_id,
    }


async def stream_agent_execution(agent, mission_prompt: str, log_output_path: str, 
                                  structured_log_path: str = None, 
                                  scenario_id: str = "", run_id: str = "",
                                  recursion_limit: int = 100) -> str:
    """
    LangChain 에이전트의 astream_events를 수신하여 터미널 및 로그 파일에 스트리밍 출력하고
    최종 메시지(final_message)를 반환합니다.
    
    개선 사항 (v2):
    - on_tool_end 이벤트 캡처: 도구 반환 결과를 로그에 기록
    - 에이전트 계층 태깅: [Supervisor], [Navigator], [Coder] 식별
    - 타이밍 정보: 도구별 소요시간, 전체 실행시간
    - 구조화된 JSON 로그: 프로그래매틱 분석 및 버전 비교 가능
    """
    thread_id = f"scenario_test_{uuid.uuid4().hex[:8]}"
    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": recursion_limit}
    final_message = ""
    
    # 구조화 로거 초기화
    logger = StructuredLogger(scenario_id=scenario_id, run_id=run_id)
    
    # browser-use 에이전트의 터미널 출력을 로그 파일에도 기록
    bu_logger = logging.getLogger("browser_use")
    bu_file_handler = logging.FileHandler(log_output_path, mode="a", encoding="utf-8")
    bu_file_handler.setFormatter(logging.Formatter(
        "\n> 🌐 [browser-use] %(message)s"
    ))
    bu_file_handler.setLevel(logging.INFO)
    bu_logger.addHandler(bu_file_handler)
    
    execution_start = time.time()

    try:
        async for event in agent.astream_events(
            {"messages": [HumanMessage(content=mission_prompt)]},
            config=config,
            version="v2"
        ):
            kind = event["event"]
            name = event["name"]
            agent_tag = logger._identify_agent(event)
            
            # ── 도구 호출 시작 ──
            if kind == "on_tool_start":
                tool_input = str(event['data'].get('input'))
                tool_msg = f"\n🚀 [{agent_tag}] Tool Start: {name} | Input: {tool_input[:200]}...\n"
                print(tool_msg)
                with open(log_output_path, "a", encoding="utf-8") as f:
                    f.write(f"\n### 🛠️ [{agent_tag}] Tool: `{name}`\n")
                    f.write(f"**Input:**\n```json\n{tool_input[:1000]}\n```\n\n")
                
                logger.log_tool_start(event)
            
            # ── 도구 호출 종료 ──
            elif kind == "on_tool_end":
                output = event["data"].get("output", "")
                output_str = str(output)
                
                # 터미널 출력 (간결하게)
                output_preview = output_str[:300].replace('\n', ' ')
                print(f"  ✅ [{agent_tag}] Tool End: {name} | Output: {output_preview}...")
                
                # Markdown 로그에 도구 결과 기록
                with open(log_output_path, "a", encoding="utf-8") as f:
                    truncated = output_str[:1500] if len(output_str) > 1500 else output_str
                    f.write(f"**Output** ({len(output_str)}자):\n```\n{truncated}\n```\n\n")
                
                logger.log_tool_end(event)
                
            # ── LLM 스트리밍 ──
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
                    
            # ── LLM 응답 완료 ──
            elif kind == "on_chat_model_end":
                output = event["data"].get("output")
                if output and hasattr(output, "content"):
                    content = output.content
                    if isinstance(content, list):
                        content = "".join([c.get("text", "") if isinstance(c, dict) else str(c) for c in content])
                    final_message = content
                    print()
                    with open(log_output_path, "a", encoding="utf-8") as f:
                        f.write("\n\n---\n")
                    
                    logger.log_llm_response(event, str(content))

    except Exception as e:
        # 에러 정보를 로그에 기록
        error_msg = f"\n❌ 스트리밍 중 오류 발생: {type(e).__name__}: {e}\n"
        print(error_msg)
        with open(log_output_path, "a", encoding="utf-8") as f:
            f.write(error_msg)

    finally:
        # browser-use 로거 핸들러 해제
        bu_logger.removeHandler(bu_file_handler)
        bu_file_handler.close()
        
        # 전체 실행 시간 기록 (정상/에러 모두)
        total_duration = round(time.time() - execution_start, 2)
        duration_msg = f"\n⏱️ 전체 실행 시간: {total_duration}초\n"
        print(duration_msg)
        with open(log_output_path, "a", encoding="utf-8") as f:
            f.write(duration_msg)
        
        # 구조화 로그 저장 (에러 시에도 그 시점까지의 데이터 보존)
        if structured_log_path:
            logger.save(structured_log_path)
    
    return final_message


async def evaluate_and_log(scenario: Scenario, json_output_path: str, final_message: str, log_output_path: str):
    """
    Evaluator를 실행하여 수집 결과 및 에이전트 리포트를 평가하고 결과를 터미널과 로그에 출력합니다.
    
    개선 사항 (v2):
    - artifacts/code/ 디렉토리에서 실제 코드 파일을 읽어 agent_code로 전달
    """
    print("\n✅ 시나리오 에이전트 수행 완료! 평가(Evaluator) 단계로 넘어갑니다...")
    print("-" * 60)
    
    # 실제 코드 파일 탐색 (artifacts/code/ 내 최신 .py 파일)
    agent_code = final_message  # 기본값: 기존과 동일
    code_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "artifacts", "code")
    if os.path.exists(code_dir):
        py_files = [f for f in os.listdir(code_dir) if f.endswith('.py')]
        if py_files:
            # 가장 최근 수정된 파일 선택
            py_files_with_time = [
                (f, os.path.getmtime(os.path.join(code_dir, f))) 
                for f in py_files
            ]
            latest_file = max(py_files_with_time, key=lambda x: x[1])[0]
            try:
                with open(os.path.join(code_dir, latest_file), "r", encoding="utf-8") as f:
                    agent_code = f.read()
                print(f"📄 평가에 사용할 코드 파일: {latest_file}")
            except Exception as e:
                print(f"⚠️ 코드 파일 읽기 실패 ({latest_file}): {e}")
    
    eval_result = await evaluate_scenario_result(
        scenario=scenario,
        json_output_path=json_output_path,
        agent_code=agent_code,
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
