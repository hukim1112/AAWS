"""Observable checks for skill helpers; browser tests use only a local fixture."""

import asyncio
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


SCRIPTS = Path(__file__).resolve().parents[1] / "app/agents/scraper/skills/scripts"


def load_helper(name):
    spec = importlib.util.spec_from_file_location(f"scraper_skill_{name}", SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


quality = load_helper("validate_collection")
probe = load_helper("browser_probe")


class CollectionValidationTests(unittest.TestCase):
    def test_successful_file_does_not_claim_unmeasured_coverage(self):
        report = quality.validate(
            [{"id": "a", "price": 0, "in_stock": False}],
            required=["id", "price", "in_stock"], unique_key=["id"],
            field_types={"price": "number", "in_stock": "boolean"},
        )
        self.assertTrue(report["checks_passed"])
        self.assertEqual(report["coverage"], "not_established")
        self.assertEqual(report["unique_count"], 1)

    def test_partial_duplicate_and_missing_data_fail(self):
        report = quality.validate(
            [{"id": "a", "title": "one"}, {"id": "a", "title": "  "}, {"title": "lost"}],
            required=["id", "title"], unique_key=["id"], expected_count=5,
        )
        self.assertFalse(report["checks_passed"])
        self.assertEqual(report["duplicate_count"], 1)
        self.assertEqual(report["coverage"], "count_mismatch")
        self.assertEqual(report["field_issues"]["missing_required:title"]["row_indexes"], [1])
        self.assertEqual(report["field_issues"]["missing_unique_key"]["count"], 1)

    def test_identity_can_include_variant_and_numbers_exclude_booleans(self):
        records = [{"id": "a", "variant": "red", "price": 1}, {"id": "a", "variant": "blue", "price": True}]
        report = quality.validate(records, unique_key=["id", "variant"], field_types={"price": "number"})
        self.assertEqual(report["duplicate_count"], 0)
        self.assertEqual(report["field_issues"]["invalid_type:price:number"]["count"], 1)
        self.assertFalse(quality.validate([])["checks_passed"])
        self.assertTrue(quality.validate([], min_count=0, expected_count=0)["checks_passed"])

    def test_cli_reports_failure_without_modifying_input(self):
        with tempfile.TemporaryDirectory() as root:
            source = Path(root) / "items.jsonl"
            report = Path(root) / "quality.json"
            source.write_text('{"id":"a"}\n{"id":"a"}\n', encoding="utf-8")
            original = source.read_bytes()
            result = subprocess.run(
                [sys.executable, "-B", str(SCRIPTS / "validate_collection.py"), str(source),
                 "--unique-key", "id", "--report", str(report)],
                capture_output=True, text=True, timeout=10,
            )
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertEqual(json.loads(report.read_text())["duplicate_count"], 1)
            self.assertEqual(source.read_bytes(), original)
            source.write_text("<html>Login required</html>", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, "-B", str(SCRIPTS / "validate_collection.py"), str(source)],
                capture_output=True, text=True, timeout=10,
            )
            self.assertEqual(result.returncode, 2)
            self.assertFalse(json.loads(result.stdout)["checks_passed"])

    def test_diagnostics_omit_scalar_values_and_url_credentials(self):
        url = probe.diagnostic_url("https://name:password@example.com/list?cursor=abc&token=secret#private")
        self.assertNotIn("password", url)
        self.assertNotIn("secret", url)
        self.assertNotIn("private", url)
        shape = probe.json_shape({"items": [{"id": "private-id"}], "token": "private-token"})
        self.assertNotIn("private-", json.dumps(shape))
        self.assertEqual(shape["fields"]["items"]["length"], 1)


HTML = """<!doctype html><html><head><title>Shared skill fixture</title>
<script id="__NEXT_DATA__" type="application/json">
{"props":{"pageProps":{"items":[{"id":"private-record","title":"private-title"}],"token":"private-json-token"}}}
</script></head><body>
<input id="term"><button id="load">Load</button><button id="limited">Limited</button>
<div id="items"></div><iframe id="results" src="/frame"></iframe>
<script>
sessionStorage.loads = String(Number(sessionStorage.loads || 0) + 1);
document.querySelector('#load').onclick = async () => {
  const response = await fetch('/records?cursor=private-cursor&token=private-query-token', {
    method:'POST', headers:{'Content-Type':'application/json', 'Authorization':'Bearer private-header'},
    body:JSON.stringify({filter:document.querySelector('#term').value, csrf:'private-csrf'})
  });
  const data = await response.json();
  document.querySelector('#items').textContent = data.items[0].title;
};
document.querySelector('#limited').onclick = () => fetch('/limited');
</script></body></html>"""


