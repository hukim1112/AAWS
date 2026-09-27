"""Local Chromium/CDP regression tests; enable with RUN_BROWSER_TESTS=1.

No external websites or model API calls are needed. browser-use's actual
BrowserSession is used, with only its LLM/Agent run replaced by local actions.
"""

import asyncio
import json
import os
import socket
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from aiohttp import web

from app.tools import navigator


HTML = """<!doctype html><html><head><title>Local collection fixture</title></head>
<body><input id="term"><button id="add" onclick="appendItem()">Add item</button>
<button id="record" onclick="recorded.push(document.querySelector('#term').value)">Record</button>
<ul id="items"></ul><div style="height:4000px">Scroll fixture</div>
<script>
let recorded = [];
let count = 0;
function appendItem() {
  const item = document.createElement('li');
  item.className = 'item'; item.textContent = 'item-' + (++count);
  document.querySelector('#items').append(item);
}
for (let i=0; i<12; i++) appendItem();
sessionStorage.loads = String(Number(sessionStorage.loads || 0) + 1);
</script></body></html>"""


@unittest.skipUnless(os.environ.get("RUN_BROWSER_TESTS") == "1", "Set RUN_BROWSER_TESTS=1 for local Chromium/CDP tests")
class SharedBrowserTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="navigator-test-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.env = patch.dict(os.environ, {
            "HEADLESS": "true", "ANONYMIZED_TELEMETRY": "false",
            "BROWSER_USE_CLOUD_SYNC": "false", "BROWSER_USE_LOGGING_LEVEL": "error",
            "BROWSER_USE_CONFIG_DIR": str(self.root / "browser-use"),
            "LANGSMITH_TRACING": "false", "LANGCHAIN_TRACING_V2": "false",
        })
        self.env.start()
        self.addCleanup(self.env.stop)
        app = web.Application()

        async def fixture(request):
            return web.Response(text=HTML, content_type="text/html")

        app.router.add_get("/{tail:.*}", fixture)
        self.server = web.AppRunner(app)
        await self.server.setup()
        self.addAsyncCleanup(self.server.cleanup)
        site = web.TCPSite(self.server, "127.0.0.1", 0)
        await site.start()
        port = site._server.sockets[0].getsockname()[1]
        self.url = f"http://127.0.0.1:{port}/"

        self.manager = navigator.PlaywrightManager()
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            self.manager._cdp_port = sock.getsockname()[1]
        self.instance = patch.object(navigator.PlaywrightManager, "_instance", self.manager)
        self.instance.start()
        self.addCleanup(self.instance.stop)
        self.addAsyncCleanup(self.manager.close)
        self.screenshots = patch.object(navigator, "SCREENSHOT_DIR", str(self.root / "screenshots"))
        self.screenshots.start()
        self.addCleanup(self.screenshots.stop)
        self.page = await self.manager.get_page(self.url, wait_ms=0)

    async def test_interaction_survives_analysis_verification_and_screenshot(self):
        result = await navigator.interact_page.ainvoke({
            "url": self.url,
            "actions_json": json.dumps([
                {"action": "fill", "selector": "#term", "value": "preserved"},
                {"action": "click", "selector": "#add"},
                {"action": "scroll", "direction": "down", "amount": 650},
            ]), "wait_ms": 0,
        })
        self.assertNotIn("[Error]", result)
        await self.page.wait_for_function("window.scrollY > 0")
        scroll = await self.page.evaluate("scrollY")
        loads = await self.page.evaluate("sessionStorage.loads")
        skeleton = await navigator.extract_dom_skeleton.ainvoke({"root_selector": "#items", "wait_ms": 0})
        section = await navigator.get_page_section.ainvoke({"root_selector": "#items", "wait_ms": 0})
        self.assertIn("×13", skeleton)
        self.assertIn("item-13", section)
        self.assertIn(self.url, skeleton)
        self.assertIn(self.url, section)
        verification = await navigator.verify_selectors.ainvoke({"selectors_json": '{"items":".item"}', "max_samples": 3, "wait_ms": 0})
        self.assertIn("매칭 13건 (샘플 3건)", verification)
        screenshot = await navigator.take_screenshot.ainvoke({"filename": "preserved"})
        self.assertNotIn("[Error]", screenshot)
        self.assertTrue((self.root / "screenshots/preserved.png").is_file())
        self.assertIs(await self.manager.get_page(self.url.rstrip("/"), wait_ms=0), self.page)
        self.assertEqual(await self.page.locator("#term").input_value(), "preserved")
        self.assertEqual(await self.page.evaluate("sessionStorage.loads"), loads)
        self.assertEqual(await self.page.evaluate("scrollY"), scroll)
        self.assertEqual(len(self.page.context.pages), 1)

    async def test_explicit_reload_navigation_and_closed_tab_recovery(self):
        await self.page.locator("#term").fill("keep until reload")
        result = await navigator.verify_selectors.ainvoke({"selectors_json": '{"bad":"["}', "wait_ms": 0})
        self.assertIn("[Error]", result)
        self.assertFalse(self.page.is_closed())
        self.assertEqual(await self.page.locator("#term").input_value(), "keep until reload")
        await navigator.get_page_section.ainvoke({"root_selector": "#items", "reload": True, "wait_ms": 0})
        self.assertEqual(await self.page.locator("#term").input_value(), "")
        self.assertEqual(await self.page.evaluate("sessionStorage.loads"), "2")
        self.assertIs(await self.manager.get_page(self.url + "other", wait_ms=0), self.page)
        self.assertEqual(self.page.url, self.url + "other")
        await self.page.close()
        replacement = await self.manager.get_page(self.url, wait_ms=0)
        self.assertFalse(replacement.is_closed())
        self.assertIsNot(replacement, self.page)

    async def test_concurrent_interaction_sequences_do_not_interleave(self):
        async def record(value):
            return await navigator.interact_page.ainvoke({"actions_json": json.dumps([
                {"action": "fill", "selector": "#term", "value": value},
                {"action": "click", "selector": "#record"},
            ]), "wait_ms": 0})
        outputs = await asyncio.gather(record("alpha"), record("beta"))
        self.assertTrue(all("[Error]" not in r for r in outputs))
        self.assertEqual(await self.page.evaluate("recorded"), ["alpha", "beta"])

    async def test_cdp_reconnect_recovers_same_tab_and_document(self):
        await self.page.locator("#term").fill("survives-reconnect")
        target_id = await self.manager.page_target_id(self.page)
        await self.manager._playwright.stop()
        restored = await self.manager.get_page(wait_ms=0)
        self.assertEqual(await self.manager.page_target_id(restored), target_id)
        self.assertEqual(await restored.locator("#term").input_value(), "survives-reconnect")
        self.assertEqual(await restored.evaluate("sessionStorage.loads"), "1")

    async def test_browser_use_handoff_tracks_tab_identity_on_success_and_failure(self):
        from browser_use import BrowserSession
        from browser_use.browser.events import SwitchTabEvent

        other = await self.page.context.new_page()
        await other.goto(self.url)
        original_id = await self.manager.page_target_id(self.page)
        other_id = await self.manager.page_target_id(other)
        await self.manager.adopt_target(original_id)
        await self.page.locator("#term").fill("before-browser-use")
        test = self
        sessions = []

        def make_session(**kwargs):
            session = BrowserSession(**kwargs, enable_default_extensions=False, downloads_path=str(self.root / "downloads"))
            sessions.append(session)
            return session

        class History:
            def __len__(self): return 1
            def is_successful(self): return True
            def urls(self): return [test.url]
            def final_result(self): return "local browser-use action complete"

        class LocalAgent:
            def __init__(self, browser_session, **kwargs):
                self.session = browser_session

            async def run(self, max_steps):
                test.assertEqual(self.session.agent_focus_target_id, original_id)
                actor = await self.session.get_current_page()
                test.assertEqual(await actor.evaluate("() => document.querySelector('#term').value"), "before-browser-use")
                event = self.session.event_bus.dispatch(SwitchTabEvent(target_id=other_id))
                await event
                await event.event_result(raise_if_any=True, raise_if_none=False)
                actor = await self.session.get_current_page()
                await actor.evaluate("() => { document.querySelector('#term').value = 'after-browser-use'; return true; }")
                if max_steps == 1:
                    raise RuntimeError("local fixture interruption")
                return History()

        for max_steps in (2, 1):
            await self.manager.adopt_target(original_id)
            with patch("browser_use.BrowserSession", side_effect=make_session), patch("browser_use.Agent", LocalAgent), patch("browser_use.ChatOpenAI", return_value=object()):
                result = await navigator.browse_web.ainvoke({"task": "local fixture", "max_steps": max_steps})
            self.assertEqual("[Error]" in result, max_steps == 1)
            current = await self.manager.get_page(wait_ms=0)
            self.assertIs(current, other)
            self.assertEqual(await current.locator("#term").input_value(), "after-browser-use")
            self.assertFalse(self.page.is_closed())
            self.assertFalse(other.is_closed())
            self.assertEqual(len(self.page.context.pages), 2)
            self.assertIsNone(sessions[-1].agent_focus_target_id)
