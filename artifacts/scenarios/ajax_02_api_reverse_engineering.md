---
scenario_id: ajax_02_api_reverse_engineering
site_name: Scrape This Site (AJAX)
target_url: https://www.scrapethissite.com/pages/ajax-javascript/
difficulty: Level 2.5
expected_schema:
  type: array
  items:
    type: object
    required: ["year", "title", "awards"]
    properties:
      year:
        type: integer
      title:
        type: string
      awards:
        type: integer
evaluation_criteria:
  navigator_strategy: >
    무거운 브라우저 렌더링 대신, 백엔드 비동기 API 엔드포인트('https://www.scrapethissite.com/pages/ajax-javascript/?ajax=true&year=YYYY')를 역공학하여 파악해야 함.
  coder_strategy: >
    Playwright 대신 가벼운 requests.get(params={'ajax': 'true', 'year': year})를 활용하여 2010년부터 2015년까지 6년치 영화 목록(총 87건)을 초고속으로 수집하고 year, title, awards(integer) 스키마를 만족해야 함.
---

# 시나리오: ajax_02_api_reverse_engineering

2010년부터 2015년까지 총 6년치 영화 데이터를 가장 빠르고 효율적으로 수집하세요.
(단, Playwright 등 무거운 브라우저 렌더링 생략이 가능하다면 생략할 것)

[수집 항목]
- year (int)
- title (string)
- awards (int)

통합된 한 개의 JSON 파일로 저장해주세요.
