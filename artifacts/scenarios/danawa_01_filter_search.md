---
scenario_id: danawa_01_filter_search
site_name: Danawa
target_url: https://www.danawa.com/
difficulty: Level 4
expected_schema:
  type: array
  items:
    type: object
    required: ["product_name", "lowest_price", "spec_list"]
    properties:
      product_name:
        type: string
      lowest_price:
        type: integer
      spec_list:
        type: array
        items:
          type: string
evaluation_criteria:
  navigator_strategy: >
    다나와 검색 및 노트북 카테고리 진입 후 RAM 32GB 필터 요소(체크박스/라벨) 및 광고 요소('prod_ad_item')를 제외하는 목록 구조를 파악해야 함.
  coder_strategy: >
    Playwright 또는 안정적인 브라우저 제어를 통해 검색어 입력 ➔ RAM 32GB 필터 적용 ➔ 리스트 갱신 대기를 수행하고, 상위 20개 제품의 제품명, 최저가(원/콤마 제거 integer), 스펙 리스트(슬래시/구분자 분리 list)를 수집해야 함.
---

# 시나리오: danawa_01_filter_search

다나와에서 '게이밍 노트북'을 검색한 뒤, RAM 32GB 조건을 만족하는 제품 중 가장 인기있는 제품들을 정렬하여 상위 20개 제품의 정보를 수집하세요.

[수집 항목]
- product_name (string): 제품명
- lowest_price (integer): 최저 가격 (숫자만)
- spec_list (array): 주요 스펙 목록 (슬래시 등으로 분리된 텍스트 리스트)

결과물은 지정된 경로에 JSON 파일 배열 형태로 저장하세요.