"""
Supervisor Agent Package (Trainee Mission 03 & 04)
===============================================================================
본 패키지는 Mission 03 및 Mission 04 실습 대상 패키지입니다.
- agent.py: create_agent_executor 에이전트 조립 팩토리 (TODO)
- prompt.py: SUPERVISOR_SYSTEM_PROMPT 시스템 프롬프트 (TODO)
- tools.py: invoke_sub_agent 도구 구현 및 tools_supervisor 바인딩 (TODO)
===============================================================================
"""

from .agent import AGENT_METADATA

try:
    from .agent import create_agent_executor
    __all__ = ["create_agent_executor", "AGENT_METADATA"]
except ImportError:
    __all__ = ["AGENT_METADATA"]
