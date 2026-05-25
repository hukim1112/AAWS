---
scenario_id: quotes_02_tag_filter
site_name: Quotes to Scrape
target_url: http://quotes.toscrape.com
difficulty: Level 2
expected_schema:
  type: array
  items:
    text: string
    author: string
    tags:
    - string
evaluation_criteria:
  navigator_strategy: 모든 페이지를 긁어온 뒤 파이썬에서 if문으로 거르는 것이 아니라, 사이트 내의 '/tag/inspirational/'
    엔드포인트를 발견하여 이 주소의 페이지만 긁어오는 전략을 수립해야 함.
---

# 시나리오: quotes_02_tag_filter

전체 페이지에서 'inspirational' 태그를 가진 인용구만 모두 수집하세요.

[수집 항목]
- 인용구 원문 (text)
- 저자 이름 (author)
- 태그 목록 (tags)

결과는 'quotes_tag_inspirational.json' 파일에 저장해주세요.
