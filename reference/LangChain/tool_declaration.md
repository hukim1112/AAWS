# LangChain `@tool` 선언 핵심 가이드 (v2)

LangChain에서 도구(Tool)를 가장 쉽고 명확하게 선언하는 방법은 파이썬 함수에 `@tool` 데코레이터를 사용하는 것입니다. v2에서는 비동기 처리와 모범 사례(에러 핸들링)를 추가로 강조합니다.

특히 `parse_docstring=True` 옵션을 활용하면, 파이썬 Docstring(Google 스타일 등)을 파싱하여 **도구의 설명(Description)**과 **인자들의 JSON 스키마(Args)**를 LLM이 이해하기 쉬운 형태로 자동 변환해 줍니다. 이는 LLM이 도구를 올바르게 사용하도록 돕는 매우 중요한 정보가 됩니다.

## 1. `@tool(parse_docstring=True)` 사용 문법

도구를 선언할 때는 **함수 시그니처(타입 힌트 필수)**와 **Docstring(설명 및 인자 정의)**을 명확하게 작성해야 합니다. I/O 작업(예: DB 조회, API 호출)이 포함된 경우 비동기 함수(`async def`) 사용을 적극 권장합니다.

```python
from langchain.tools import tool
from typing import Optional

# parse_docstring=True 옵션을 통해 Docstring 구성을 파싱합니다.
@tool(parse_docstring=True)
async def search_database(query: str, limit: int = 10, filter_type: Optional[str] = None) -> str:
    """Search the customer database for records matching the query.

    # 1. 함수의 반환 값이나 동작에 대한 전체적인 설명이 도구의 메인 Description이 됩니다.
    # LLM은 이 설명을 읽고 언제 이 도구를 써야 할지 결정합니다.

    Args:
        query: Search terms to look for (e.g., customer name).
        limit: Maximum number of results to return. Default is 10.
        filter_type: Optional filter by customer type (e.g., 'VIP', 'Regular').
    """
    try:
        # 실제 비동기 DB 조회 로직이 위치하는 곳
        return f"Found {limit} results for '{query}' with filter '{filter_type}'"
    except Exception as e:
        # 에러 발생 시 LLM이 스스로 원인을 파악할 수 있도록 친절한 에러 메시지를 반환합니다.
        return f"데이터베이스 조회 중 오류가 발생했습니다: {str(e)}"
```

## 2. 런타임 상태(Context) 주입 활용하기

이전에 정의한 `Context`(런타임 주입 컨텍스트)를 활용해야 할 경우, 파라미터로 `runtime: ToolRuntime[Context]`를 함께 선언합니다. 이 매개변수는 LLM에게는 노출되지 않으며 실행 시 프레임워크가 자동으로 주입합니다.

```python
from dataclasses import dataclass
from langchain.tools import tool, ToolRuntime

@dataclass
class Context:
    user_id: str

@tool
def get_user_profile(runtime: ToolRuntime[Context]) -> str:
    """현재 로그인한 사용자의 프로필을 조회합니다."""
    user_id = runtime.context.user_id
    return f"사용자 ID {user_id}의 프로필 정보 조회를 성공했습니다."
```

## 3. 내부 검증 및 스키마 확인 (디버깅)

내부적으로 생성된 Tool 객체의 속성들을 검증하여 프롬프트로 전환될 정보를 미리 확인할 수 있습니다.

```python
if __name__ == "__main__":
    print("Tool Name:", search_database.name)
    print("Description:", search_database.description)
    print("JSON Schema:", search_database.args)
```

## ✅ 핵심 모범 사례 (Best Practices)

1. **명시적인 타입 힌트(Type Hints)**: LLM이 인수 타입을 혼동하지 않도록 명확한 타입을 제공하세요.
2. **프롬프트 관점의 Docstring 작성**: 단순히 코드를 위한 주석이 아니라, "LLM에게 도구 사용법을 가르치는 지시문"이라고 생각하고 작성하세요.
3. **Graceful Error Handling**: 에러가 발생해도 파이썬 앱이 멈추지 않고 예외가 반환되게 하면, LLM이 이를 인지하고 인수를 수정하여 도구를 다시 호출할 수 있습니다.
