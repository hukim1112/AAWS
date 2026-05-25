---
scenario_id: danawa_01_filter_search
site_name: Danawa
target_url: https://www.danawa.com/
difficulty: Level 4
expected_schema:
  type: array
  items:
    product_name: string
    lowest_price: integer
    spec_list:
    - string
evaluation_criteria:
  navigator_strategy: 다나와 특유의 복잡한 카테고리/상세검색 필터 UI (체크박스, 펼침 메뉴)의 DOM 구조를 정확히 뜯어내고
    Action Plan을 세워야 함.
  coder_strategy: iframe 또는 동적 폼 내의 체크박스 요소에 대한 클릭 이벤트를 안정적으로 작성하고, 쉼표 등으로 구분된 텍스트
    장벽을 깔끔하게 list로 파싱해야 함.
---

# 시나리오: danawa_01_filter_search

다나와에서 '게이밍 노트북'을 검색한 뒤, RAM 32GB 조건을 만족하는 제품 중 가장 인기있는 제품들을 정렬하여 상위 20개 제품의 정보를 수집하세요. 어떤 정보를 수집할 지 모델이 판단하고 실행합니다.