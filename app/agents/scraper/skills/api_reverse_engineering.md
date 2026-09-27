---
name: api_reverse_engineering
description: 난독화된 DOM 대신 백엔드 비공개 JSON API(XHR/Fetch) 가로채기 및 초고속 직수집 기법
---

# 🌐 네트워크 API 역공학 직수집 플레이북 (API Reverse Engineering)


웹사이트가 React, Vue, Next.js 등 복잡한 프론트엔드 프레임워크로 작성되어 DOM 클래스명이 난독화(예: `class="_3xY8a_0"`)되어 있거나, 무한 스크롤 데이터가 DOM 파싱으로 다루기 까다로울 때 적용하는 초고속 직수집 패턴입니다.

---

## 1. 핵심 원리: DOM을 긁지 말고, 원본 JSON API를 낚아채라

현대 웹사이트는 화면을 그리기 전에 **백엔드 REST API 또는 GraphQL 엔드포인트**에서 JSON 형식의 순수 데이터를 받아옵니다.  
따라서 복잡한 HTML 셀렉터를 고생해서 찾을 필요 없이, **브라우저가 호출하는 그 비공개 API를 파이썬 스크립트에서 직접 호출**하는 것이 가장 깔끔하고 빠릅니다.

---

## 2. Playwright를 통한 네트워크 요청 가로채기 (Sniffing)

스크래퍼가 페이지를 방문할 때 어떤 백엔드 API가 호출되는지 탐지하는 스크립트 템플릿:

```python
import json
from playwright.sync_api import sync_playwright

def sniff_api_requests(target_url: str):
    captured_apis = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # 네트워크 응답 가로채기 핸들러 등록
        def handle_response(response):
            # JSON 데이터를 반환하는 XHR/Fetch 요청 필터링
            content_type = response.headers.get("content-type", "")
            if "application/json" in content_type and "api" in response.url:
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

## 3. 포착된 API로 직접 수집 스크립트 작성 (`httpx` / `requests`)

포착된 URL, 쿼리 파라미터, 필수 헤더(`Referer`, `Authorization`, `Cookie`)를 복사하여 경량 HTTP 클라이언트로 즉시 대량 수집합니다:

```python
import requests
import json

def fetch_direct_api():
    endpoint = "https://api.target-site.com/v1/products"
    headers = {
        "User-Agent": "Mozilla/5.0 ...",
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
        resp = requests.get(endpoint, headers=headers, params=params)
        if resp.status_code == 200:
            items = resp.json().get("items", [])
            if not items:
                break
            all_data.extend(items)
        else:
            print(f"Error at page {page}: {resp.status_code}")
            break

    with open("artifacts/data/api_collected.json", "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)

    return f"총 {len(all_data)}건 수집 완료"
```

---

## 4. 체크리스트
- [ ] 브라우저 렌더링에 비해 수집 속도가 10~50배 이상 빠릅니다.
- [ ] HTML 셀렉터 변경에 영향을 받지 않아 코드가 훨씬 견고합니다.
- [ ] 요청 시 반드시 원본 페이지의 `Referer` 헤더를 포함해야 403 차단을 피할 수 있습니다.
