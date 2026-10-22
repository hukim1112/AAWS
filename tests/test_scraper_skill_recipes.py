"""Execute the documented recipes against local data, interruptions and Chromium.

The Python examples in Markdown are the source under test. No LLM or external
website is used. Set RUN_BROWSER_TESTS=1 for the local CDP integration cases.
"""

import asyncio
import importlib.util
import json
import os
from pathlib import Path
import re
import socket
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from unittest.mock import patch


SKILLS = Path(__file__).resolve().parents[1] / "app/agents/scraper/skills"
DOCUMENTS = (
    "references/shared_browser.md", "api_reverse_engineering.md",
    "anti_bot_stealth.md", "pagination_and_resume.md",
    "dynamic_content_diagnosis.md", "collection_validation.md",
)


def recipe_source():
    blocks = []
    for document in DOCUMENTS:
        text = (SKILLS / document).read_text(encoding="utf-8")
        blocks.extend(re.findall(r"```python\n(.*?)\n```", text, flags=re.DOTALL))
    return "\n\n".join(blocks)


RECIPES = {"__name__": "documented_scraper_recipes"}
exec(compile(recipe_source(), "scraper_skill_recipes", "exec"), RECIPES)
spec = importlib.util.spec_from_file_location(
    "recipe_quality", SKILLS / "scripts/validate_collection.py"
)
quality = importlib.util.module_from_spec(spec)
spec.loader.exec_module(quality)


class RecipeValueTests(unittest.TestCase):
    def test_retry_after_seconds_http_date_and_invalid_values(self):
        parse = RECIPES["retry_after_seconds"]
        now = datetime(2026, 9, 28, tzinfo=timezone.utc)
        self.assertEqual(parse("120", now), 120)
        self.assertEqual(parse(format_datetime(now + timedelta(seconds=120), usegmt=True), now), 120)
        self.assertEqual(parse(format_datetime(now - timedelta(seconds=5), usegmt=True), now), 0)
        self.assertIsNone(parse("not a date", now))
        self.assertIsNone(parse(None, now))

    def test_missing_price_does_not_shift_following_product_rows(self):
        html = """<article class="product" data-id="a">
          <span class="title">Alpha</span><span class="price">10 USD</span><a class="detail" href="/a">View</a>
        </article><article class="product" data-id="b">
          <span class="title">Beta</span><a class="detail" href="/b">View</a>
        </article><article class="product" data-id="c">
          <span class="title">Gamma</span><span class="price">30 USD</span>
        </article>"""
        rows = RECIPES["parse_product_cards"](html, "https://example.com/catalog/")
        self.assertEqual([row["id"] for row in rows], ["a", "b", "c"])
        self.assertEqual([row["price_text"] for row in rows], ["10 USD", None, "30 USD"])
        self.assertEqual(rows[1]["url"], "https://example.com/b")
        report = quality.validate(rows, required=["id", "title", "price_text"], unique_key=["id"])
        self.assertEqual(report["field_issues"]["missing_required:price_text"]["row_indexes"], [1])

    def test_failed_serialization_keeps_previous_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "data.json"
            RECIPES["atomic_json"](path, {"records": ["committed"]})
            before = path.read_bytes()
            with self.assertRaises(TypeError):
                RECIPES["atomic_json"](path, {"records": [object()]})
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(list(Path(directory).iterdir()), [path])


class PaginationRecipeTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="scraper-recipe-pagination-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    async def test_interruption_between_data_and_checkpoint_replays_without_loss(self):
        calls = []

        async def fetch(position):
            calls.append(position)
            if position == 1:
                return [{"id": "a"}, {"id": "b", "title": "first"}], 2
            return [{"id": "b", "title": "later"}, {"id": "c"}], None

        write = RECIPES["atomic_json"]

        def interrupt_checkpoint(path, value):
            if Path(path).name == "checkpoint.json" and value["done"]:
                raise OSError("simulated process interruption after data commit")
            write(path, value)

        with patch.dict(RECIPES, {"atomic_json": interrupt_checkpoint}):
            with self.assertRaises(OSError):
                await RECIPES["collect_pages"](fetch, self.root, source={"site": "fixture"})
        self.assertEqual(json.loads((self.root / "checkpoint.json").read_text())["next_position"], 2)
        self.assertEqual(len(json.loads((self.root / "data.json").read_text())["records"]), 3)
        result = await RECIPES["collect_pages"](fetch, self.root, source={"site": "fixture"})
        self.assertEqual(calls, [1, 2, 2])
        self.assertTrue(result["done"])
        self.assertEqual([row["id"] for row in result["records"]], ["a", "b", "c"])
        self.assertEqual(result["records"][1]["title"], "first")

    async def test_page_limit_resumes_cursor_and_rejects_changed_source(self):
        calls = []

        async def fetch(cursor):
            calls.append(cursor)
            return ([{"id": "a"}], "opaque-next") if cursor is None else ([{"id": "b"}], None)

        result = await RECIPES["collect_pages"](
            fetch, self.root, source={"filter": "blue"}, start=None, max_pages=1
        )
        self.assertFalse(result["done"])
        self.assertEqual(result["stop_reason"], "page_limit")
        with self.assertRaises(ValueError):
            await RECIPES["collect_pages"](fetch, self.root, source={"filter": "red"}, start=None)
        self.assertEqual(calls, [None])
        result = await RECIPES["collect_pages"](
            fetch, self.root, source={"filter": "blue"}, start=None
        )
        self.assertTrue(result["done"])
        self.assertEqual(calls, [None, "opaque-next"])

    async def test_cycle_and_bad_identity_leave_last_checkpoint_unchanged(self):
        async def first(position):
            return [{"id": "a"}], 2

        await RECIPES["collect_pages"](first, self.root, source={}, max_pages=1)
        checkpoint = (self.root / "checkpoint.json").read_bytes()
        data = (self.root / "data.json").read_bytes()

        async def cycle(position):
            return [{"id": "b"}], 1

        async def missing_identity(position):
            return [{"title": "missing identity"}], None

        for fetch, expected_error in ((cycle, ValueError), (missing_identity, KeyError)):
            with self.assertRaises(expected_error):
                await RECIPES["collect_pages"](fetch, self.root, source={})
            self.assertEqual((self.root / "checkpoint.json").read_bytes(), checkpoint)
            self.assertEqual((self.root / "data.json").read_bytes(), data)

    async def test_missing_committed_data_does_not_resume_as_empty_collection(self):
        async def fetch(position):
            return [{"id": "a"}], None

        await RECIPES["collect_pages"](fetch, self.root, source={})
        (self.root / "data.json").unlink()
        with self.assertRaises(ValueError):
            await RECIPES["collect_pages"](fetch, self.root, source={})

    async def test_compound_identity_and_confirmed_empty_terminal_page(self):
        async def fetch(position):
            if position == 1:
                return [{"id": 0, "variant": "red"}, {"id": 0, "variant": "blue"}], 2
            return [], None

        result = await RECIPES["collect_pages"](
            fetch, self.root, source={}, key_fields=("id", "variant")
        )
        self.assertTrue(result["done"])
        self.assertEqual(len(result["records"]), 2)


HTML = """<!doctype html><html><head><title>Recipe fixture</title>
<script id="__NEXT_DATA__" type="application/json">
{"props":{"pageProps":{"items":[{"id":"a","title":"Alpha"},{"id":"b","title":"Beta"}],"total":3}}}
</script></head><body>
<input id="term"><button id="more">More</button><div id="items"></div>
<iframe id="results" src="/frame"></iframe><div id="shadow-host"></div>
<div id="panel" style="height:80px;width:250px;overflow:auto;position:relative">
  <div style="height:320px;position:relative"><div id="rows"></div></div>
</div>
<script>
sessionStorage.loads = String(Number(sessionStorage.loads || 0) + 1);
document.querySelector('#more').onclick = async () => {
  fetch('/metrics');
  const response = await fetch('/api/items?category=' + encodeURIComponent(document.querySelector('#term').value));
  const data = await response.json();
  document.querySelector('#items').textContent = data.items[0].title;
};
document.querySelector('#shadow-host').attachShadow({mode:'open'}).innerHTML = '<span class="item">Shadow value</span>';
const panel = document.querySelector('#panel');
function renderRows() {
  const first = Math.min(6, Math.floor(panel.scrollTop / 40));
  document.querySelector('#rows').innerHTML = [first, first + 1].map(i =>
    '<div class="row" data-id="r' + i + '" style="position:absolute;height:40px;top:' + (i*40) + 'px">' +
    '<span class="title">Title ' + i + '</span></div>').join('');
}
panel.addEventListener('scroll', renderRows); renderRows();
</script></body></html>"""


