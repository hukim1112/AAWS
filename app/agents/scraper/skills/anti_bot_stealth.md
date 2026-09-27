---
name: anti_bot_stealth
description: Bypass bot detection, Cloudflare Turnstile, 403 Forbidden, User-Agent filtering, and apply Playwright stealth patterns.
---

# 🛡️ Anti-Bot Detection Bypass & Headless Stealth Playbook

When automated browsers (Headless Chrome, Playwright, Puppeteer) trigger `403 Forbidden`, Cloudflare Turnstile, CAPTCHAs, or empty/blocked pages, apply the evasion patterns below.

---

## 1. Primary Bot Detection Signals & Diagnosis

1. **`navigator.webdriver === true`**: Default headless Chromium flags expose this property directly to JavaScript.
2. **Abnormal / Missing Request Headers**: `User-Agent` containing `HeadlessChrome`, missing `Sec-Ch-Ua`, or absent `Accept-Language` headers.
3. **Machine Request Velocity**: Unthrottled requests trigger automated rate limiters (HTTP 429).
4. **Session Cold Starts**: Direct requests to deep detail URLs without visiting the root domain or establishing session cookies.

---

## 2. Playwright Stealth Configuration

Apply the following setup to launch Playwright with realistic browser fingerprints and CDP-level property overrides:

```python
import asyncio
from playwright.async_api import async_playwright

async def run_stealth_crawler():
    async with async_playwright() as p:
        # 1. Disable automation flags
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-infobars"
            ]
        )
        
        # 2. Emulate realistic desktop context
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
            timezone_id="America/New_York"
        )
        
        page = await context.new_page()
        
        # 3. Mask navigator.webdriver & inject chrome runtime
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            window.chrome = { runtime: {} };
        """)
        
        # 4. Safe navigation with timeout
        await page.goto("https://target-site.com", wait_until="networkidle", timeout=30000)
        await asyncio.sleep(2)  # Extra grace period for hydration
        
        content = await page.content()
        await browser.close()
        return content
```

---

## 3. Session Warm-Up & Adaptive Rate Limiting

1. **Randomized Delay (Jitter)**:
   ```python
   import random, time
   time.sleep(random.uniform(1.5, 3.5))
   ```

2. **Session Warm-Up**:
   Always navigate to the home/landing page (`https://target-site.com/`) first to obtain valid initial cookies and tokens before requesting deep endpoints or internal queries.
