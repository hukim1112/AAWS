# LangChain `create_agent` 핵심 문법 가이드

`create_agent`를 활용하여 런타임 상태(Context)를 주입하고 메모리(Store)를 다루는 확장형 에이전트 구성 방법입니다.

## 1. Context 스키마 & 모델 준비
런타임에 주입될 데이터(Context) 스키마를 정의하고 언어 모델을 초기화합니다.
```python
from dataclasses import dataclass
from langchain.chat_models import init_chat_model

@dataclass
class Context:
    user_id: str

model = init_chat_model("google_genai:gemini-2.5-flash", temperature=0.1)
```

## 2. Tool & Store 접근
`ToolRuntime[Context]`를 통해 주입된 `Context`와 `Store`에 안전하게 접근합니다.
```python
from langchain.tools import tool, ToolRuntime
from typing_extensions import TypedDict

class UserInfo(TypedDict):
    name: str; hobby: list; occupation: list

@tool
def get_user_info(runtime: ToolRuntime[Context]) -> str:
    """사용자 정보를 조회합니다."""
    # 1. Context 활용: 런타임에 주입된 user_id 접근
    user_id = runtime.context.user_id
    
    # 2. Store 활용: 데이터 조회
    if not runtime.store or not (store := runtime.store.get("structured")):
        return "데이터 없음"
    
    memory = store.get(("user_info",), user_id)
    return memory.value if memory and hasattr(memory, "value") else (memory or "데이터 없음")

@tool
def save_user_info(user_info: UserInfo, runtime: ToolRuntime[Context]) -> str:
    """사용자 정보를 저장합니다."""
    if not runtime.store: return "Store 오류"
    # 3. Store에 데이터 저장 (namespace, key, value)
    try:
        runtime.store["structured"].put(("user_info",), runtime.context.user_id, user_info)
        return "저장 성공"
    except Exception as e:
        return f"저장 실패: {e}"
```

## 3. 에이전트 생성 (`create_agent`)
정의한 구성요소들과 Store/Checkpointer를 연결하여 통합 에이전트를 선언합니다.
*(선택) 출력 포맷을 고정하려면 `ToolStrategy`를 사용합니다.*
```python
from langchain.agents import create_agent
from langgraph.store.memory import InMemoryStore
from langgraph.checkpoint.memory import InMemorySaver
from langchain.agents.structured_output import ToolStrategy # (선택) 구조화된 출력

@dataclass
class OutputSchema:
    analysis: str; advisory: str # (선택) 원하는 출력 구조 정의

store, checkpointer = InMemoryStore(), InMemorySaver()
SYSTEM_PROMPT = "당신은 기상 분석 에이전트입니다. 조건에 따라 행동하세요."

agent = create_agent(
    model=model,
    system_prompt=SYSTEM_PROMPT,
    context_schema=Context,                # 런타임 주입 스키마
    tools=[get_user_info, save_user_info], # 사용할 도구 목록
    store=store,                           # 영구/구조화 저장소
    checkpointer=checkpointer,             # 대화 이력 추적기 (스레드 관리)
    # response_format=ToolStrategy(OutputSchema) # (선택) 지정된 딕셔너리/클래스 형태로 응답 강제
)
```

## 4. 에이전트 실행 (`invoke`)
설정한 `config`(세션 고유값)와 `context`(런타임 주입 데이터)를 넘기며 에이전트를 호출합니다.
```python
from langchain_core.messages import HumanMessage

# 세션/스레드 식별자
config = {"configurable": {"thread_id": "thread_1"}}
# 주입할 컨텍스트 데이터
context = Context(user_id="user_123")

# 에이전트 실행
response = agent.invoke(
    {"messages": [HumanMessage("새로운 취미 정보를 기록해줘.")]},
    config=config,
    context=context
)

# ----------------- 결과 출력 -----------------
# 1) 일반 메시지 형태 출력
for m in response.get('messages', []): 
    m.pretty_print()

# 2) 구조화(ToolStrategy) 응답 출력 시
# print(response["structured_response"])
```
