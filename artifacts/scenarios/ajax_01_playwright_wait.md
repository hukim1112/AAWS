---
scenario_id: ajax_01_playwright_wait
site_name: Scrape This Site (AJAX)
target_url: https://www.scrapethissite.com/pages/ajax-javascript/
difficulty: Level 1.5
expected_schema:
  type: array
  items:
    year: integer
    title: string
    is_best_picture: boolean
evaluation_criteria:
  navigator_strategy: AJAX 로딩 지연 시간을 인지하고, 요소가 렌더링될 때까지 기다려야 한다는 점을 Blueprint에 명시해야
    함.
  coder_strategy: '클릭 후 무조건 sleep()을 주는 것이 아니라, Playwright를 사용하여 데이터 렌더링(예: wait_for_selector)을
    정확히 대기(Wait)하는 코드를 작성해야 함.'
---

# 시나리오: ajax_01_playwright_wait

화면에 있는 연도 탭(2015, 2014, 2013)을 눌러 하단에 나오는 영화 정보 테이블을 크롤링하세요.
각 연도별로 'Best Picture' 아이콘이 있는 영화만 수집해야 합니다.

[수집 항목]
- year (int)
- title (string)
- is_best_picture (boolean: true)

통합된 결과를 JSON 배열로 저장해주세요.