@unittest.skipUnless(os.environ.get("RUN_BROWSER_TESTS") == "1", "Set RUN_BROWSER_TESTS=1 for local Chromium/CDP recipes")
class BrowserRecipeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from aiohttp import web
        from app.tools.navigator import PlaywrightManager

        self.tmp = tempfile.TemporaryDirectory(prefix="scraper-recipe-browser-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        env = patch.dict(os.environ, {"HEADLESS": "true", "LANGSMITH_TRACING": "false"})
        env.start()
        self.addCleanup(env.stop)
        self.requests, self.counts = [], {}
        application = web.Application()

        async def fixture(request):
            return web.Response(text=HTML, content_type="text/html")

        async def frame(request):
            return web.Response(text='<div class="item">Frame value</div>', content_type="text/html")

        async def items(request):
            self.requests.append({"path": request.path, "query": dict(request.query),
                                  "cookie": request.cookies.get("lesson")})
            if request.cookies.get("lesson") != "session":
                return web.Response(text="Login required", content_type="text/html")
            if request.path == "/api/items":
                return web.json_response({"items": [{"id": "c", "title": "Captured"}], "nextCursor": None})
            if "cursor" not in request.query:
                return web.json_response({"items": [{"id": "a", "title": "Alpha"}, {"id": "b", "title": "Beta"}], "nextCursor": "opaque-next"})
            if request.query["cursor"] == "opaque-next":
                return web.json_response({"items": [{"id": "b", "title": "Beta"}, {"id": "c", "title": "Gamma"}], "nextCursor": None})
            return web.json_response({"errors": ["invalid cursor"]})

        async def responses(request):
            kind = request.match_info["kind"]
            self.counts[kind] = self.counts.get(kind, 0) + 1
            if kind == "recover" and self.counts[kind] == 1:
                return web.json_response({"error": "limited"}, status=429, headers={"Retry-After": "0"})
            if kind == "wait":
                return web.json_response({"error": "limited"}, status=429, headers={"Retry-After": "120"})
            if kind == "denied":
                return web.json_response({"error": "denied"}, status=403)
            if kind == "html":
                return web.Response(text="Login required", content_type="text/html")
            if kind == "errors":
                return web.json_response({"data": None, "errors": [{"message": "failed"}]})
            return web.json_response({"items": [{"id": "recovered"}]})

        async def metrics(request):
            return web.json_response({"metrics": True})

        application.router.add_get("/page", fixture)
        application.router.add_get("/frame", frame)
        application.router.add_get("/api/items", items)
        application.router.add_get("/cursor", items)
        application.router.add_get("/responses/{kind}", responses)
        application.router.add_get("/metrics", metrics)
        server = web.AppRunner(application)
        await server.setup()
        self.addAsyncCleanup(server.cleanup)
        site = web.TCPSite(server, "127.0.0.1", 0)
        await site.start()
        self.origin = f"http://127.0.0.1:{site._server.sockets[0].getsockname()[1]}"
        self.url = self.origin + "/page"
        self.manager = PlaywrightManager()
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            self.manager._cdp_port = sock.getsockname()[1]
        self.addAsyncCleanup(self.manager.close)
        self.page = await self.manager.get_page(self.url, wait_ms=0)
        await self.page.locator("#term").fill("lesson filter")
        await self.page.context.add_cookies([{"name": "lesson", "value": "session", "url": self.url}])
        self.target_id = await self.manager.page_target_id(self.page)

    async def assert_preserved(self):
        self.assertIsNone(self.manager._chrome_process.returncode)
        self.assertFalse(self.page.is_closed())
        self.assertEqual(await self.page.locator("#term").input_value(), "lesson filter")
        self.assertEqual(await self.page.evaluate("sessionStorage.loads"), "1")
        self.assertEqual(await self.manager.page_target_id(self.page), self.target_id)

    async def test_cross_process_recipes_read_values_capture_response_and_preserve_tab(self):
        script, output = self.root / "use_recipes.py", self.root / "result.json"
        script.write_text(recipe_source() + '''
import sys
async def main():
    async with existing_page(sys.argv[1], current_url=sys.argv[2]) as page:
        initial = await next_item_rows(page)
        missing = await read_embedded_json(page, "script#missing")
        frame = await read_frame_items(page, "iframe#results", ".item")
        shadow = await page.locator("#shadow-host .item").all_text_contents()
        request, payload = await capture_more(page, sys.argv[3], "#more")
        result = {"initial": initial, "missing": missing, "frame": frame,
                  "shadow": shadow, "method": request.method, "captured": payload["items"]}
    Path(sys.argv[4]).write_text(json.dumps(result), encoding="utf-8")
asyncio.run(main())
''', encoding="utf-8")
        process = await asyncio.create_subprocess_exec(
            sys.executable, "-B", str(script), self.manager.cdp_url, self.url,
            self.origin + "/api/items", str(output),
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=25)
        finally:
            if process.returncode is None:
                process.kill()
                await process.wait()
        self.assertEqual(process.returncode, 0, (stdout, stderr))
        result = json.loads(output.read_text())
        self.assertEqual([row["id"] for row in result["initial"]], ["a", "b"])
        self.assertEqual(result["missing"], [])
        self.assertEqual(result["frame"], ["Frame value"])
        self.assertEqual(result["shadow"], ["Shadow value"])
        self.assertEqual(result["captured"], [{"id": "c", "title": "Captured"}])
        self.assertEqual(self.requests[-1]["query"], {"category": "lesson filter"})
        self.assertEqual(self.requests[-1]["cookie"], "session")
        await self.assert_preserved()

    async def test_authenticated_api_collection_resumes_and_validates_real_records(self):
        run_dir = self.root / "collection"
        async with RECIPES["existing_page"](self.manager.cdp_url, current_url=self.url) as page:
            first = await RECIPES["collect_cursor_list"](
                page, self.origin + "/cursor", run_dir, filters={"category": "chosen"}, max_pages=1
            )
            self.assertFalse(first["done"])
            second = await RECIPES["collect_cursor_list"](
                page, self.origin + "/cursor", run_dir, filters={"category": "chosen"}, max_pages=1
            )
        self.assertTrue(second["done"])
        rows = json.loads((run_dir / "items.json").read_text())
        self.assertEqual([row["id"] for row in rows], ["a", "b", "c"])
        report = quality.validate(rows, required=["id", "title"], unique_key=["id"], expected_count=3)
        self.assertTrue(report["checks_passed"], report)
        self.assertEqual([request["query"].get("cursor") for request in self.requests], [None, "opaque-next"])
        self.assertTrue(all(request["cookie"] == "session" for request in self.requests))
        await self.assert_preserved()

    async def test_retry_recovers_but_does_not_ignore_wait_budget_or_non_retryable_response(self):
        get = RECIPES["get_json_with_backoff"]
        async with RECIPES["existing_page"](self.manager.cdp_url, current_url=self.url) as page:
            result = await get(page.context, self.origin + "/responses/recover", max_wait_s=0)
            self.assertEqual(result["items"], [{"id": "recovered"}])
            with self.assertRaises(RuntimeError):
                await get(page.context, self.origin + "/responses/wait", max_wait_s=1)
            for kind in ("denied", "html", "errors"):
                with self.assertRaises(ValueError):
                    await get(page.context, self.origin + "/responses/" + kind)
        self.assertEqual(self.counts, {"recover": 2, "wait": 1, "denied": 1, "html": 1, "errors": 1})
        await self.assert_preserved()

    async def test_virtual_list_collects_items_that_disappear_from_the_dom(self):
        async with RECIPES["existing_page"](self.manager.cdp_url, current_url=self.url) as page:
            result = await RECIPES["collect_virtual_rows"](page, "#panel", ".row", wait_ms=80)
            self.assertEqual(await page.locator("#panel .row").count(), 2)
        self.assertEqual([row["id"] for row in result["records"]], [f"r{i}" for i in range(8)])
        self.assertEqual([row["title"] for row in result["records"]], [f"Title {i}" for i in range(8)])
        self.assertEqual(result["stop_reason"], "no_scroll_progress")
        await self.assert_preserved()

    async def test_ambiguous_tabs_require_identity_and_are_not_replaced(self):
        other = await self.page.context.new_page()
        await other.goto(self.url)
        with self.assertRaises(ValueError):
            async with RECIPES["existing_page"](self.manager.cdp_url, current_url=self.url):
                self.fail("An ambiguous URL must not choose a tab")
        async with RECIPES["existing_page"](self.manager.cdp_url, target_id=self.target_id) as page:
            self.assertEqual(await page.locator("#term").input_value(), "lesson filter")
        with self.assertRaises(ValueError):
            async with RECIPES["existing_page"](self.manager.cdp_url, target_id="missing"):
                self.fail("A missing target must not create a new one")
        self.assertFalse(other.is_closed())
        self.assertEqual(len(self.page.context.pages), 2)
        await self.assert_preserved()