@unittest.skipUnless(os.environ.get("RUN_BROWSER_TESTS") == "1", "Set RUN_BROWSER_TESTS=1 for local Chromium/CDP tests")
class SharedBrowserProbeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from aiohttp import web
        from app.tools.navigator import PlaywrightManager

        self.tmp = tempfile.TemporaryDirectory(prefix="scraper-skill-test-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        environment = patch.dict(os.environ, {"HEADLESS": "true", "LANGSMITH_TRACING": "false"})
        environment.start()
        self.addCleanup(environment.stop)
        self.requests = []
        application = web.Application()

        async def fixture(request):
            return web.Response(text=HTML, content_type="text/html")

        async def frame(request):
            return web.Response(text='<div class="item">Frame data</div>', content_type="text/html")

        async def records(request):
            self.requests.append({
                "cookie": request.cookies.get("lesson"),
                "authorization": request.headers.get("Authorization"),
                "body": await request.json(),
            })
            return web.json_response({"items": [{"id": "a", "title": "Collected"}], "next": None})

        async def limited(request):
            return web.json_response({"error": "rate_limited"}, status=429, headers={"Retry-After": "7"})

        application.router.add_get("/page", fixture)
        application.router.add_get("/frame", frame)
        application.router.add_post("/records", records)
        application.router.add_get("/limited", limited)
        server = web.AppRunner(application)
        await server.setup()
        self.addAsyncCleanup(server.cleanup)
        site = web.TCPSite(server, "127.0.0.1", 0)
        await site.start()
        self.url = f"http://127.0.0.1:{site._server.sockets[0].getsockname()[1]}/page"
        self.manager = PlaywrightManager()
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            self.manager._cdp_port = sock.getsockname()[1]
        self.addAsyncCleanup(self.manager.close)
        self.page = await self.manager.get_page(self.url, wait_ms=0)
        await self.page.locator("#term").fill("lesson search")
        await self.page.context.add_cookies([{"name": "lesson", "value": "private-cookie", "url": self.url}])
        self.target_id = await self.manager.page_target_id(self.page)

    async def run_probe(self, *arguments):
        output = self.root / "probe.json"
        process = await asyncio.create_subprocess_exec(
            sys.executable, "-B", str(SCRIPTS / "browser_probe.py"), *arguments,
            "--cdp-url", self.manager.cdp_url, "--output", str(output),
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=25)
        finally:
            if process.returncode is None:
                process.kill()
                await process.wait()
        self.assertTrue(output.exists(), (stdout, stderr))
        return process.returncode, json.loads(output.read_text(encoding="utf-8"))

    async def assert_state_preserved(self):
        self.assertIsNone(self.manager._chrome_process.returncode)
        self.assertFalse(self.page.is_closed())
        self.assertEqual(await self.page.locator("#term").input_value(), "lesson search")
        self.assertEqual(await self.page.evaluate("sessionStorage.loads"), "1")
        self.assertEqual(await self.manager.page_target_id(self.page), self.target_id)

    async def test_inspection_preserves_existing_document_and_process(self):
        count = len(self.page.context.pages)
        code, report = await self.run_probe("inspect", "--target-id", self.target_id)
        self.assertEqual(code, 0, report)
        self.assertEqual(len(self.page.context.pages), count)
        self.assertEqual(len(report["frames"]), 2)
        data = report["embedded_data"][0]["json_shape"]
        self.assertEqual(data["fields"]["props"]["fields"]["pageProps"]["fields"]["items"]["length"], 1)
        self.assertNotIn("private-record", json.dumps(report))
        self.assertNotIn("private-json-token", json.dumps(report))
        await self.assert_state_preserved()

    async def test_ambiguous_or_missing_target_is_not_silently_replaced(self):
        other = await self.page.context.new_page()
        await other.goto(self.url)
        code, report = await self.run_probe("inspect")
        self.assertEqual(code, 2, report)
        code, report = await self.run_probe("inspect", "--target-id", "missing")
        self.assertEqual(code, 2, report)
        code, report = await self.run_probe("inspect", "--target-id", self.target_id)
        self.assertEqual(code, 0, report)
        self.assertEqual(report["target"]["target_id"], self.target_id)
        self.assertFalse(other.is_closed())
        await self.assert_state_preserved()

    async def test_capture_observes_current_authenticated_state_without_exporting_values(self):
        code, report = await self.run_probe(
            "network", "--target-id", self.target_id, "--click", "#load", "--duration-ms", "200",
        )
        self.assertEqual(code, 0, report)
        response = next(item for item in report["responses"] if "/records" in item["url"])
        self.assertEqual(response["method"], "POST")
        self.assertEqual(response["status"], 200)
        self.assertEqual(response["json_shape"]["fields"]["items"]["length"], 1)
        self.assertEqual(self.requests, [{
            "cookie": "private-cookie", "authorization": "Bearer private-header",
            "body": {"filter": "lesson search", "csrf": "private-csrf"},
        }])
        self.assertNotIn("private-", json.dumps(report))
        self.assertEqual(await self.page.locator("#items").text_content(), "Collected")
        await self.assert_state_preserved()

    async def test_http_failure_and_action_failure_are_distinguishable(self):
        code, report = await self.run_probe(
            "network", "--target-id", self.target_id, "--click", "#limited", "--duration-ms", "200",
        )
        self.assertEqual(code, 0, report)  # A completed observation, not collection success.
        response = next(item for item in report["responses"] if "/limited" in item["url"])
        self.assertEqual(response["status"], 429)
        self.assertEqual(response["retry_after"], "7")
        code, report = await self.run_probe(
            "network", "--target-id", self.target_id, "--click", "button", "--duration-ms", "0",
        )
        self.assertEqual(code, 1, report)  # Strict selector matches both buttons.
        self.assertFalse(report["action"]["ok"])
        await self.assert_state_preserved()
