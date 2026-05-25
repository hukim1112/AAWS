---
trigger: manual
---

주요 맥락 정보는 docs/LangChain 폴더 내에 있습니다.
모든 파일을 보지말고 현재 작업 수행에 필요한 컨텍스트를 가지고 있는 파일만 분석하십시오.

[LangChain 하위 작업 맥락]

docs/LangChain 폴더 내 LangChain 모듈 구성에 대한 instruction이 있습니다.

1. tool_declaration.md : LangChain에서 커스텀 도구(Tool)를 선언하고 구성할 때 봐야 할 맥락입니다.
2. create_agent.md : 기본 에이전트를 선언할 때 (예: system prompt 설정, model binding 등) 참고해야 하는 문서입니다.
3. runtime.md : ToolRuntime 등 런타임 단계에서 동적인 상태 전환 및 외부 상태 관리가 필요할 때 참고하는 문서입니다.
4. middleware.md : call_agent_middleware를 포함하여 에이전트 호출 중간 과정에 개입하는 커스텀 미들웨어 구현 시 살펴봐야 할 구조 문서입니다.
5. human_in_the_loop.md : LangGraph를 활용한 Human-in-the-Loop(HITL) 워크플로우 구성, 사용자 승인 절차를 설계할 때 봐야 할 가이드입니다.
6. multi_agent_patterns.md : Handoffs 방식과 Agent as Tool 방식의 다중 에이전트 시스템 패턴 비교와 구현 코드가 있는 문서입니다.
7. mcp_integration.md : MCP(Model Context Protocol) 클라이언트/서버 연결, FastMCP, 그리고 LangChain-MCP 통합이 필요할 때 참고하는 문서입니다.
