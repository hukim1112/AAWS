# Multi-Agent Patterns in LangChain

이 문서는 LangChain에서 다중 에이전트를 구축하는 두 가지 대표적인 패턴인 **Supervisor with Handoffs(핸드오프가 있는 매니저 에이전트)**와 **Supervisor with Agent as Tool(에이전트를 도구로 사용하는 매니저 에이전트)** 패턴을 설명합니다.

---

## 1. Supervisor with Handoffs 패턴
이 패턴에서 Supervisor(슈퍼바이저/매니저) 에이전트는 핸드오프 도구(`handoff tools`)를 사용하여 특정 작업을 담당하는 워커(Worker) 에이전트들에게 제어권을 위임(이관)합니다. 모든 에이전트가 LangGraph의 구조에서 하나의 노드로 취급되며 전체 대화 흐름(상태)를 이어받아 협력합니다.

### 1.1. 구현 예시
```python
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import MessagesState
from langchain_core.messages import HumanMessage

# 1) Domain Tools
@tool(description="출발지와 도착지로 항공편을 예약합니다.")
def book_flight(from_airport: str, to_airport: str) -> str:
    return f"{from_airport}에서 {to_airport}행 항공편 예약이 완료되었습니다."

@tool(description="호텔명으로 호텔을 예약합니다.")
def book_hotel(hotel_name: str) -> str:
    return f"{hotel_name} 숙박 예약이 완료되었습니다."

# 2) Worker Agents
flight_agent = create_agent(
    model="openai:gpt-5-mini",
    tools=[book_flight],
    system_prompt=(
        "당신은 항공편 예약 어시스턴트입니다.\n"
        "- 항공 관련 요청만 처리합니다.\n"
        "- 사용자가 출발/도착 공항을 이미 제공했다면 즉시 book_flight를 호출하세요.\n"
        "- book_flight에 필요한 정보는 from_airport, to_airport 뿐입니다.\n"
        "- 응답은 도구 실행 결과만 간결히 출력하세요."
    ),
    name="flight_agent",
)

hotel_agent = create_agent(
    model="openai:gpt-5-mini",
    tools=[book_hotel],
    system_prompt=(
        "당신은 호텔 예약 어시스턴트입니다.\n"
        "- 숙박 관련 요청만 처리합니다.\n"
        "- 사용자가 호텔 이름을 제공했다면 즉시 book_hotel 도구를 호출하세요.\n"
        "- book_hotel에 필요한 정보는 hotel_name 뿐입니다.\n"
        "- 응답은 도구 실행 결과만 간결히 출력하세요."
    ),
    name="hotel_agent",
)

# 3) Handoff Tools
handoff_to_flight = create_handoff_tool(
    agent_name="flight_agent",
    description="항공 작업을 flight_agent에게 이관합니다."
)

handoff_to_hotel = create_handoff_tool(
    agent_name="hotel_agent",
    description="숙박 작업을 hotel_agent에게 이관합니다."
)

# 4) Supervisor Agent
supervisor = create_agent(
    model="openai:gpt-5-mini",
    tools=[handoff_to_flight, handoff_to_hotel],
    system_prompt=(
        "당신은 항공/호텔 예약 팀의 슈퍼바이저입니다.\n"
        "- 항공 요청은 transfer_to_flight_agent로, 호텔 요청은 transfer_to_hotel_agent로 이관하세요.\n"
        "- 한 번에 한 에이전트만 이관합니다.\n"
        "- 추가 정보 요청을 만들지 말고, 사용자가 준 정보만으로 진행하세요.\n"
        "- 모든 작업이 끝나면 최종 요약만 말하고 종료하세요."
    ),
    name="supervisor",
)

# 5) Graph 구성 (Supervisor -> Worker -> Supervisor -> END)
supervisor_with_handoff = (
    StateGraph(MessagesState)
    .add_node("supervisor", supervisor)
    .add_node("flight_agent", flight_agent)
    .add_node("hotel_agent", hotel_agent)
    .add_edge(START, "supervisor")
    .add_edge("flight_agent", "supervisor")
    .add_edge("hotel_agent", "supervisor")
    .add_edge("supervisor", END)  # supervisor가 tool call 없이 마무리하면 종료
    .compile()
)
```

---

## 2. Supervisor with Agent as Tool 패턴
하위 에이전트를 독립된 노드로 구성해 전체 상태(`messages`)의 흐름을 넘겨받는 대신, 하위 에이전트 자체를 Supervisor의 **도구(Tool)** 로 묶어서 호출합니다. 
이 방식은 하위 에이전트에 **맥락의 격리(Context Isolation)** 를 보장하여 모델의 할루시네이션(환각) 방지 및 토큰 낭비 방지에 매우 효율적입니다. 또한, 실행과정의 내역을 제외한 최종 응답만 Supervisor에 전달될 수 있도록 파이프라인을 통제할 수 있습니다.

