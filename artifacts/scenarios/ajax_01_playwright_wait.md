---
scenario_id: ajax_01_playwright_wait
site_name: Scrape This Site (AJAX)
target_url: https://www.scrapethissite.com/pages/ajax-javascript/
difficulty: Level 1.5
expected_schema:
  type: array
  items:
    type: object
    required: ["year", "title", "is_best_picture"]
    properties:
      year:
        type: integer
      title:
        type: string
      is_best_picture:
        type: boolean
evaluation_criteria:
  navigator_strategy: >
    연도별 탭 클릭 시 발생하는 비동기 AJAX 렌더링 지연과 로딩 스피너의 존재를 인지하고 대기 전략을 수립해야 함.
  coder_strategy: >
    무조건적인 sleep() 대신 Playwright의 명시적 대기(wait_for_selector 로딩 스피너 hidden 및 table-body tr.film visible)를 적용하여 2015, 2014, 2013년의 'Best Picture' 오스카 수상작(총 3건)을 정확히 필터링 수집해야 함.
---

# 시나리오: ajax_01_playwright_wait

화면에 있는 연도 탭(2015, 2014, 2013)을 눌러 하단에 나오는 영화 정보 테이블을 크롤링하세요.
각 연도별로 'Best Picture' 아이콘이 있는 영화만 수집해야 합니다.

[수집 항목]
- year (int)
- title (string)
- is_best_picture (boolean: true)

통합된 결과를 JSON 배열로 저장해주세요.
