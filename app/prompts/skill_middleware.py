"""Refresh skill discovery once per invocation, including for cached agents."""

import asyncio

from langchain.agents.middleware import AgentMiddleware, AgentState
from langchain_core.messages import SystemMessage
from typing_extensions import NotRequired

from .skill_builder import SkillPromptBuilder


class SkillCatalogState(AgentState):
    skill_catalog: NotRequired[str]


class SkillCatalogMiddleware(AgentMiddleware):
    state_schema = SkillCatalogState

    def __init__(self, builder: SkillPromptBuilder):
        self.builder = builder

    def before_agent(self, state, runtime):
        return {"skill_catalog": self.builder.assemble()}

    async def abefore_agent(self, state, runtime):
        return {"skill_catalog": await asyncio.to_thread(self.builder.assemble)}

    @staticmethod
    def _with_catalog(request):
        # This invocation's checkpointed snapshot is reused by model/tool loops
        # and interrupt/resume; the next invocation discovers new files.
        catalog = request.state.get("skill_catalog", "")
        if not catalog:
            return request
        message = request.system_message
        if message is None:
            message = SystemMessage(content=catalog)
        else:
            content = message.content
            content = f"{content}\n{catalog}" if isinstance(content, str) else [*content, {"type": "text", "text": catalog}]
            message = message.model_copy(update={"content": content})
        return request.override(system_message=message)

    def wrap_model_call(self, request, handler):
        return handler(self._with_catalog(request))

    async def awrap_model_call(self, request, handler):
        return await handler(self._with_catalog(request))
