---
scenario_id: quotes_01_pagination
site_name: Quotes to Scrape
target_url: http://quotes.toscrape.com
difficulty: Level 1
expected_schema:
  type: array
  items:
    text: string
    author: string
    tags:
    - string
evaluation_criteria:
  navigator_strategy: 단순히 'Next' 버튼의 CSS Selector를 찾는 것이 아니라, '/page/2/', '/page/3/'
    등의 URL 패턴을 파악하여 URL 파라미터 기반의 수집 전략을 제안해야 함.
  coder_strategy: UI 클릭 기반(Playwright) 대신, Requests 등 가벼운 HTTP 클라이언트로 루프를 도는 코드를 작성해야
    함.
---

# 시나리오: quotes_01_pagination

Quotes to Scrape 사이트의 1~5페이지에서 모든 인용구 데이터를 수집하세요.

[수집 항목]
- 인용구 원문 (text)
- 저자 이름 (author)
- 태그 목록 (tags)

결과는 JSON 배열 형태로 'quotes_5pages.json' 파일에 저장해주세요.
