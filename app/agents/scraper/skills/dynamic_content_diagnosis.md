---
name: dynamic-content-diagnosis
description: Use when selectors return empty values, content appears only after rendering, or scrolling replaces existing DOM items.
---

# 빈 추출 결과와 동적 목록의 진단 사례

## 요소가 있는데 추출한 값은 없는 경우

`verify_selectors`의 "매칭 12건, 샘플 0건"은 요소 12개를 찾았지만 검사한 샘플에서는 선택한 텍스트·속성 값을 얻지 못했다는 뜻이다. 일부 요소만 샘플링하므로 모든 매칭 요소의 값이 비었다는 뜻도 아니다. 매칭 0건과 원인이 다를 수 있다.

예를 들어 아래 이미지의 주소는 텍스트나 `src`가 아니라 `data-src`에 있다.

```html
<img class="product-image" data-src="https://example.com/item.jpg">
```

이 구조를 실제로 확인했다면 `verify_selectors`에 다음 인자를 전달해 속성 값을 확인할 수 있다.

```json
{
  "url": "",
  "selectors_json": "{\"image\":\"img.product-image::attr(data-src)\"}"
}
```

`::attr(...)`는 이 도구의 전용 표기다. Playwright 코드에서는 `get_attribute()`, BeautifulSoup에서는 해당 태그의 속성 접근으로 옮겨야 한다.

## 화면에는 보이는데 셀렉터가 매칭되지 않는 경우

| 관찰한 상황 | 적용할 수 있는 접근 |
|---|---|
| 로딩 표시가 사라진 뒤 목록이 생김 | `interact_page`의 wait 액션으로 실제 목록 셀렉터를 제한된 시간 동안 기다린 뒤 다시 검증한다. |
| iframe 안에 목록이 있음 | 부모 HTML 대신 해당 프레임에 `page.frame_locator(...).locator(...)`로 접근한다. |
| open Shadow DOM 안에 항목이 있음 | Playwright locator는 open shadow root 내부를 찾을 수 있다. `page.content()`를 BeautifulSoup으로 파싱하는 방식으로는 같은 내부 DOM을 얻지 못한다. closed shadow root에는 같은 접근을 적용할 수 없다. |
| 내부 패널을 스크롤해야 항목이 생김 | 실제 패널을 대상으로 조작한다. `interact_page`의 scroll 액션은 창을 스크롤하므로 패널 스크롤과 다를 수 있다. |

예를 들어 `.result-item`이 나타날 때까지 기다리는 `interact_page` 인자는 다음과 같다. 셀렉터는 실제로 관찰한 것으로 바꾼다.

```json
{
  "url": "",
  "actions_json": "[{\"action\":\"wait\",\"selector\":\".result-item\",\"timeout_ms\":5000}]"
}
```

대기 후 `url=""`로 현재 탭의 항목을 다시 확인한다. 도구의 `DOM 변경` 표시는 HTML 길이 차이에 기반하므로 같은 길이의 목록으로 교체되면 변화를 놓칠 수 있다. 각 액션 결과와 실제 항목이 더 직접적인 확인 근거다.

Playwright 코드로 iframe 등을 진단할 때 기존 탭에 연결하는 방법은 [API 스킬의 예제](api_reverse_engineering.md)를 참고할 수 있다.

## 스크롤해도 DOM 항목 수가 일정한 경우

예를 들어 스크롤 전후 매칭 수는 모두 20건이지만 항목 ID가 달라진다면, 화면 밖의 노드를 제거하는 가상 목록일 수 있다. 마지막 DOM을 한 번만 읽으면 앞서 지나간 항목이 빠진다.

이때는 [API 스킬](api_reverse_engineering.md)로 목록 응답을 찾는 접근이 유용하다. 적합한 API를 찾지 못했다면 조금씩 스크롤하며 보이는 항목을 누적하고, 안정적인 ID나 복합 키로 중복을 제거하는 방법도 가능하다. 새 항목이 잠시 없다는 사실만으로 마지막이라고 판단하지 말고, 종료 표시나 확인된 전체 건수 등과 대조한다.
