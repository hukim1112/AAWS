---
scenario_id: ajax_02_api_reverse_engineering
site_name: Scrape This Site (AJAX)
target_url: https://www.scrapethissite.com/pages/ajax-javascript/
difficulty: Level 2.5
expected_schema:
  type: array
  items:
    year: integer
    title: string
    awards: integer
evaluation_criteria:
  navigator_strategy: 네트워크 탭을 분석하여 '/ajax-javascript/?ajax=true&year=YYYY' 라는 백엔드
    API 엔드포인트를 찾아내야 함.
  coder_strategy: UI 렌더러를 쓰지 않고 requests.get() 반복문으로 JSON 응답을 직접 파싱하는 효율적인 백엔드 호출
    스크립트를 작성해야 함.
---

# 시나리오: ajax_02_api_reverse_engineering

2010년부터 2015년까지 총 6년치 영화 데이터를 가장 빠르고 효율적으로 수집하세요.
(단, Playwright 등 무거운 브라우저 렌더링 생략이 가능하다면 생략할 것)

[수집 항목]
- year (int)
- title (string)
- awards (int)

통합된 한 개의 JSON 파일로 저장해주세요.
