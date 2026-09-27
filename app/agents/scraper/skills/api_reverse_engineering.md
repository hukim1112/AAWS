---
name: api-discovery
description: Use when embedded page data or observed JSON responses can replace fragile DOM extraction; includes an example that reads an existing browser tab.
---

# 내장 JSON과 목록 API의 수집 패턴

## HTML에 데이터가 이미 들어 있는 경우

Next.js의 `__NEXT_DATA__` 같은 script에 화면 구성에 쓰인 데이터가 들어 있을 수 있다. `extract_dom_skeleton`과 일반적인 `get_page_section` 출력은 script를 제거하므로, 그 출력에서 찾지 못해도 원본에 없다는 뜻은 아니다.

다음 예제는 이미 열린 Chrome의 탭에서 `__NEXT_DATA__`를 읽는다. `cdp_url`은 `app/tools/navigator.py`의 `CDP_DEBUG_PORT`에 해당하는 주소이고, `current_url`은 도구가 확인한 현재 탭 URL이다. URL이 같은 탭이 여러 개라면 추가 식별이 필요하므로 임의로 선택하지 않는다.

```python
import json
from playwright.async_api import async_playwright

async def read_next_data(cdp_url, current_url):
    async with async_playwright() as playwright:
        browser = await playwright.chromium.connect_over_cdp(cdp_url)
        pages = [
            page for context in browser.contexts for page in context.pages
            if page.url == current_url
        ]
        if len(pages) != 1:
            raise ValueError("대상 탭을 하나로 식별할 수 없습니다.")
        page = pages[0]
        node = page.locator("script#__NEXT_DATA__")
        if await node.count() == 0:
            return None
        raw = await node.text_content()
        return json.loads(raw) if raw else None
```

이 코드는 기존 브라우저·탭을 닫지 않고, `async with`를 빠져나갈 때 자신의 Playwright 연결만 정리한다. iframe·네트워크 진단용 코드를 작성할 때도 이 연결 범위 안에서 선택한 `page`를 사용할 수 있다.

반환된 JSON의 구조와 데이터 범위는 사이트마다 다르다. 예를 들어 목록 20개와 전체 건수 250이 함께 있다면 초기 목록만 얻은 것이다. `__NEXT_DATA__`의 존재는 전체 데이터가 들어 있다는 보장이 아니다. Nuxt 데이터나 JSON-LD도 각각의 구조와 실제 필드를 확인해야 한다.

## 더보기를 누를 때 JSON 응답이 오는 경우

화면의 목록과 네트워크 응답을 연결하면 수집 경로를 찾을 수 있다.

1. 기존 탭에서 `page.on("response", handler)`로 응답 관찰을 시작한 뒤 검색·더보기를 실행한다. 리스너를 등록하기 전에 끝난 요청은 새 리스너로 관찰할 수 없다.
2. XHR/Fetch 등의 응답에서 실제 목록 항목이 있는지 확인한다. URL에 `api`가 들어 있는지만으로 판단하면 관련 응답을 놓치거나 무관한 요청을 선택할 수 있다.
3. 화면의 항목·필터·정렬과 응답을 대조하고, 실제 메서드·URL·쿼리·본문·인증 조건을 기록한다. 이를 바탕으로 요청 하나를 재현해 같은 데이터가 나오는지 확인한다.

예를 들어 관찰한 응답에 `nextCursor`가 있다면 그 값을 다음 요청에 전달하는 방식일 수 있다. 실제 요청과 비교해 확인하며, 임의로 `page=1, 2, 3`을 붙이는 것으로 대체하지 않는다. 쿠키가 필요한 재현에는 `page.context.request`를 사용할 수 있지만 JavaScript가 추가한 인증 헤더는 별도로 확인해야 한다.

정상 응답의 종료 값이나 빈 목록과 오류 응답을 구분한다. 같은 cursor·항목이 반복되면 수집이 진전되지 않는 것이며, HTTP 200이어도 오류 객체가 들어 있을 수 있다. 수집 건수·항목 ID·필수 필드를 대조해야 어느 범위까지 확보했는지 알 수 있다.
