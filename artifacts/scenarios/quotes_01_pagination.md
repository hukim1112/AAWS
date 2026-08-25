---
scenario_id: quotes_01_pagination
site_name: Quotes to Scrape
target_url: http://quotes.toscrape.com
difficulty: Level 1
expected_schema:
  type: array
  items:
    type: object
    required: ["text", "author", "tags"]
    properties:
      text:
        type: string
      author:
        type: string
      tags:
        type: array
        items:
          type: string
evaluation_criteria:
  navigator_strategy: >
    단순히 'Next' 버튼 클릭 기반의 UI 브라우징 대신, '/page/1/', '/page/2/' 등의 명확한 URL 패턴을 파악하여 경량 HTTP 루프 수집 전략을 도출해야 함.
  coder_strategy: >
    Playwright 등 무거운 브라우저 대신 requests 또는 httpx 클라이언트와 BeautifulSoup을 활용하여 1~5페이지(총 50건)의 인용구(text, author, tags)를 안정적이고 빠르게 수집해야 함.
---

# 시나리오: quotes_01_pagination

Quotes to Scrape 사이트의 1~5페이지에서 모든 인용구 데이터를 수집하세요.

[수집 항목]
- 인용구 원문 (text)
- 저자 이름 (author)
- 태그 목록 (tags)

결과는 지정된 경로에 JSON 배열 형태로 저장해주세요.
