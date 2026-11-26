# Long-Running Sub-Agent & Reactive Wakeup 설계 패턴 — 핵심 교훈

> **대상 독자**: AAWS(Agent-As-a-Worker-Service) 교육 수강생  
> **관련 파일**: `app/server.py`, `app/client.py`, `app/tools/supervisor_tools.py`, `app/prompts/SUPERVISOR.py`, `app/chainlit_ui.py`

---

## 목차

1. [Long-Running 패턴이 필요한 이유 — Sync-over-HTTP의 한계](#1-long-running-패턴이-필요한-이유--sync-over-http의-한계)
2. [전체 아키텍처 시퀀스 다이어그램 — Event-Driven Reactive Wakeup](#2-전체-아키텍처-시퀀스-다이어그램--event-driven-reactive-wakeup)
3. [FastAPI Task Registry & Job Store 설계 — `server.py`](#3-fastapi-task-registry--job-store-설계--serverpy)
4. [Reactive Agent Wakeup — 서브에이전트 완료/실패 시 Supervisor 자동 재개](#4-reactive-agent-wakeup--서브에이전트-완료실패-시-supervisor-자동-재개)
5. [통합 확장형 도구 인터페이스 — `invoke_sub_agent`, `get_sub_agent_job_status` & `cancel_sub_agent_job`](#5-통합-확장형-도구-인터페이스--invoke_sub_agent-get_sub_agent_job_status--cancel_sub_agent_job)
6. [시스템 프롬프트 위임 원칙 — 언제 백그라운드로 보낼 것인가?](#6-시스템-프롬프트-위임-원칙--언제-백그라운드로-보낼-것인가)
7. [부록: 4대 핵심 시나리오 실험 검증 Walkthrough](#7-부록-4대-핵심-시나리오-실험-검증-walkthrough)

---

## 1. Long-Running 패턴이 필요한 이유 — Sync-over-HTTP의 한계

### 왜 동기식 HTTP 대기(Sync-over-HTTP)는 실패하는가?

웹 스크래핑(3~5분 소요), 다단계 통계 분석, 복합 차트 및 대시보드 생성과 같은 무거운 작업은 단일 요청-응답 모델로 처리할 수 없습니다:

- **HTTP ReadTimeout 발생**: HTTP 클라이언트(httpx, fetch 등)의 기본 타임아웃(1~2분)을 초과하여 연결이 강제 종료됨
- **UI 및 사용자 대화의 완전 블로킹**: 서브에이전트가 작업을 끝낼 때까지 2~3분 동안 화면에 로딩만 표시되고 중간 대화나 질의응답이 불가능
- **네트워크 순단에 취약**: 일시적인 네트워크 끊김이나 게이트웨이 타임아웃(504 Gateway Timeout) 시 에이전트 전체 파이프라인이 즉시 크래시

```
❌ 잘못된 방식 — 동기식 HTTP 대기 (블로킹)
Supervisor ──[HTTP POST /invoke (2~3분간 연결 유지 대기)]──> Worker
                                                               ↓ (120초 경과 시 타임아웃 크래시 💥)

✅ 올바른 방식 — 비동기 잡 등록 (0.1초 즉시 반환) + 백그라운드 실행
Supervisor ──[POST /jobs (Job ID 발급)]──> Server (0.1초 만에 반환 ✅)
                                              └─ Background Task로 Worker 비동기 구동
```

> **핵심 교훈**: 오래 걸리는 작업은 결코 동기식 연결을 붙잡고 기다려서는 안 된다. 작업 요청 즉시 `job_id`를 반환하고 서버 백그라운드 코루틴으로 안전하게 분기시켜야 한다.

---

## 2. 전체 아키텍처 시퀀스 다이어그램 — Event-Driven Reactive Wakeup

서브에이전트가 백그라운드에서 완료되었을 때 단순히 DB에만 넣어두면 사용자가 직접 *"다 됐어?"* 하고 물어보기 전까지 알 수 없습니다.  
우리는 **서버가 완료 이벤트를 감지하여 Supervisor 에이전트를 자동으로 깨워(Wakeup) 최종 종합 보고서와 시각화 대시보드를 스스로 완성**하도록 설계했습니다:

```mermaid
sequenceDiagram
    autonumber
    actor User as 👤 사용자
    participant UI as 💬 Chainlit UI
    participant Sup as 👑 Supervisor (supervisor)
    participant API as 🚀 FastAPI 작업 관리자 (Job Runner)
    participant Sub as 🔬 Sub-Agent (analyst / scraper)

    User->>UI: "키보드 분석 대시보드 백그라운드로 만들어줘"
    UI->>Sup: POST /agents/supervisor/stream
    Sup->>API: invoke_sub_agent(run_in_background=True)<br/>POST /agents/analyst/jobs
    API->>Sub: 독립 세션(sub_thread_id)으로 백그라운드 실행 시작
    activate Sub
    API-->>Sup: Job ID: job_123 즉시 반환 (~0.1초)
    Sup-->>UI: "Analyst에게 백그라운드 작업을 위임했습니다 (Job ID: job_123)" (1차 턴 종료)
    UI-->>User: 작업 시작 안내 (대기 중 다른 질문·대화 자유롭게 진행)

    Note over Sub: 2분 뒤... 독립 컨텍스트에서 분석 및 HTML 대시보드 생성 완료!
    Sub-->>API: [TASK REPORT] 산출물 경로 및 완료 보고 반환
    deactivate Sub

    API->>Sup: 완료 통보 (Reactive Wakeup)<br/>[SYSTEM NOTIFICATION: BACKGROUND TASK COMPLETED] + [TASK REPORT]
    activate Sup
    Note over Sup: 완료 보고서 검토 및 후속 작업 수행<br/>(결과 종합, 필요 시 추가 위임, Render_HTML 응답 구성)
    Sup-->>API: 최종 응답(supervisor_response) 작성 및 Checkpointer/Job Store 저장
    deactivate Sup

    UI->>API: 세션 모니터링 (GET /sessions/{thread_id}/jobs)
    API-->>UI: 완료 상태 + Supervisor 최종 응답 전달
    UI-->>User: 🔔 "[백그라운드 작업 완료] 알림" + 최종 보고서 및 대시보드 자동 렌더링!
```

> **💡 UI 연동 핵심 팁**: 프론트엔드(Chainlit)는 대화 세션(`thread_id`)을 기준으로 서버의 `GET /sessions/{thread_id}/jobs` 엔드포인트를 주기적으로 확인(Session Monitoring)합니다. 이를 통해 서브에이전트가 완료되고 Supervisor의 Wakeup 응답(`supervisor_response`)이 준비되는 즉시 사용자 개입 없이 화면에 결과와 시각화 대시보드를 띄워줍니다.

---

## 3. FastAPI Task Registry & Job Store 설계 — `server.py`

### Job 데이터 모델 및 인메모리 스토어

```python
class JobSubmitInput(BaseModel):
    message: str
    thread_id: Optional[str] = None
    parent_thread_id: Optional[str] = None
    callback_agent: Optional[str] = "supervisor"
    callback_thread_id: Optional[str] = None
    user_id: Optional[str] = None

# --- In-Memory Job Store & Task Registry ---
job_store: Dict[str, dict] = {}
job_tasks: Dict[str, asyncio.Task] = {}
MAX_CONSECUTIVE_FAILED_WAKEUPS = 3
```

### Job 제출 · 취소 · 조회 엔드포인트

- **`POST /agents/{agent_name}/jobs`**: `asyncio.create_task()`로 실행 태스크를 `job_tasks`에 추적 등록하고 `job_id`와 `sub_thread_id`를 즉시 반환합니다. (`CANCELLED`된 `sub_thread_id` 재사용 요청은 `409 Conflict`로 차단)
- **`POST /jobs/{job_id}/cancel`**: 실행·대기 중인 태스크를 즉시 취소하고 `PlaywrightManager.close_session_tabs(sub_thread_id)`로 브라우저 탭을 정리하며 Wakeup(`wakeup_status="SKIPPED"`)을 억제합니다. (`caller_thread_id` 불일치 시 `403 Forbidden`)
- **`GET /jobs/{job_id}` & `GET /sessions/{thread_id}/jobs`**: `AgentLogTracer.get_session_snapshot()`을 결합해 실시간 LLM/도구 실행 현황(`progress`, `progress_report`)을 반환합니다. 목록 조회는 활성 Job에만 인메모리 스냅샷을 결합해 디스크 I/O를 방지하고, 단건 상세 조회만 디스크 로그 폴백을 허용합니다.

---

## 4. Reactive Agent Wakeup — 서브에이전트 완료/실패 시 Supervisor 자동 재개

### 백그라운드 워커 내부 구현 (`_run_agent_job` & `_trigger_reactive_wakeup`)

서브에이전트가 작업을 성공(`SUCCESS`)하거나 예외로 실패(`FAILED`)한 직후, 서버가 `callback_agent`(`supervisor`)를 자동으로 깨워 후속 조치를 트리거합니다:
- **`SUCCESS` Wakeup**: `[TASK REPORT]`와 산출물 경로를 전달해 최종 보고서 작성·후속 위임을 수행하고 `wakeup_status="COMPLETED"`를 기록합니다.
- **`FAILED` Wakeup**: 오류 상세와 `AgentLogTracer` 실행 텔레메트리를 함께 전달하며, 동일 서브에이전트의 연속 실패가 `MAX_CONSECUTIVE_FAILED_WAKEUPS`(3회)를 초과하면 무한 재귀 루프를 막기 위해 Wakeup을 억제합니다.
- **`CANCELLED` 억제**: 취소 요청(`cancel_requested=True`)이 발생하면 정리 중 예외가 나더라도 `FAILED`로 덮어쓰지 않고 `CANCELLED` 상태 유지, 브라우저 탭 정리 및 Wakeup 억제를 보장합니다.

> 💡 **대화 이력 저장 방식**: 서버는 모든 에이전트에 공유 `AsyncSqliteSaver`(`app/database/checkpoints.db`, WAL 모드)를 주입합니다. UI가 조회하는 `/sessions/{id}/messages`도 이 체크포인트에서 직접 읽어오므로, Wakeup으로 추가된 Supervisor 응답이 별도 저장 코드 없이 채팅 이력에 그대로 나타납니다. (서버가 주입한 `[SYSTEM NOTIFICATION: ...]` 트리거 메시지는 체크포인트에는 남지만, UI 조회 시에는 자동으로 숨겨집니다.)

> **핵심 교훈**: 이벤트 기반 에이전트 오케스트레이션의 핵심은 "완료 콜백에서의 능동형 재호출(Wakeup)"이다. 이를 통해 사용자가 기다릴 필요 없이 백그라운드 완료 즉시 최종 산출물이 전달된다.

---

## 5. 통합 확장형 도구 인터페이스 — `invoke_sub_agent`, `get_sub_agent_job_status` & `cancel_sub_agent_job`

### 도구 분리 vs 단일 도구 확장 & 세션 격리(`sub_thread_id`)

도구를 `invoke_sync`와 `invoke_async`로 쪼개면 LLM이 도구 선택에 혼란을 겪습니다. 하나의 `invoke_sub_agent`에 `run_in_background: bool = False`와 선택적 `sub_thread_id: Optional[str] = None` 파라미터를 통합했습니다:

- **기본 호출 (`sub_thread_id=None`)**: 호출마다 고유한 `sub_thread_id` (`{supervisor_tid}_{subagent_role}_{uuid8}`)를 자동 생성합니다. 덕분에 한 세션에서 여러 `scraper`를 동시에 호출해도 각 서브에이전트의 단기 메모리(Checkpointer)가 섞이지 않고 완벽히 격리됩니다.
- **연속 작업 (`sub_thread_id` 전달)**: 도구 반환값이나 완료 알림에 포함된 `Sub-Thread ID`를 `sub_thread_id` 인자로 다시 전달하면, 해당 서브에이전트의 기존 Checkpointer 세션을 그대로 이어받아 후속 지시나 `[BLOCKER]` 복구를 수행합니다.

```python
class InvokeSubAgentInput(BaseModel):
    task_instruction: str = Field(description="Actionable step-by-step instruction.")
    target_file_list: List[str] = Field(default_factory=list)
    subagent_role: str = Field(default="scraper")
    run_in_background: bool = Field(
        default=False,
        description=(
            "Set to True for all production tasks (data analysis, chart generation, HTML dashboard, "
            "excel report, web scraping) to run asynchronously in the background."
        )
    )
    sub_thread_id: Optional[str] = Field(
        default=None,
        description=(
            "Optional session ID (Sub-Thread ID) of a previously invoked sub-agent to continue its work "
            "with preserved short-term memory. Leave None when starting a new task or running in parallel."
        )
    )

@tool(args_schema=InvokeSubAgentInput)
async def invoke_sub_agent(
    task_instruction: str,
    target_file_list: List[str] = [],
    subagent_role: str = "scraper",
    run_in_background: bool = False,
    sub_thread_id: Optional[str] = None,
    runtime: ToolRuntime = None,
) -> str:
    # ToolRuntime에서 Supervisor의 thread_id 추출
    supervisor_tid = "supervisor_default"
    if runtime and runtime.execution_info and runtime.execution_info.thread_id:
        supervisor_tid = runtime.execution_info.thread_id

    client = AsyncAgentClient(base_url="http://localhost:8000", timeout=600.0)

    # 새 작업이면 고유 sub_thread_id 자동 생성, 연속 작업이면 전달받은 sub_thread_id 재사용
    if sub_thread_id and sub_thread_id.strip():
        resolved_sub_tid = sub_thread_id.strip()
        prior_messages = await client.get_messages(resolved_sub_tid)
        is_first_call = len(prior_messages) == 0
    else:
        resolved_sub_tid = f"{supervisor_tid}_{subagent_role}_{uuid.uuid4().hex[:8]}"
        is_first_call = True

    message = _build_subagent_message(task_instruction, target_file_list, is_first_call)

    # 1. 백그라운드 모드 분기
    if run_in_background:
        job_res = await client.submit_job(
            agent_name=subagent_role,
            message=message,
            thread_id=resolved_sub_tid,
            callback_agent="supervisor",
            callback_thread_id=supervisor_tid,
        )
        job_id = job_res.get("job_id")
        return (
            f"[JOB SUBMITTED]\n"
            f"- Job ID: {job_id}\n"
            f"- Sub-Agent: {subagent_role}\n"
            f"- Sub-Thread ID: {resolved_sub_tid} (use sub_thread_id='{resolved_sub_tid}' to continue this agent)\n"
            f"- Status: RUNNING (Background)\n"
            f"- Tracking: The server will automatically notify and wake you up with full results when this job completes.\n"
            f"Please inform the user that the task has started in the background."
        )

    # 2. 일반 동기 모드 분기
    response = await client.async_invoke(
        agent_name=subagent_role,
        message=message,
        thread_id=resolved_sub_tid,
    )
    content = response.get("content", "[BLOCKER: Empty response]")
    return (
        f"{content}\n"
        f"- Sub-Thread ID: {resolved_sub_tid} (use sub_thread_id='{resolved_sub_tid}' to continue this agent)"
    )
```

### 상태 조회 및 중단 제어 도구 (`get_sub_agent_job_status` & `cancel_sub_agent_job`)

사용자가 진행 현황을 묻거나 작업 방향을 수정해야 할 때 Supervisor가 능동적으로 상태를 조회·중단하는 도구입니다 (두 도구 모두 계획 모드 중에도 호출 허용):

- **`get_sub_agent_job_status(job_id: Optional[str] = None)`**:
  - `job_id` 지정 시: 해당 작업의 상태, `AgentLogTracer` 기반 `[Live Execution Progress]`, 완료 보고서/`CANCELLED`/`FAILED` 상세 조회 (`caller_thread_id` 소유권 검증 포함)
  - `job_id` 생략 시: 현재 세션(`GET /sessions/{thread_id}/jobs`)의 모든 백그라운드 작업 요약 및 활성 텔레메트리 목록 반환
- **`cancel_sub_agent_job(job_id: str, reason: Optional[str] = None)`**:
  - `POST /jobs/{job_id}/cancel`을 호출해 실행·대기 중인 백그라운드 태스크를 즉시 중단하고 브라우저 탭 정리 및 Wakeup 억제를 수행합니다. (취소된 `sub_thread_id`는 `invoke_sub_agent`에서 재사용 차단)

---

## 6. 시스템 프롬프트 위임 원칙 — 언제 백그라운드로 보낼 것인가?

### LLM의 착각과 실무 가이드라인

LLM에게 단순 선택권을 주면 *"데이터가 이미 있으니 분석이 금방 끝나겠지"* 하고 동기 호출을 선택하는 실수를 합니다. 이를 방지하기 위해 프롬프트에 명확한 원칙을 주입합니다:

```python
SUPERVISOR_SYSTEM_PROMPT = """
- **전문가 활용하기 & 백그라운드 위임 원칙 (CRITICAL)**:
  - **`run_in_background=True` (기본 원칙)**:
    데이터 분석, 차트 생성, HTML 대시보드 작성, 엑셀 리포트 제작, 웹 스크래핑 등
    산출물을 생성하거나 여러 단계의 도구를 거치는 모든 실무 작업은 반드시 run_in_background=True로 위임하세요.
    (기존에 수집된 로컬 데이터가 이미 있더라도 분석 및 대시보드 작성은 여러 도구를 실행하므로 반드시 백그라운드로 실행해야 합니다.)
    백그라운드 위임 시 사용자에게는 작업이 백그라운드에서 시작되었음과 Job ID를 간결하게 안내하세요.
    작업이 완료되면 서버가 자동으로 당신을 다시 호출(Wakeup)하므로, 그때 최종 보고서와 시각화 태그(<Render_HTML> 등)를 출력하세요.

  - **`run_in_background=False` (예외)**:
    "에이전트 기능 설명해줘", "1줄 요약해줘" 같은 초경량 단순 질의에만 예외적으로 사용하세요.

  - **백그라운드 작업 모니터링 & 취소 (`get_sub_agent_job_status`, `cancel_sub_agent_job`)**:
    진행 상태가 궁금하면 `get_sub_agent_job_status(job_id)`로 실시간 단계/도구 실행 현황을 조회하세요(`job_id` 생략 시 현재 세션 전체 작업 목록 조회).
    방향을 바꿔야 하거나 불필요해진 작업은 `cancel_sub_agent_job(job_id, reason)`으로 즉시 중단하고, 취소된 `sub_thread_id`는 재사용하지 마세요.

  - **실패 자동 알림 (`FAILED` Wakeup)**: 백그라운드 작업이 실패해도 서버가 오류 상세와 실행 궤적을 포함해 자동으로 당신을 다시 호출합니다.
"""
```

---

## 7. 부록: 4대 핵심 시나리오 실험 검증 Walkthrough

**테스트 환경**: AAWS v2.0, FastAPI `:8000`, Chainlit `:8080`, Python 3.12 (WSL)  
**테스트 스크립트**: `scratch/test_multi_scenarios.py`

### 종합 결과 요약

| # | 시나리오 | 동작 방식 | 응답시간 | 결과 |
|:---:|:---|:---|:---:|:---:|
| **1** | 동기식 빠른 위임 | `invoke_sub_agent(run_in_background=False)` | 8.2s | ✅ PASS |
| **2** | 백그라운드 위임 & Reactive Wakeup | `invoke_sub_agent(run_in_background=True)` ➔ Analyst ➔ Supervisor 자동 재개 | 94.5s | ✅ PASS |
| **3** | 작업 상태 실시간 조회 | `get_sub_agent_job_status(job_id)` 도구 호출 | 3.1s | ✅ PASS |
| **4** | 미등록 에이전트 Blocker 복원 | 없는 에이전트 요청 시 `[BLOCKER]` 수신 및 대안 제시 | 2.9s | ✅ PASS |

---

### Test 1. 동기식 서브에이전트 위임 (응답시간: 8.2s)

**[USER → Supervisor]**
> Analyst에게 요청해서 현재 사용 가능한 데이터 분석 도구 목록과 역량을 1줄로 요약받아서 나한테 알려줘.

**[Supervisor Response]**
> Analyst 에이전트의 데이터 분석 도구 및 핵심 역량 요약입니다:  
> **"데이터 프로파일링(`data_profiler`), Pandas 심층 분석(`data_query`), 정적·인터랙티브 시각화(`chart_generator`), 수식 포함 엑셀 보고서(`excel_writer`), HTML 대시보드(`html_report`) 및 포맷 변환(`file_converter`) 도구를 완비하여 전주기 데이터 분석과 맞춤형 리포트 생성이 가능합니다."**

> 🔍 **분석**: 단순 설명 질의 → 동기식(`run_in_background=False`)으로 즉시 결과를 받아 단일 턴으로 완결.

---

### Test 2. 백그라운드 위임 & Reactive Wakeup (소요시간: 94.5s)

**[1차 턴: USER → Supervisor]**
> 키보드 시장 분석 작업을 Analyst에게 백그라운드로 위임해줘.

**[Supervisor 1차 즉시 응답 (0.1초)]**
> 키보드 시장 분석 작업을 **Analyst**에게 백그라운드로 전달했습니다.  
> - **작업 ID (Job ID)**: `job_4caf3246`  
> - **담당 에이전트**: Analyst  
> - **상태**: 진행 중 (RUNNING)  
> 작업이 완료되면 최종 리포트 및 시각화 대시보드와 함께 안내해 드리겠습니다.

*(2분간 Analyst가 백그라운드에서 차트 4개, 엑셀, HTML 대시보드 파일 생성 완료)*

**[2차 턴: Server ➔ Supervisor Reactive Wakeup 자동 응답]**
> Analyst의 키보드 시장 심층 분석 작업이 완료되었습니다. 주요 분석 결과와 인터랙티브 시각화 대시보드를 안내해 드립니다.  
>  
> # 📊 글로벌 및 국내 키보드 시장 심층 분석 리포트  
> `<Render_HTML>artifacts/charts/keyboard_market_dashboard.html</Render_HTML>`  
>  
> ### 1. 시장 규모 및 성장 추이  
> - 글로벌 시장: 2026년 약 62.5억 달러(CAGR 6.8%) 규모  
> - 국내 시장: 3,220억 원 규모 (게이밍 기계식·자석축 중심 연 11.1% 고성장)  
>  
> ### 2. 주요 브랜드 점유율  
> - Logitech (31.2%) > Razer (14.8%) > Corsair (9.5%) > AULA/독거미 (12.5%)  
>  
> ### 📁 생성된 산출물  
> - 상세 분석 보고서: `artifacts/reports/keyboard_market_analysis.md`  
> - 인터랙티브 대시보드: `artifacts/charts/keyboard_market_dashboard.html`  

> 🔍 **분석**: 사용자 개입 없이 백그라운드 작업 완료 즉시 Supervisor가 스스로 깨어나 최종 보고서 작성 및 `<Render_HTML>` 태그 출력 성공.

---

### Test 3. 작업 상태 조회 도구 검증 (응답시간: 3.1s)

**[USER → Supervisor]**
> 방금 실행한 백그라운드 작업 'job_4caf3246'의 상태를 get_sub_agent_job_status 도구로 확인해서 알려줘.

**[Supervisor Response]**
> 백그라운드 작업(`job_4caf3246`)이 **성공적으로 완료(SUCCESS)**되었습니다.  
> - **수행 에이전트**: `analyst`  
> - **완료 시각**: 2026-08-26T22:31:31Z  
> - **분석 요약**: 글로벌 키보드 시장 62.5억 달러 규모 분석 및 대시보드 생성 완료  
> - **산출물**: `<Render_HTML>artifacts/charts/keyboard_market_dashboard.html</Render_HTML>`  

> 🔍 **분석**: `get_sub_agent_job_status` 도구를 통해 서버 Job Store로부터 완료 상태와 산출물을 정확히 조회.

---

### Test 4. 미등록 에이전트 Blocker 처리 (응답시간: 2.9s)

**[USER → Supervisor]**
> 존재하지 않는 'quantum_physicist' 에이전트에게 양자역학 논문 분석을 위임해봐.

**[Supervisor Response]**
> `quantum_physicist` 에이전트에게 위임을 시도했으나, 해당 에이전트가 등록되어 있지 않아 위임이 차단되었습니다.  
> ```text
> [BLOCKER: Unknown subagent_role 'quantum_physicist'. Available agents: ['analyst', 'chatbot', 'scraper', 'supervisor']]
> ```  
> **대안 안내**: 제가 직접 웹 검색(`web_search`)을 통해 논문을 분석해 드리거나, `analyst` 에이전트에게 심층 분석을 위임할 수 있습니다. 원하시는 방식을 말씀해 주세요!

> 🔍 **분석**: 에러로 크래시되지 않고 `[BLOCKER]`를 포착하여 대안(Fallback)을 제시하는 자가 치유(Self-Healing) 동작 확인.

---

*관련 구현 파일: `server.py` · `client.py` · `supervisor_tools.py` · `SUPERVISOR.py` · `chainlit_ui.py`*
