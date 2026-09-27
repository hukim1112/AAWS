"""Regression coverage for discovery and refresh on a cached LangChain agent."""

import tempfile
import unittest
from pathlib import Path

from langchain.agents import create_agent
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command, interrupt
from pydantic import Field

from app.prompts.skill_builder import SkillPromptBuilder
from app.middleware import SkillCatalogMiddleware


def write_skill(root, name, description="A useful skill.", body="Read on demand."):
    path = root / name / "SKILL.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\nname: {name}\ndescription: {description}\n---\n{body}\n", encoding="utf-8")
    return path


class RecordingModel(BaseChatModel):
    responses: list[AIMessage]
    prompts: list[str] = Field(default_factory=list)

    @property
    def _llm_type(self):
        return "local-test-model"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self.prompts.append(messages[0].text)
        return ChatResult(generations=[ChatGeneration(message=self.responses[len(self.prompts) - 1])])

    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
        return self._generate(messages, stop, run_manager, **kwargs)


class SkillDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_multiline_yaml_and_nested_metadata(self):
        path = self.root / "SKILL.md"
        path.write_text('\ufeff---\nname: cursor-pagination\ndescription: |\n  Collect all cursor pages.\n  Detect repeated cursors.\nmetadata:\n  version: "1.0"\n---\nDetails.\n', encoding="utf-8")
        builder = SkillPromptBuilder([str(self.root)])
        metadata = builder._extract_frontmatter(str(path))
        self.assertEqual(metadata["metadata"], {"version": "1.0"})
        self.assertIn("Collect all cursor pages. Detect repeated cursors.", builder.build_catalog())

    def test_hub_flat_and_folder_skills_are_discoverable(self):
        (self.root / "SKILL.md").write_text("---\nname: hub\ndescription: Shared entrypoint.\n---\nHub body.")
        (self.root / "flat.md").write_text("# Flat skill\nLegacy description.")
        write_skill(self.root, "packaged")
        references = self.root / "packaged" / "references"
        references.mkdir()
        (references / "detail.md").write_text("# Not a skill entrypoint")
        catalog = SkillPromptBuilder([str(self.root), str(self.root)]).build_catalog()
        for name in ("hub", "Flat skill", "packaged"):
            self.assertEqual(catalog.count(f"**{name}**"), 1)
        self.assertNotIn("Not a skill entrypoint", catalog)

    def test_explicit_shared_guidelines_are_loaded_once(self):
        hub = self.root / "SKILL.md"
        hub.write_text("---\nname: hub\ndescription: Shared policy.\n---\nShared recovery instructions.")
        write_skill(self.root, "specific", body="Long instructions should be loaded on demand.")
        prompt = SkillPromptBuilder([str(self.root)], str(hub)).assemble()
        self.assertIn("Shared recovery instructions.", prompt)
        self.assertNotIn("**hub**", prompt)
        self.assertNotIn("Long instructions should be loaded on demand.", prompt)

    def test_invalid_metadata_is_skipped_without_hiding_valid_skills(self):
        write_skill(self.root, "valid")
        for name, content in {
            "bad-type.md": "---\nname: wrong\ndescription: [a, b]\n---\n",
            "unclosed.md": "---\nname: unfinished\ndescription: x\n",
            "unsafe.md": "---\n!!python/object:builtins.object {}\n---\n",
        }.items():
            (self.root / name).write_text(content)
        with self.assertLogs("app.prompts.skill_builder", level="WARNING"):
            catalog = SkillPromptBuilder([str(self.root)]).build_catalog()
        self.assertIn("**valid**", catalog)
        self.assertNotIn("**wrong**", catalog)
        self.assertNotIn("unfinished", catalog)

    def test_large_frontmatter_and_duplicate_names(self):
        path = write_skill(self.root, "long", description="x" * 2500)
        (self.root / "duplicate.md").write_text(path.read_text())
        with self.assertLogs("app.prompts.skill_builder", level="WARNING"):
            catalog = SkillPromptBuilder([str(self.root)]).build_catalog()
        self.assertEqual(catalog.count("**long**"), 1)
        self.assertIn("x" * 2500, catalog)

    def test_cached_sync_agent_discovers_additions_and_removals(self):
        first = write_skill(self.root, "first")
        model = RecordingModel(responses=[AIMessage(content="done") for _ in range(3)])
        agent = create_agent(model, system_prompt="Base policy", middleware=[SkillCatalogMiddleware(SkillPromptBuilder([str(self.root)]))], checkpointer=InMemorySaver())
        config = {"configurable": {"thread_id": "same-session"}}
        for change in (lambda: None, lambda: write_skill(self.root, "new-skill"), first.unlink):
            change()
            agent.invoke({"messages": [("user", "collect")]}, config)
        self.assertNotIn("**new-skill**", model.prompts[0])
        self.assertIn("**new-skill**", model.prompts[1])
        self.assertNotIn("**first**", model.prompts[2])
        self.assertTrue(all(p.startswith("Base policy") for p in model.prompts))


class SkillInvocationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        write_skill(self.root, "original")

    async def test_catalog_is_fixed_during_tool_loop_and_refreshed_next_invocation(self):
        @tool
        def register_skill() -> str:
            """Register a local fixture while an invocation is running."""
            write_skill(self.root, "added-during-run")
            return "registered"

        model = RecordingModel(responses=[
            AIMessage(content="", tool_calls=[{"name": "register_skill", "args": {}, "id": "register"}]),
            AIMessage(content="finished"), AIMessage(content="next"),
        ])
        agent = create_agent(model, tools=[register_skill], system_prompt="Base policy", middleware=[SkillCatalogMiddleware(SkillPromptBuilder([str(self.root)]))], checkpointer=InMemorySaver())
        config = {"configurable": {"thread_id": "cached"}}
        await agent.ainvoke({"messages": [("user", "start")]}, config)
        await agent.ainvoke({"messages": [("user", "again")]}, config)
        self.assertEqual(model.prompts[0], model.prompts[1])
        self.assertNotIn("**added-during-run**", model.prompts[1])
        self.assertIn("**added-during-run**", model.prompts[2])

    async def test_interrupt_resume_preserves_catalog_snapshot(self):
        @tool
        def pause_for_fixture() -> str:
            """Pause to check catalog consistency across a checkpoint."""
            return interrupt("continue?")

        model = RecordingModel(responses=[
            AIMessage(content="", tool_calls=[{"name": "pause_for_fixture", "args": {}, "id": "pause"}]),
            AIMessage(content="resumed"), AIMessage(content="new invocation"),
        ])
        agent = create_agent(model, tools=[pause_for_fixture], system_prompt="Base policy", middleware=[SkillCatalogMiddleware(SkillPromptBuilder([str(self.root)]))], checkpointer=InMemorySaver())
        config = {"configurable": {"thread_id": "interrupt"}}
        state = await agent.ainvoke({"messages": [("user", "start")]}, config)
        self.assertTrue(state["__interrupt__"])
        write_skill(self.root, "added-while-paused")
        await agent.ainvoke(Command(resume="continue"), config)
        self.assertEqual(model.prompts[0], model.prompts[1])
        await agent.ainvoke({"messages": [("user", "next")]}, config)
        self.assertIn("**added-while-paused**", model.prompts[2])
