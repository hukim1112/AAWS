# MCP (Model Context Protocol) Integration in LangChain

**MCP(Model Context Protocol)**은 AI 모델과 외부 도구(Tool), 데이터 소스, 서비스를 표준화된 방식으로 연결하는 오픈 프로토콜입니다. 
이를 통해 LangChain 에이전트나 독립된 프로세스가 외부 데이터베이스, 로컬 환경, 혹은 엔터프라이즈 시스템과 안전하고 일관된 방식으로 통신할 수 있습니다.

---

## 1. FastMCP를 이용한 서버 실행
Python 기반 프레임워크인 **FastMCP**를 활용하면 손쉽게 데코레이터 패턴으로 MCP 서버의 도구를 정의하고 구동할 수 있습니다.
다음은 Python 내에서 백그라운드로 MCP 서버를 띄우는 예시입니다.

```python
import os, socket

# 가용 포트 탐색 (포트 충돌 방지)
def find_available_port(start=5000, end=7000):
    for port in range(start, end):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("0.0.0.0", port))
                return port
            except OSError:
                continue
    raise RuntimeError("사용 가능한 포트를 찾지 못했습니다.")

MCP_PORT = find_available_port(6000, 6500)
server_path = os.path.join("mcp_servers", "basic_mcp_server.py")
log_path = os.path.join("mcp_servers", "basic_mcp_server.log")

# 리눅스 환경 기준 nohup을 사용하여 프로세스를 백그라운드로 유지
cmd = f"nohup python -u {server_path} --port {MCP_PORT} > {log_path} 2>&1 &"
os.system(cmd)
```

---

## 2. MCP 클라이언트 연결 및 도구 탐색
`fastmcp` 모듈에서 제공하는 `Client` 객체를 통해 구동 중인 MCP 서버에 접근하고, 서버가 노출하는 기능을 확인할 수 있습니다.

```python
import asyncio
from fastmcp import Client

client = Client(f"http://localhost:{MCP_PORT}/mcp")

async def test_mcp_client():
    async with client:
        # 1) 서버 연결 확인
        ping_response = await client.ping()
        print("ping 반환:", ping_response)

        # 2) 사용 가능한 도구(Tool) 목록 조회 (Tool Discovery)
        tools = await client.list_tools()
        for tool in tools:
            print(tool)
            
        # 3) 특정 도구 수동 실행 (직접 호출)
        response = await client.call_tool("greet", {"name": "Ford"})
        print(response)

# asyncio.run(test_mcp_client())
```

---

## 3. LangChain 환경과의 통합 (LangChain MCP Adapters)
`langchain-mcp-adapters` 라이브러리는 구동 중인 다양한 대상 MCP 서버들을 LangGraph 등 LangChain 기반 에이전트에 쉽게 결합하도록 돕는 유틸리티입니다. 여러 MCP 서버를 통합하여 하나의 도구 목록으로 구성하고 LLM이 능동적으로 호출할 수 있습니다.

### 패키지 설치
```bash
pip install langchain-mcp-adapters
```

### 멀티 서버 연결 어댑터 (MultiServerMCPClient)
여러 MCP 서버(예를 들면, 시스템 제어용 서버와 금융 정보 수집용 서버)를 매핑하여 통합 클라이언트를 정의합니다.
```python
from langchain_mcp_adapters.client import MultiServerMCPClient

langgraph_client = MultiServerMCPClient(
    {
        "fastmcp-tool-demo": {
            "transport": "streamable_http",     # HTTP 스트리밍 방식 구동
            "url": "http://localhost:6001/mcp/" # 첫 번째 서버
        },
        "FinanceTools": {
            "transport": "streamable_http",  
            "url": "http://localhost:6002/mcp/" # 두 번째 금융 MCP 서버
        },
    }
)
```

### Agent에 MCP Tools와 Langchain 내장 도구 결합하기
외부 원격의 서버 툴(`mcp_tools`)과 LangChain 내장 로컬 툴킷을 결합한 통합 에이전트를 구성합니다.
```python
from langchain.agents import create_agent
from langchain_community.agent_toolkits import FileManagementToolkit
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage

async def run_finance_agent():
    # 1) 접속된 모든 MCP 서버의 도구 리스트 가져오기
    mcp_tools = await langgraph_client.get_tools()
    
    # 2) Langchain 로컬 도구 로드
    fmtools = FileManagementToolkit(root_dir="./sandbox").get_tools()
    
    # 3) 도구 리스트 병합
    tools = mcp_tools + fmtools
    
    system_prompt = """당신은 금융 데이터 분석 에이전트입니다. 사용자가 특정 종목(티커)에 대해 묻거나 최근 뉴스를 요청하면 MCP 서버의 도구(stock_data, web_scraper)를 활용하세요.
    응답 시 다음 규칙을 따르세요:
    1. 수치는 명확하게 단위(USD, %)를 표시합니다.
    2. 변동률은 상승/하락 여부를 명확히 적습니다.
    3. 뉴스를 인용할 때는 제목과 링크를 함께 제공합니다.
    4. 투자 조언은 하지 말고, 데이터 기반 사실만 전달하세요."""
    
    # 4) LLM 객체 설정
    llm = ChatOpenAI(model="gpt-4o")
    
    # 5) 에이전트 생성
    finance_agent = create_agent(
        system_prompt=system_prompt,
        model=llm.bind_tools(tools, parallel_tool_calls=False),
        tools=tools,
        checkpointer=MemorySaver()
    )
    
    # 6) 에이전트 실행 유발
    query = "애플(AAPL)과 엔비디아(NVDA)의 현재 주가와 최근 뉴스 요약해줘."
    response = await finance_agent.ainvoke(
        {"messages": [HumanMessage(content=query)]},
        config={"configurable": {"thread_id": "1"}}
    )
    
    # 도구 호출(Tool Call) 결과 포함 응답 출력
    for message in response['messages']:
        message.pretty_print()
```

## 핵심 요약
- **독립성 강화**: MCP 서버를 구현하여 배포하면 LangChain이나 특정 AI 프레임워크와 무관하게 모든 에이전트 시스템에서 해당 기능을 재사용할 수 있습니다.
- **보안성(격리)**: 외부 API 키들이 애플리케이션 코드가 아닌 개별 독립 서버에 적재되어, 중앙 애플리케이션 엔진과 물리적/논리적으로 분리 관리가 가능합니다.
- **통합의 최소화**: 여러 복잡한 패키지를 하나의 가상환경에 밀어넣을 필요 없이, HTTP/WebSocket 등의 표준 프로토콜로 도구를 넘겨주는 방식을 채택합니다.
