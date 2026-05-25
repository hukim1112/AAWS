---
scenario_id: quotes_03_multi_step_crawling
site_name: Quotes to Scrape
target_url: http://quotes.toscrape.com
difficulty: Level 3
expected_schema: {}
evaluation_criteria:
  coder_strategy: Coder가 단일 파이썬 스크립트 안에서 데이터 수집 -> 파싱/빈도수 집계 -> 재수집(동적 URL 파라미터 활용)으로 이어지는 복합 로직을 스스로 구현해야 함.
  navigator_strategy: 기본 URL 구조를 파악하여 Coder가 '/tag/{tag_name}/' 패턴을 응용할 수 있도록 Blueprint에 명시해야 함.
---

# 시나리오: quotes_03_multi_step_crawling

다음 3단계 작업을 수행하세요. 이 작업은 별도의 분석 에이전트 없이 데이터를 다루는 Coder의 파이썬 스크립트 작성 능력을 평가합니다.

1. 'love' 태그를 가진 인용구를 전체 수집합니다.
2. 파이썬 코드를 통해 수집된 인용구에 달린 태그들의 빈도수를 집계하여 가장 많이 등장한 Top 10 태그를 추출합니다.
3. 추출된 Top 10 태그 각각에 대해 전체 인용구를 재수집하여, 태그별로 별도의 JSON 파일(예: quotes_tag_love.json)로 저장하세요.
