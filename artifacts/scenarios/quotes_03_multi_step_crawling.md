---
scenario_id: quotes_03_multi_step_crawling
site_name: Quotes to Scrape
target_url: http://quotes.toscrape.com
difficulty: Level 3
expected_schema:
  type: object
evaluation_criteria:
  navigator_strategy: >
    기본 사이트 구조 및 '/tag/{tag_name}/page/{N}/' 동적 파라미터 구조를 분석하여 다단계 수집 전략을 도출해야 함.
  coder_strategy: >
    단일 스크립트 안에서 1단계('love' 인용구 14건 수집) ➔ 2단계(태그 빈도수 Top 10 집계) ➔ 3단계(Top 10 태그별 전체 인용구 동적 재수집 및 태그별 개별 JSON 파일 저장)로 이어지는 복합 파이프라인을 자율적으로 완결해야 함.
---

# 시나리오: quotes_03_multi_step_crawling

다음 3단계 작업을 수행하세요.

1. 'love' 태그를 가진 인용구를 전체 수집합니다.
2. 파이썬 코드를 통해 수집된 인용구에 달린 태그들의 빈도수를 집계하여 가장 많이 등장한 Top 10 태그를 추출합니다.
3. 추출된 Top 10 태그 각각에 대해 전체 인용구를 재수집하여, 태그별로 별도의 JSON 파일(예: quotes_tag_love.json)로 저장하세요.
