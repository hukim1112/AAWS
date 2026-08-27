# Sub-Agent 설계 패턴 — 핵심 교훈

> **대상 독자**: AAWS(Agent-As-a-Worker-Service) 교육 수강생  
> **관련 파일**: `app/tools/supervisor_tools.py`, `app/agents/supervisor.py`, `app/prompts/SUPERVISOR.py`, `app/client.py`

---

## 목차

1. [Sub-Agent 패턴이 필요한 이유 — Dynamic Context Pruning](#1-sub-agent-패턴이-필요한-이유--dynamic-context-pruning)
2. [정보 비대칭 문제와 Blackboard 패턴](#2-정보-비대칭-문제와-blackboard-패턴)
3. [Sub-Agent Protocol Overlay — 역할 전환 기법](#3-sub-agent-protocol-overlay--역할-전환-기법)
4. [Thread ID 설계 — 세션 연속성과 독립성의 균형](#4-thread-id-설계--세션-연속성과-독립성의-균형)
5. [에이전트 팩토리 vs 서버 클라이언트 호출 — 아키텍처 선택](#5-에이전트-팩토리-vs-서버-클라이언트-호출--아키텍처-선택)
6. [시스템 프롬프트 vs 도구 Docstring — 책임 분리 원칙](#6-시스템-프롬프트-vs-도구-docstring--책임-분리-원칙)
7. [Self-Healing — Backtracking 설계](#7-self-healing--backtracking-설계)
8. [부록: 실험 결과 Walkthrough](#부록-실험-결과-walkthrough)

---

## 1. Sub-Agent 패턴이 필요한 이유 — Dynamic Context Pruning

### 왜 Supervisor의 대화 이력을 Sub-agent에게 넘기지 않는가?

Supervisor가 10번의 대화를 거친 뒤 Scraper를 호출할 때, 부모의 전체 메시지 히스토리를 그대로 전달하면 다음 문제가 발생합니다:

- **컨텍스트 오염**: 사용자와의 잡담, 이전 작업의 결과 등 관련 없는 맥락이 Sub-agent의 집중도를 저하시킴
- **토큰 비용 폭발**: 호출 횟수가 늘수록 컨텍스트 길이가 선형적으로 증가
- **응답 오염**: Sub-agent의 상세 응답이 Supervisor 히스토리에 그대로 누적되어 Supervisor의 추론 능력 저하

이 문제를 막기 위해 **Dynamic Context Pruning** — 즉, Supervisor의 대화 이력을 전달하지 않고 압축된 지시문만 주입하는 방식을 채택합니다:

```
# ❌ 잘못된 방식 — 전체 대화 이력 전달
worker.invoke({"messages": supervisor_full_history + [HumanMessage(task)]})

# ✅ 올바른 방식 — 압축된 지시문만 주입
worker.invoke({"messages": [HumanMessage(compressed_3layer_message)]})
```

그리고 Sub-agent의 응답도 **5줄 포인터**로 제한하여 Supervisor 히스토리의 오염을 최소화합니다:

```
Supervisor → [압축된 3-Layer 지시문] → Scraper
                                           ↓
Supervisor ← [5줄 TASK REPORT 포인터] ← Scraper
```

`[TASK REPORT]` 포맷의 실제 예시:

```
[TASK REPORT]
- Status: SUCCESS
- Target Files: artifacts/data/quotes_supervisor_test.json
- Artifacts Created: artifacts/data/quotes_supervisor_test.json
- Summary: 10건의 명언(text, author, tags) 수집 완료. Einstein, Rowling 등 포함.
- Issues: None
```

상세 데이터는 `artifacts/` 파일에 보존되므로, Supervisor는 필요 시 `file_read`로 검증할 수 있습니다.

> **핵심 교훈**: Sub-agent에게는 부모 대화 이력을 전달하지 않는다. 압축된 지시문만 주입하고, 결과는 "파일 포인터(TASK REPORT)"로만 반환받아라. 이것이 컨텍스트 오염을 막는 핵심 설계 결정이다.

---

## 2. 정보 비대칭 문제와 Blackboard 패턴

### Dynamic Context Pruning의 부작용: 정보 비대칭

1장의 설계 — 맥락을 의도적으로 단절 — 은 컨텍스트 오염을 막지만, 동시에 새로운 문제를 만들어냅니다:

```
👑 Supervisor
  → Sub-agent 내부에서 무슨 일이 벌어지는지 모름
  → Sub-agent가 어디까지 진행했는지 모름

🔧 Scraper (Sub-agent)
  → Supervisor가 전체 계획에서 어떤 위치에 있는지 모름
  → 다른 Sub-agent가 무슨 작업을 했는지 모름
```

이 **정보 비대칭**이 누적되면 Supervisor는 전체 파이프라인의 진행 상태를 파악할 수 없게 됩니다.

### 해법: Blackboard 패턴 — 공유 저장소

맥락을 직접 전달하는 대신, **공유 저장소(Blackboard)**를 통해 간접적으로 정보를 동기화합니다:

| 구성 요소 | 역할 | 해소하는 비대칭 |
|:---|:---|:---|
| `Task Board` (`task_state.json`) | 계획 + 진행 상태를 디스크에 기록 | Supervisor가 전체 진행도를 추적 |
| `artifacts/` 디렉토리 | 산출물을 파일로 영구 보존 | 이후 Sub-agent가 이전 결과를 파일로 조회 가능 |
| `[TASK REPORT]` 프로토콜 | Worker → Supervisor 5줄 요약 반환 | Supervisor가 핵심 결과만 히스토리에 기록 |

```
👑 Supervisor
  enter_plan()          # Blackboard에 계획 수립
  task_create()         # 태스크 등록
  invoke_sub_agent()    # 지시문 주입 → Scraper 실행
  [TASK REPORT] 수신    # 5줄 결과 포인터 수신
  task_update('DONE')   # Blackboard 상태 업데이트
  exit_plan()           # 완료 선언
```

> **핵심 교훈**: Dynamic Context Pruning은 컨텍스트 오염을 막지만, 그 대가로 정보 비대칭 문제를 만든다. 이를 해소하는 것이 Blackboard 패턴이다. "맥락 단절 → 파일 기반 공유"가 멀티에이전트 설계의 핵심 트레이드오프다.

---

## 3. Sub-Agent Protocol Overlay — 역할 전환 기법

### 문제: 동일 에이전트를 두 가지 맥락에서 사용

`Scraper`는 두 가지 맥락에서 사용됩니다:
1. **Chat UI 메인 에이전트**: 사용자와 직접 대화 (인사, 확인 질문 허용)
2. **Supervisor의 Sub-agent**: 즉각 실행, `[TASK REPORT]` 반환 강제

시스템 프롬프트를 수정하면 1번 맥락이 망가집니다. 이를 **HumanMessage에 프로토콜 헤더를 주입**하는 방식으로 해결합니다.

### 3-Layer 메시지 구조

`invoke_sub_agent`가 Scraper에게 넘기는 메시지는 다음 3가지 레이어로 구성됩니다:

```
[LAYER 1 — Protocol Header]   ← 역할 계약 수립 (고정 주입)
[SUB-AGENT MODE - STRICT PROTOCOL]
You are operating as a sub-agent under a Supervisor. You MUST follow these rules:
1. NO greetings or conversational responses. Execute the task immediately.
2. On ANY blocker: return [BLOCKER: <reason>]
3. On success: write results to disk, return [TASK REPORT] format
══════════════════════════

[LAYER 2 — Context]           ← 파일 경로 목록 주입
Target File List: artifacts/data/quotes_supervisor_test.json
══════════════════════════

[LAYER 3 — Task]              ← Supervisor의 지시문 주입
Instruction: http://quotes.toscrape.com 1페이지 명언 수집 후 저장하라.
```

### 실제 구현 — `supervisor_tools.py`

```python
_FULL_PROTOCOL_HEADER = """\
[SUB-AGENT MODE - STRICT PROTOCOL]
You are operating as a sub-agent under a Supervisor. You MUST follow these rules:
1. NO greetings or conversational responses. Execute the task immediately.
2. On ANY blocker (corrupted file / site blocked / selector failure / access denied):
   STOP immediately and return EXACTLY:
   [BLOCKER: <concise reason>]
3. On success: write all results to disk first, then return EXACTLY:
   [TASK REPORT]
   - Status: SUCCESS
   - Target Files: <comma-separated file paths>
   - Artifacts Created: <created file paths>
   - Summary: <1-2 sentence core finding>
   - Issues: None
══════════════════════════════════════════════════════════"""

def _build_subagent_message(task_instruction, target_file_list, is_first_call) -> str:
    header = _FULL_PROTOCOL_HEADER if is_first_call else _PROTOCOL_REMINDER
    file_list_str = ", ".join(target_file_list) if target_file_list else "없음"
    return (
        f"{header}\n"
        f"Target File List: {file_list_str}\n"
        f"══════════════════════════════════════════════════════════\n"
        f"Instruction: {task_instruction}"
    )
```

### 첫 호출 vs 이후 호출 분기

Sub-agent 세션이 유지되는 환경에서 매 호출마다 Full Header를 주입하면 중복 문제가 발생합니다. 세션 이력을 조회하여 분기합니다:

```python
# 4. 첫 호출 여부 판단 — 세션 이력 조회
prior_messages = await client.get_messages(sub_thread_id)
is_first_call = len(prior_messages) == 0
```

| 호출 순서 | 주입 내용 | 목적 |
|:---:|:---|:---|
| **첫 번째** | Full Protocol Header (전체 규약) | 역할 계약 수립 |
| **두 번째~** | `[CONTINUE SUB-AGENT PROTOCOL]` 단 3줄 | 기존 계약 참조 지시 |

이후 호출의 Reminder:
```
[CONTINUE SUB-AGENT PROTOCOL]
This is a follow-up task in the same session.
Apply the same strict sub-agent protocol established earlier:
no conversational responses, return [BLOCKER] on failure, [TASK REPORT] on success.
```

> **핵심 교훈**: 에이전트의 역할 전환은 시스템 프롬프트 수정이 아니라 HumanMessage 첫 블록에 프로토콜 헤더를 주입하는 방식으로 달성한다. 이를 통해 동일 에이전트가 두 가지 맥락(메인 에이전트 / Sub-agent)에서 자연스럽게 동작할 수 있다.

---

## 4. Thread ID 설계 — 세션 연속성과 독립성의 균형

### 문제: Sub-agent에게 몇 번 연속으로 요청할 때

Supervisor가 Scraper를 여러 번 호출하는 시나리오:

```
1차 invoke_sub_agent: "1-2페이지 수집해줘"
2차 invoke_sub_agent: "아까 수집한 데이터에서 3-5페이지도 추가 수집해"
```

2차 호출에서 "아까 수집한 데이터"를 Scraper가 기억하려면 **동일 세션**이어야 합니다. 하지만 Supervisor와 같은 세션을 쓰면 독립적인 메시지 히스토리를 유지할 수 없습니다.

### 해법: `supervisor_tid + "_" + role` 네이밍 컨벤션

```python
# 2. Sub-agent 전용 세션 ID 구성 (연속성 보장)
sub_thread_id = f"{supervisor_tid}_{subagent_role}"
```

예시:
```
Supervisor thread_id : "session_abc123"
Scraper  thread_id   : "session_abc123_scraper"   ← 독립 세션, 연속성 보장
Analyst  thread_id   : "session_abc123_analyst"   ← 독립 세션, 연속성 보장
```

### ToolRuntime으로 thread_id 자동 추출

도구 함수 내부에서 Supervisor의 `thread_id`를 가져오는 방법으로 `ToolRuntime`을 활용합니다. `runtime` 파라미터는 LLM의 function call 스키마에 **노출되지 않으며**, 런타임에 자동 주입됩니다:

```python
from langgraph.prebuilt import ToolRuntime

@tool(args_schema=InvokeSubAgentInput)
async def invoke_sub_agent(
    task_instruction: str,
    target_file_list: List[str] = [],
    subagent_role: str = "scraper",
    runtime: ToolRuntime = None,   # ← LLM에 노출되지 않음, 자동 주입
) -> str:
    # ToolRuntime으로 Supervisor의 thread_id 추출
    supervisor_tid = "supervisor_default"
    if runtime and runtime.execution_info and runtime.execution_info.thread_id:
        supervisor_tid = runtime.execution_info.thread_id
```

실험으로 검증된 `ToolRuntime`이 제공하는 정보:
```python
runtime.execution_info.thread_id    # → "test_session_supervisor_001"
runtime.execution_info.checkpoint_id
runtime.execution_info.task_id
runtime.config                      # RunnableConfig 전체
runtime.state                       # 현재 그래프 상태
runtime.tool_call_id
```

> **핵심 교훈**: Sub-agent의 thread_id는 `{supervisor_tid}_{role}` 패턴으로 구성하라. 독립적인 메시지 히스토리를 유지하면서 세션 연속성을 확보할 수 있다. thread_id는 ToolRuntime.execution_info.thread_id로 도구 내부에서 안전하게 추출한다.

---

## 5. 에이전트 팩토리 vs 서버 클라이언트 호출 — 아키텍처 선택

### 노트북 방식의 문제점

노트북(4번)의 `invoke_sub_agent`는 매 호출마다 새 에이전트 인스턴스를 생성합니다:

```python
# ❌ 노트북 방식 — 매번 새 인스턴스 생성
def run_worker_agent(...):
    worker = create_agent(model=..., tools=[...])  # 매번 초기화!
    result = worker.invoke(...)
```

이 방식의 문제점:

| # | 문제 | 영향 |
|:---:|:---|:---|
| 1 | 매 호출마다 LLM 초기화 + 도구 바인딩 반복 | 지연 증가 |
| 2 | 동기 `invoke()` — 서버는 async 기반 | 이벤트 루프 블로킹 위험 |
| 3 | Worker 도구 세트 하드코딩 | 역할 추가 시 코드 수정 필요 |
| 4 | 에러 핸들링 부재 | Worker 예외 → Supervisor 전체 크래시 |
| 5 | thread_id 충돌 가능성 | `time()` 기반 ID → 밀리초 단위 충돌 |
| 6 | 인라인 Worker 프롬프트 | 유지보수 어려움 |
| 7 | 레지스트리 하드코딩 | 역할 추가 시 코드 수정 필요 |

### 해법: AgentClient 기반 서버 내부 호출

```python
# ✅ 프로덕션 방식 — 서버를 통한 캐시된 에이전트 호출
client = AsyncAgentClient(base_url="http://localhost:8000")

# 3. Agent Registry 동적 조회 — GET /agents
available_agents = await client.get_agents()
agent_names = [a.get("name") for a in available_agents if isinstance(a, dict)]

# 6. 서버를 통한 비동기 Sub-agent 호출
response = await client.async_invoke(
    agent_name=subagent_role,
    message=message,
    thread_id=sub_thread_id,
)
```

### `AsyncAgentClient.async_invoke` 구현 — `client.py`

```python
async def async_invoke(
    self,
    agent_name: str,
    message: str,
    thread_id: Optional[str] = None,
) -> dict:
    url = f"{self.base_url}/agents/{agent_name}/invoke"
    payload = {"message": message, "thread_id": thread_id}

    async with httpx.AsyncClient(timeout=httpx.Timeout(self.timeout, connect=10.0)) as client:
        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            return {"type": "error", "content": str(e)}
```

이 방식으로 얻는 이점:
- **`server.py`의 `get_or_load_agent()`** 캐시 재활용 → 인스턴스 재생성 없음
- **`GET /agents`** 로 Agent Registry 동적 조회 → 레지스트리 딕셔너리 불필요
- Supervisor-Scraper 간 HTTP 호출은 모두 `async` → asyncio Self-Call 데드락 없음
- 서버 표준 파이프라인(로깅, 메시지 DB 저장) 자동 적용

> **핵심 교훈**: 프로덕션 환경에서 Sub-agent는 새 인스턴스를 생성하지 말고, 서버의 캐시된 에이전트를 HTTP 클라이언트로 호출하라. 서버 자체가 Agent Registry이자 인스턴스 풀이다.

---

## 6. 시스템 프롬프트 vs 도구 Docstring — 책임 분리 원칙

### 안티패턴: 모든 규약을 시스템 프롬프트에 넣기

시스템 프롬프트에 도구 사용 절차까지 상세히 기술하면:
- **토큰 낭비**: 매 요청마다 긴 시스템 프롬프트가 컨텍스트를 차지
- **유지보수 어려움**: 도구 변경 시 시스템 프롬프트도 함께 수정 필요
- **중복**: 같은 정보가 시스템 프롬프트와 도구 docstring 양쪽에 존재

### 해법: 레이어별 책임 분리

| 레이어 | 담당 내용 | 특징 |
|:---|:---|:---|
| **시스템 프롬프트** | 행동 철학(Principle) — 언제 무엇을 할 것인가 | 간결, 불변 |
| **도구 Docstring** | 실행 절차(Procedure) — 어떻게 할 것인가 | 도구와 함께 관리 |

### Supervisor 시스템 프롬프트 — `SUPERVISOR.py`

```python
SUPERVISOR_SYSTEM_PROMPT = """
[핵심 원칙]
1. 직접 처리 우선 (Direct Execution First)
   범용 작업은 직접 도구를 사용하여 즉시 처리하라.
   단순한 작업에 Planning을 적용하는 것은 불필요한 오버헤드다.

2. 계획 후 위임 (Plan Then Delegate)
   전문 역량이 필요한 작업은 Planning 도구로 계획을 수립한 뒤
   전문 sub-agent에게 invoke_sub_agent로 위임하라.
   세부 실행 절차는 invoke_sub_agent 도구의 설명을 참고하라.  ← 위임!

3. 자가 치유 (Self-Healing on Failure)
   sub-agent의 실패([BLOCKER])는 전체 파이프라인을 멈추게 하지 않는다.
   자세한 절차는 invoke_sub_agent 도구의 설명을 참고하라.       ← 위임!
"""
```

### 도구 Docstring — `supervisor_tools.py`

```python
@tool(args_schema=InvokeSubAgentInput)
async def invoke_sub_agent(...) -> str:
    """Delegates a focused task to a specialized sub-agent running on the server.

    WHEN TO USE:
      - Web scraping / data collection tasks → subagent_role="scraper"
      - Data analysis / chart generation    → subagent_role="analyst"

    PROTOCOL — BEFORE CALLING:
      1. Register a task with task_create() to track this delegation.
      2. Set target_file_list to exact output artifact path(s).

    PROTOCOL — AFTER RECEIVING RESPONSE:
      - [TASK REPORT] + Status: SUCCESS → task_update(task_id, 'COMPLETED')
      - [BLOCKER: reason]               → task_update(task_id, 'BLOCKED')
                                          → task_create() fallback & retry
    """
```

> **핵심 교훈**: 시스템 프롬프트는 "무엇을 해야 하는가(원칙)"만 담고, "어떻게 해야 하는가(절차)"는 각 도구의 docstring에 위임하라. LLM은 도구를 호출할 시점에 docstring을 참조하므로 중복 없이 정확한 행동을 유도할 수 있다.

---

## 7. Self-Healing — Backtracking 설계

### [BLOCKER] 기반 Backtracking 루프

Sub-agent가 작업을 완수할 수 없을 때 `[BLOCKER: reason]`을 반환하면, Supervisor는 파이프라인을 멈추지 않고 자가 치유 루프를 실행합니다:

```
invoke_sub_agent 반환값 분기:

┌─ [TASK REPORT] Status: SUCCESS
│    └─ task_update(task_id, 'COMPLETED')
│    └─ 다음 태스크로 진행
│
└─ [BLOCKER: <reason>]
     └─ task_update(task_id, 'BLOCKED')
     └─ 원인 분석 (reason 파싱)
     └─ task_create() → 대안 태스크 등록
     └─ invoke_sub_agent() → 수정된 파라미터로 재위임
```

### Backtracking 시나리오 예시

```
1차 시도: invoke_sub_agent("quotes.toscrape.com 수집", role="scraper")
   → [BLOCKER: 사이트 접근 차단 (403 Forbidden)]

Supervisor:
   → task_update(task_id="T001", status="BLOCKED")
   → task_create(title="대안 수집", desc="books.toscrape.com으로 전환")
   → invoke_sub_agent("books.toscrape.com 수집", role="scraper")
   → [TASK REPORT] Status: SUCCESS ✅
```

Sub-agent 도구에서도 `[BLOCKER]`가 안전하게 반환되도록 모든 실패 경로를 처리합니다:

```python
# Agent Registry 조회 실패
except Exception as e:
    return f"[BLOCKER: Failed to query agent registry — {str(e)}]"

# 유효하지 않은 역할
if subagent_role not in agent_names:
    return f"[BLOCKER: Unknown subagent_role '{subagent_role}'. Available: {agent_names}]"

# Sub-agent 실행 중 예외
except Exception as e:
    return f"[BLOCKER: Sub-agent execution exception — {str(e)}]"
```

> **핵심 교훈**: `[BLOCKER]`는 에러가 아니라 "처리 불가 신호"다. Supervisor는 이를 받으면 파이프라인을 멈추지 않고 대안을 찾는 자가 치유 루프를 실행한다. 모든 실패 경로가 `[BLOCKER]`를 반환하도록 도구 내부에서 방어적으로 처리해야 한다.

---

## 부록: 실험 결과 Walkthrough

**환경**: AAWS v2.0, LangChain 1.3.15, `gemini-3.7-flash`  
**Supervisor thread_id**: `test_session_supervisor_v2`  
**Scraper sub-thread_id**: `test_session_supervisor_v2_scraper`

### 시나리오별 결과 요약

| # | 시나리오 | 응답시간 | Supervisor 동작 방식 | 결과 |
|:---:|:---|:---:|:---|:---:|
| 1 | 인사 | 3s | 도구 없이 즉시 직접 응답 (AI 어시스턴트 페르소나) | ✅ |
| 2 | ReAct 질문 | 4.3s | 도구 없이 즉시 직접 응답 | ✅ |
| 3 | 웹 검색 | 10.3s | `web_search` 직접 사용 (코드 예시 포함) | ✅ |
| 4 | 피보나치 코딩 | 2.6s | 도구 없이 즉시 직접 응답 (한국어 에러 메시지) | ✅ |
| 5 | 스크래핑 위임 | 59.9s | `enter_plan → task_create → invoke_sub_agent → task_update → exit_plan` | ✅ |
| 6 | Sub-agent 후속 질문 | 7.7s | Scraper가 이전 세션 맥락 및 셀렉터 회상 | ✅ |

---

### Test 1. 간단한 인사 (응답시간: 3s)

**[USER → Supervisor]**
> 안녕하세요! 당신은 어떤 역할을 하는 에이전트인가요?

**[Supervisor]**

안녕하세요! 저는 일상적인 질문 답변부터 복잡한 작업까지 다방면으로 도와드리는 **AI 어시스턴트**입니다.

주로 다음과 같은 작업을 수행할 수 있습니다:

1. **정보 검색 및 질의응답**: 최신 정보 검색, 일반 지식 설명, 문서 요약 등
2. **코드 및 기술 작업**: 프로그래밍 코드 작성·디버깅, 텍스트 및 파일 편집
3. **전문 데이터 작업**: 전문 에이전트와 협업하여 웹 데이터 수집(스크래핑) 및 심층 데이터 분석·리포트 생성
4. **체계적인 작업 관리**: 여러 단계가 필요한 복잡한 프로젝트 계획 수립 및 실행

궁금한 점이나 도움이 필요한 작업이 있으시면 편하게 말씀해 주세요!

> 🔍 **분석**: "총괄 오케스트레이터"라는 시스템 직함 대신, 사용자 관점의 가치를 제공하는 친근한 "AI 어시스턴트" 페르소나로 직접 응답 → 원칙 1(규모에 맞게 즉시 처리) 및 사용자 친화적 커뮤니케이션 준수.

---

### Test 2. 일반 지식 질문 — ReAct 패턴 (응답시간: 4.3s)

**[USER → Supervisor]**
> ReAct(Reasoning + Acting) 패턴이 뭔지 한 문단으로 설명해줘.

**[Supervisor]**

**ReAct(Reasoning and Acting)** 패턴은 대형 언어 모델(LLM)이 문제를 해결할 때 **'생각(Reasoning)'과 '행동(Acting)'을 교대로 반복**하도록 유도하는 프롬프트 및 에이전트 프레임워크입니다. 모델이 주어진 상황을 스스로 분석하고 추론한 뒤 필요한 도구(웹 검색, 계산기, API 등)를 사용해 행동을 수행하고, 그 결과로 얻은 관찰(Observation) 내용을 바탕으로 다시 다음 단계의 생각과 행동을 결정해 나가는 방식으로 작동하여, 단순 추론 시 발생할 수 있는 환각을 줄이고 복잡한 다단계 작업을 높은 정확도로 해결할 수 있습니다.

> 🔍 **분석**: 단순 개념 질의 → 도구 호출 오버헤드 없이 즉시 답변 제공. 환각 방지 등 실용적 이점 설명 포함.

---

### Test 3. 웹 검색 (응답시간: 10.3s)

**[USER → Supervisor]**
> LangChain 1.x의 create_agent 함수가 최근에 어떤 변화가 있었는지 웹 검색해서 간단히 알려줘.

**[Supervisor]** *(`web_search` 도구 직접 사용)*

LangChain 1.x / LangGraph 1.0 릴리스에서 에이전트 생성 방식에 주요 변화가 있었습니다:

1. **`create_agent`로의 통합 및 표준화**
   - 기존의 `AgentExecutor`나 `langgraph.prebuilt.create_react_agent`가 **더 이상 권장되지 않고(Deprecated)**, `langchain.agents.create_agent`가 공식 표준 진입점으로 자리 잡았습니다.
   - 내부적으로는 **LangGraph 엔진을 기반으로 구동**되어 안정적인 루프 제어와 상태 관리를 제공합니다.

2. **간결해진 인터페이스**
   - 모델, 도구 목록, 시스템 프롬프트를 직관적으로 전달하는 방식으로 단순화되었습니다:
     ```python
     from langchain.agents import create_agent

     agent = create_agent(
         model="gpt-4o",
         tools=[search_tool],
         system_prompt="You are a helpful assistant."
     )
     ```

3. **유연한 미들웨어 및 확장 기능 도입**
   - 도구 실행 전후 제어, 에러 핸들링(`wrap_tool_call`), 동적 프롬프트(`@dynamic_prompt`), Human-in-the-loop(사람 개입 승인) 설정 등이 미들웨어 형태로 한층 더 정교해졌습니다.

4. **패키지 정리**
   - 이전 레거시 패턴이나 도구들은 `langchain-classic`으로 분리되고, 핵심 추상화 중심으로 패키지가 슬림화되었습니다.

> 🔍 **분석**: 외부 최신 정보 탐색 작업 → `web_search` 도구 직접 활용. Planning 단계 없이 단일 도구 직접 처리 후 구체적인 코드 예시와 함께 간결히 답변.

---

### Test 4. 간단한 코딩 요청 (응답시간: 2.6s)

**[USER → Supervisor]**
> Python으로 피보나치 수열 n번째 값을 재귀 없이 반환하는 함수를 작성해줘. 코드만 보여줘.

**[Supervisor]**

```python
def fibonacci(n: int) -> int:
    if n < 0:
        raise ValueError("n은 0 이상의 정수여야 합니다.")
    if n <= 1:
        return n

    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b
```

> 🔍 **분석**: 최소 응답시간(2.6s). "코드만 보여줘"라는 제약조건에 맞춰 불필요한 설명 없이 간결하게 코드만 제공하며, 에러 메시지 또한 한국어 환경에 맞게 자연스럽게 생성.

---

### Test 5. 웹 스크래핑 위임 — invoke_sub_agent → Scraper (응답시간: 59.9s)

**[USER → Supervisor]**
> http://quotes.toscrape.com 사이트에서 1페이지의 명언(text, author, tags)을 수집해서 'artifacts/data/quotes_v2_test.json' 파일로 저장하고, 수집된 결과 요약을 보고해줘. Task Board에 계획을 등록하고 Scraper에게 위임해서 진행해줘.

**[Supervisor]** *(내부 실행: `enter_plan` → `task_create` → `invoke_sub_agent` → Scraper 실행 → `task_update` → `exit_plan`)*

웹 스크래핑 작업을 성공적으로 완료하고 데이터를 저장했습니다.

---

#### 📊 수집 결과 요약

- **수집 대상**: `http://quotes.toscrape.com` (1페이지)
- **수집 건수**: 총 **10건**의 명언 데이터
- **수집 항목**: 명언 문구(`text`), 작가(`author`), 태그 목록(`tags`)
- **주요 수집 작가**: Albert Einstein, J.K. Rowling, Jane Austen, Marilyn Monroe, André Gide, Thomas A. Edison, Eleanor Roosevelt, Steve Martin
- **저장 파일**: `artifacts/data/quotes_v2_test.json`

> 🔍 **분석**: 다단계 전문 작업 → Planning 도구로 상태를 등록하고 Scraper에게 위임.
> 원문 데이터 10건 전체를 대화 메시지로 나열하지 않고 **핵심 요약 + 결과 파일 포인터**만 보고하여 컨텍스트 오염을 원천 차단(Dynamic Context Pruning 실증).

---

### Test 6. Sub-agent(Scraper)에게 후속 질문 — 세션 연속성 검증 (응답시간: 7.7s)

> **검증 조건**: 동일 `sub_thread_id = "test_session_supervisor_v2_scraper"` 로 Scraper에 직접 후속 질문.
> Test 5에서의 작업 맥락(CSS 셀렉터, 구조적 특징)을 Scraper가 기억하고 있는지 확인.

**[USER → Scraper (직접 호출)]**
> 방금 quotes.toscrape.com에서 데이터 수집할 때 사용한 CSS 셀렉터가 뭐였어? 페이지 구조에서 특이한 점도 알려줘.

**[Scraper]** *(동일 `_scraper` 세션 이력 참조)*

방금 `quotes.toscrape.com` 데이터 수집에 사용한 CSS 셀렉터와 페이지 구조의 특징은 다음과 같습니다.

---

#### 1. 사용된 CSS 셀렉터

| 필드 | 셀렉터 | 설명 |
| :--- | :--- | :--- |
| **명언 컨테이너** | `div.quote` | 개별 명언 블록 단위 (1페이지당 10개) |
| **명언 본문 (`text`)** | `span.text` | 큰따옴표가 포함된 명언 텍스트 |
| **작성자 (`author`)** | `small.author` | 명언 하단의 저자 이름 |
| **태그 목록 (`tags`)** | `div.tags a.tag` | 개별 명언에 달린 태그 목록 (`<a>` 태그 리스트) |

---

#### 2. 페이지 구조 및 특이사항

1. **순수 정적(SSR) 페이지 구조**
   - JavaScript 실행 없이 초기 HTML 응답에 모든 텍스트/데이터가 온전히 담겨 있어 브라우저 렌더링(Playwright 등) 없이 `requests`와 `BeautifulSoup`만으로 빠르게 수집할 수 있습니다.

2. **우측 사이드바 태그 혼동 주의 (`a.tag` 중복)**
   - 본문 영역(`div.col-md-8`)의 명언 태그뿐만 아니라, 우측 사이드바(`div.col-md-4 tags-box`)의 "Top Ten tags"에도 동일하게 `a.tag` 클래스가 사용됩니다.
   - 따라서 단순히 `a.tag` 전체를 탐색하지 않고 반드시 `div.quote` 컨테이너 내부의 `div.tags a.tag`로 범위를 한정해야 사이드바 데이터 혼입을 방지할 수 있습니다.

3. **태그 개수의 가변성**
   - 명언마다 태그 개수가 다릅니다(2개~5개 등). 단일 텍스트가 아닌 태그 배열(List) 형태로 수집하도록 처리해야 합니다.

4. **단순한 페이지네이션 구조**
   - 하단 다음 페이지 링크가 `li.next a` 형태로 되어 있으며, URL 패턴이 `/page/2/`, `/page/3/` 형태로 직관적이어서 다중 페이지 확장 시 루프 처리가 매우 간단합니다.

> 🔍 **분석**: Test 5에서 Scraper가 진행했던 실제 파싱 셀렉터와 사이드바 충돌 주의점 등을 `test_session_supervisor_v2_scraper` 세션에서 정확히 회상.
> `{supervisor_tid}_{role}` 세션 네이밍 컨벤션으로 독립성과 연속성이 안정적으로 유지됨을 확인.

---

### 핵심 검증 항목

- ✅ **원칙 1 준수**: 1~4번 시나리오에서 불필요한 계획 수립 없이 즉시 직접 처리 (2.6s ~ 10.3s)
- ✅ **원칙 2 준수**: 5번에서 Planning 전체 파이프라인 정확 실행 → `artifacts/data/quotes_v2_test.json` (10건) 생성 및 간결 보고
- ✅ **세션 연속성**: 6번에서 Scraper가 `_scraper` 세션 이력으로부터 셀렉터 및 구조 분석 세부사항을 완벽 회상
- ✅ **Context Pruning**: Supervisor 응답에 10건 데이터 본문 대신 핵심 요약 및 파일 포인터만 반환하여 부모 컨텍스트 보호

---

*관련 구현 파일: `supervisor_tools.py` · `supervisor.py` · `SUPERVISOR.py` · `client.py`*
