---
scenario_id: quotes_02_tag_filter
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
    전체 10개 페이지를 모두 긁은 뒤 파이썬에서 if문으로 필터링하는 비효율적인 방식 대신, 사이트 내의 '/tag/inspirational/page/{N}/' 전용 URL 엔드포인트를 발견하여 전략을 수립해야 함.
  coder_strategy: >
    '/tag/inspirational/' 엔드포인트의 페이지네이션을 순회하여 해당 태그가 포함된 총 13건의 인용구 데이터를 정확하고 효율적으로 수집해야 함.
---

# 시나리오: quotes_02_tag_filter

전체 페이지에서 'inspirational' 태그를 가진 인용구만 모두 수집하세요.

[수집 항목]
- 인용구 원문 (text)
- 저자 이름 (author)
- 태그 목록 (tags)

결과는 'quotes_tag_inspirational.json' 및 지정된 경로에 JSON 배열 형태로 저장해주세요.