### 2.1. 구현 예시
```python
from langchain.tools import tool, ToolRuntime

# 1) 도메인 도구 및 워커 에이전트는 위 Handoff 예시와 동일하게 구현

# 2) Worker as Tool 
@tool("delegate_flight_agent", description="항공편 예약을 flight 워커에게 위임합니다.")
def delegate_flight_agent(from_airport: str, to_airport: str, runtime: ToolRuntime) -> str:
    # ToolRuntime을 이용하여 전체 대화 맥락이 아닌 원본 User message 및 원하는 정보만 추출
    original_user_message = next(
        m for m in reversed(runtime.state["messages"])
        if m.type == "human"
    )

    prompt = (
        "당신은 고객의 다음 요청을 지원합니다:\n\n"
        f"{original_user_message.text}\n\n"
        "고객의 출발지와 도착지는 각각 다음과 같습니다:\n\n"
        f"{from_airport}에서 {to_airport}로 이동"
    )

    result = flight_agent.invoke({"messages": [HumanMessage(content=prompt)]})

    # Final response passing 
    # - 전체 메세지 객체가 아닌 에이전트 처리 결과 중 핵심 텍스트만 Supervisor에게 Return
    return result["messages"][-1].content

@tool("delegate_hotel_agent", description="호텔 예약을 hotel 워커에게 위임합니다.")
def delegate_hotel_agent(hotel_name: str, runtime: ToolRuntime) -> str:
    original_user_message = next(
        m for m in reversed(runtime.state["messages"])
        if m.type == "human"
    )

    prompt = (
        "당신은 고객의 다음 요청을 지원합니다:\n\n"
        f"{original_user_message.text}\n\n"
        "고객이 예약하고자 하는 호텔입니다:\n\n"
        f"{hotel_name}에 예약을 원함"
    )

    result = hotel_agent.invoke({"messages": [HumanMessage(content=prompt)]})

    return result["messages"][-1].content

# 3) Supervisor Agent 구성
supervisor_with_tool_per_agent = create_agent(
    model="openai:gpt-5-mini",
    tools=[delegate_flight_agent, delegate_hotel_agent],
    # Supervisor는 Workflow 관장 역할로만 쓰임
    system_prompt=(
        "당신은 항공/호텔 예약 팀의 슈퍼바이저입니다.\n"
        "- 항공은 delegate_flight, 숙박은 delegate_hotel 도구를 사용해 작업을 위임하세요.\n"
        "- 항공권은 목적지와 도착지, 숙박은 호텔명만 있으면 예약이 가능합니다.\n"
        "- 직접 작업을 수행하지 마세요.\n"
        "- 한 번에 한 작업만 위임하세요."
    ),
    name="supervisor_with_tool_per_agent",
)
```

---

## 3. 에이전트 전환 방식 비교 요약

| 비교 항목 | **Handoff 방식** (Network/Relay) | **Agents as Tool 방식** (Supervisor/Subroutine) |
| :--- | :--- | :--- |
| **핵심 철학** | **"맥락의 공유" (Shared Context)**<br>모든 에이전트가 전체 대화 흐름을 파악하고 협력함. | **"맥락의 격리" (Context Isolation)**<br>필요한 정보만 선별하여 효율적이고 안전하게 작업함. |
| **데이터 전달 범위** | **전체 상태 (Full State)**<br>대화 기록 전체(`messages`)와 공유 데이터(`artifacts`)를 그대로 전달. | **선별된 인자 (Filtered Arguments)**<br>수행할 작업에 필요한 변수값만 추출하여 전달.<br>예: `{ "query": "ICN to PUS", "date": "2024-05-10" }` |
| **제어 흐름** | **단방향 이동 (Jump/Goto)**<br>A가 B를 호출하면 제어권이 B로 넘어감. | **왕복 호출 (Call & Return)**<br>관리자가 A를 호출하고, A의 결과값을 받아 다시 관리자가 판단함. |
| **토큰 효율성** | **낮음 (비용 증가)**<br>대화가 길어질수록 모든 에이전트가 읽어야 할 데이터(Input)가 계속 늘어남. | **높음 (비용 절감)**<br>하위 에이전트는 전체 대화를 몰라도 되므로 입력 토큰을 최소화할 수 있음. |
| **장점** | - **유연한 대화 흐름**: 상황에 따라 에이전트가 스스로 다음 담당자 결정.<br>- **협업 용이**: 이전 맥락을 모두 알기에 '눈치껏' 작업 가능.<br>- **HITL 용이**: 중간에 사람이 개입해도 맥락이 유지됨. | - **정확한 통제**: 관리자가 하위 에이전트의 입력을 완벽히 설계 가능.<br>- **보안 강화**: 하위 모델에 민감한 대화 내용 노출 방지.<br>- **모델 혼란 방지**: 불필요한 정보 제거로 할루시네이션 감소. |
| **단점** | - **정보 오염**: 이전 에이전트의 불필요한 사고 과정(Scratchpad)이 판단을 방해할 수 있음.<br>- **무한 루프**: 종료 조건이 명확하지 않으면 에이전트끼리 핑퐁할 위험. | - **관리자 병목**: 중앙 관리자(Supervisor)의 판단이 틀리면 전체가 실패함.<br>- **구현 복잡도**: 어떤 정보를 하위 에이전트로 넘길지 사전에 꼼꼼히 정의해야 함. |
| **비유** | **릴레이 달리기**: 릴레이 바통(전체 문맥)을 들고 다음 주자에게 넘겨줌. | **팀장과 팀원**: 팀장이 회의록을 보고, 팀원에게는 "엑셀만 정리해와"라고 쪽지를 줌. |
