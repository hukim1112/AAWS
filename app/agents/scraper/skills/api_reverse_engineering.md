---
name: api_reverse_engineering
description: Intercept internal backend JSON APIs (XHR/Fetch) and extract SSR hydration states (__NEXT_DATA__) to bypass complex DOM parsing.
---

# 🌐 Network API Reverse Engineering & SSR Extraction Playbook

When target websites utilize modern SPA/SSR frameworks (React, Vue, Next.js, Nuxt), DOM class names are often randomized or obfuscated (e.g., `class="_3xY8a_0"`), and data is loaded dynamically. Instead of struggling with fragile CSS selectors, this playbook guides you to extract data directly from the underlying JSON source.

---

## 0. Pre-flight Check: SSR Hydration State Extraction (`__NEXT_DATA__`)

Before executing dynamic browser interactions or selector parsing, check if the entire page data is already serialized in the static HTML:

```python
import json
from bs4 import BeautifulSoup

def extract_ssr_state(html_content: str):
    soup = BeautifulSoup(html_content, "html.parser")
    
    # 1. Next.js hydration script
    next_data = soup.find("script", id="__NEXT_DATA__")
    if next_data and next_data.string:
        try:
            payload = json.loads(next_data.string)
            # Extracted dataset usually resides in props.pageProps
            return payload.get("props", {}).get("pageProps", {})
        except json.JSONDecodeError:
            pass

    # 2. Nuxt.js state script
    nuxt_data = soup.find("script", id="__NUXT_DATA__")
    if nuxt_data and nuxt_data.string:
        try:
            return json.loads(nuxt_data.string)
        except json.JSONDecodeError:
            pass

    # 3. Schema.org structured data (JSON-LD)
    json_ld = soup.find("script", type="application/ld+json")
    if json_ld and json_ld.string:
        try:
            return json.loads(json_ld.string)
        except json.JSONDecodeError:
            pass

    return None
```
> **Rule of Thumb**: If `__NEXT_DATA__` exists, you can extract 100% of the structured dataset instantly without headless browser interaction.

---

## 1. Network Sniffing: Intercept Hidden JSON APIs via Playwright

When data is loaded dynamically via background AJAX/Fetch requests, sniff the network traffic to identify internal endpoints:

```python
import json
from playwright.sync_api import sync_playwright

def sniff_api_requests(target_url: str):
    captured_apis = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        def handle_response(response):
            content_type = response.headers.get("content-type", "")
            # Filter XHR/Fetch returning JSON data
            if "application/json" in content_type and any(k in response.url for k in ["api", "v1", "v2", "graphql", "list", "query"]):
                try:
                    data = response.json()
                    captured_apis.append({
                        "url": response.url,
                        "status": response.status,
                        "data_sample": list(data.keys()) if isinstance(data, dict) else len(data)
                    })
                except Exception:
                    pass

        page.on("response", handle_response)
        page.goto(target_url, wait_until="networkidle")
        browser.close()

    return captured_apis
```

---

## 2. Direct High-Speed Collection via HTTP Client (`httpx` / `requests`)

Once you identify the backend endpoint and query parameters, bypass headless browsers entirely and query the API directly:

```python
import requests
import json

def fetch_direct_api():
    endpoint = "https://api.target-site.com/v1/products"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Referer": "https://target-site.com/",
        "Accept": "application/json"
    }
    params = {
        "page": 1,
        "size": 50,
        "sort": "popular"
    }

    all_data = []
    for page in range(1, 6):
        params["page"] = page
        resp = requests.get(endpoint, headers=headers, params=params, timeout=10)
        if resp.status_code == 200:
            items = resp.json().get("items", [])
            if not items:
                break
            all_data.extend(items)
        else:
            print(f"Failed at page {page}: {resp.status_code}")
            break

    with open("artifacts/data/api_collected.json", "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)

    return len(all_data)
```

---

## 3. Checklist
- [ ] Check `<script id="__NEXT_DATA__">` or `application/ld+json` first.
- [ ] Always forward necessary request headers (`Referer`, `Authorization`, cookies) to avoid 403 Forbidden.
- [ ] API-based collection is 10x-50x faster and immune to front-end HTML/CSS redesigns.
