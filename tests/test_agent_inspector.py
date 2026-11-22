import importlib
import tempfile
import unittest
from pathlib import Path

import aiosqlite
from langchain.agents import create_agent
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.tools import tool
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app.context import AgentContext
from app.middleware import AgentLogTracer, SkillCatalogMiddleware
from app.prompts.skill_builder import SkillPromptBuilder
from tests.agent_inspector import (
    close_agent_resources,
    extract_agent_middlewares,
    extract_agent_tools,
    find_agent_middleware,
)


class _DummyChatModel(BaseChatModel):
    @property
    def _llm_type(self) -> str:
        return "dummy-inspector"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content="ok"))])


class AgentInspectorTests(unittest.IsolatedAsyncioTestCase):
    async def test_extract_tools_middlewares_and_close_resources(self):
        """CompiledStateGraph에서 도구, 노드형/래퍼형 미들웨어, DB 커넥션을 정확히 추출/종료하는지 검증."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            conn = await aiosqlite.connect(str(root / "cp.db"), check_same_thread=False)
            cp = AsyncSqliteSaver(conn)
            await cp.setup()

            @tool
            def sample_ping(x: str) -> str:
                """핑 도구."""
                return x

            tracer = AgentLogTracer(disk_enabled=False)
            skill_mw = SkillCatalogMiddleware(SkillPromptBuilder([str(root)]))

            agent = create_agent(
                model=_DummyChatModel(),
                tools=[sample_ping],
                middleware=[tracer, skill_mw],
                checkpointer=cp,
                context_schema=AgentContext,
            )

            tools = extract_agent_tools(agent)
            self.assertEqual([t.name for t in tools], ["sample_ping"])

            mws = extract_agent_middlewares(agent)
            mw_types = {type(m) for m in mws}
            self.assertIn(AgentLogTracer, mw_types)
            self.assertIn(SkillCatalogMiddleware, mw_types)

            self.assertIs(find_agent_middleware(agent, AgentLogTracer), tracer)
            self.assertIs(find_agent_middleware(agent, SkillCatalogMiddleware), skill_mw)
            self.assertIsNone(extract_agent_middlewares(None) or None)

            self.assertTrue(getattr(conn, "_running", False))
            await close_agent_resources(agent)
            self.assertFalse(getattr(conn, "_running", True))

            # 이미 닫힌 커넥션에 대해 재호출해도 안전(idempotent)해야 함
            await close_agent_resources(agent)

    async def test_subagent_and_chatbot_factories_have_no_monkeypatched_attributes(self):
        """에이전트 팩토리 반환값에 테스트용 수동 속성들이 붙어 있지 않고 인트로스펙션으로 조회 가능한지 검증."""
        forbidden_attrs = (
            "registered_tools",
            "registered_middlewares",
            "checkpointer_conn",
            "assembler",
            "log_tracer",
        )

        target_specs = [("app.agents.chatbot", False), ("app.agents.scraper.agent", True)]
        for mod_name in ("app.agents.analyst.agent", "app.agents.supervisor.agent"):
            try:
                mod = importlib.import_module(mod_name)
                if callable(getattr(mod, "create_agent_executor", None)):
                    target_specs.append((mod_name, True))
            except ImportError:
                pass

        with tempfile.TemporaryDirectory() as tmpdir:
            conn = await aiosqlite.connect(str(Path(tmpdir) / "shared_cp.db"), check_same_thread=False)
            try:
                cp = AsyncSqliteSaver(conn)
                await cp.setup()

                for mod_name, expects_tracer in target_specs:
                    mod = importlib.import_module(mod_name)
                    exec_obj = await mod.create_agent_executor(checkpointer=cp)
                    for attr in forbidden_attrs:
                        self.assertFalse(
                            hasattr(exec_obj, attr),
                            f"Unexpected monkey-patched attribute '{attr}' on {mod_name}",
                        )
                    self.assertGreater(len(extract_agent_tools(exec_obj)), 0)
                    if expects_tracer:
                        self.assertIsNotNone(find_agent_middleware(exec_obj, AgentLogTracer))
            finally:
                if getattr(conn, "_running", False):
                    await conn.close()


if __name__ == "__main__":
    unittest.main()
