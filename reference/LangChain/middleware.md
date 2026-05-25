# LangChain Middleware (에이전트 실행 흐름 제어)

에이전트의 모델 호출(`model_call`)이나 도구 호출(`tool_call`) 전후 과정, 또는 실행 흐름을 **가로채서(intercept)** 변경하거나 로깅하는 등 추가 로직을 삽입하는 기능을 **Middleware(미들웨어)**라고 합니다.
이를 통해 에이전트의 실제 비즈니스 로직(Agent 핵심)을 수정하지 않고도 부가 기능을 확장할 수 있습니다.

## 1. Built-In Middleware (기본 제공 미들웨어)

LangChain 라이브러리에는 자주 사용되는 미들웨어가 내장되어 있습니다. 에이전트 생성 시 `middleware=[...]` 배열에 등록해서 사용합니다.

**대표적인 미들웨어 예시**
- **`PIIMiddleware`**: 민감 정보(이메일, 카드번호, API 키 등)를 마스킹(`mask`), 삭제(`redact`)하거나 오류 발생(`block`) 처리 시켜 데이터 유출을 방지.
- **`SummarizationMiddleware`**: 에이전트 메시지 이력이 길어져 대화 토큰 한도에 근접하면(`trigger` 기반) 오래된 기록을 작은 개수로(`keep` 기반) 요약하여 관리.

```python
from langchain.agents import create_agent
from langchain.agents.middleware import PIIMiddleware, SummarizationMiddleware

agent = create_agent(
    model="gpt-4",
    tools=[],
    middleware=[
        # 이메일 Redact 설정
        PIIMiddleware("email", strategy="redact", apply_to_input=True),
        # 메시지 히스토리 요약 설정
        SummarizationMiddleware(
            model="gpt-3.5-turbo",
            trigger=("tokens", 4000),  # 전체 Context Token이 4000 초과 시 트리거 
            keep=("messages", 20),     # 최신 20개 메시지는 요약하지 않고 보존
        ),
    ]
)
```

## 2. Custom Middleware (사용자 정의 미들웨어)
특별한 제어가 필요한 경우 미들웨어를 직접 만들 수 있습니다.

### (1) Node-style Hooks
실행 흐름을 관찰(Observation)하거나 단순 수정하는 목적입니다. (흐름 자체를 가로막진 않음)
- `@before_agent`, `@after_agent`, `@before_model`, `@after_model` 데코레이터를 사용합니다.

```python
from langchain.agents.middleware import before_model

@before_model
def log_before_model(state, runtime) -> dict | None:
    """모델이 호출되기 직전에 로그를 남기거나 state를 일부 변경합니다."""
    user_name = runtime.context.user_name
    print(f"[{user_name}]님의 요청을 모델에 넘깁니다.")
    return None # Return 값으로 dict를 반환하면 state 수정 가능 
```

### (2) Wrap-style Hooks
실행 흐름을 직접 가로채서(Intercept) 핸들러 호출을 조건부로 제한, 변경, 또는 재시도하게 만듭니다. 
- `@wrap_model_call`, `@wrap_tool_call` 데코레이터를 사용합니다.

```python
from langchain.agents.middleware import wrap_model_call
from langchain.chat_models import init_chat_model

# 조건에 따라 호출할 모델을 동적으로 통제
@wrap_model_call
def dynamic_model_selection(request, handler):
    """대화 길이가 길어지면 더 큰 모델(complex_model)로 스위칭"""
    complex_model = init_chat_model("gpt-4o", temperature=0.1)
    
    # 딕셔너리 길이나 토큰 크기에 따라 분기 처리 
    if len(request.state["messages"]) > 10:
        return handler(request.override(model=complex_model))
    
    # 원래 설정된 base_model 로직 그대로 실행 
    return handler(request)
```

```python
from langchain.agents.middleware import wrap_tool_call
from langchain_core.messages import ToolMessage

# 도구 호출 방어 (예: 비밀번호 검사)
@wrap_tool_call
def security_tool_checker(request, handler):
    # Context 내 주입된 Password 검증
    if request.runtime.context.password != "MY_SECRET_KEY":
        # 아예 함수 핸들러 호출을 하지 않고 (취소), 툴 실행 취소 메시지 구조로만 반환함
        return ToolMessage(
            tool_call_id=request.tool_call.get("id"),
            content="Error: Wrong Password."
        )
        
    return handler(request)
```

### 3. Agent 연동

만든 커스텀 훅을 배열로 넣어줍니다.

```python
agent = create_agent(
    model="gpt-4o-mini",
    tools=[my_adding_tool, my_deleting_tool],
    middleware=[log_before_model, dynamic_model_selection, security_tool_checker],
    context_schema=Context
)
```
