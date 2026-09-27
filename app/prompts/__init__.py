from .skill_builder import SkillPromptBuilder

__all__ = [
    "SkillPromptBuilder",
]


def __getattr__(name: str):
    """하위 호환성을 위한 동적 프롬프트 로딩 (순환 참조 방지)"""
    if name == "CHATBOT_SYSTEM_PROMPT":
        from app.agents.chatbot import CHATBOT_SYSTEM_PROMPT
        return CHATBOT_SYSTEM_PROMPT
    elif name == "SCRAPER_SYSTEM_PROMPT":
        from app.agents.scraper.prompt import SCRAPER_SYSTEM_PROMPT
        return SCRAPER_SYSTEM_PROMPT
    elif name == "SUPERVISOR_SYSTEM_PROMPT":
        from app.agents.supervisor.prompt import SUPERVISOR_SYSTEM_PROMPT
        return SUPERVISOR_SYSTEM_PROMPT
    elif name == "ANALYST_SYSTEM_PROMPT":
        from app.agents.analyst.prompt import ANALYST_SYSTEM_PROMPT
        return ANALYST_SYSTEM_PROMPT
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
