---
scenario_id: danawa_02_deep_table_parsing
site_name: Danawa
target_url: https://www.danawa.com/
difficulty: Level 4.5
expected_schema:
  type: array
  items:
    mall_name: string
    final_price: integer
    card_discount: string
evaluation_criteria:
  navigator_strategy: 상품 상세 페이지 진입 후 탭 및 테이블 구조 분석, '더보기' 버튼을 열어야만 데이터(DOM)가 존재한다는
    사실 인식.
  coder_strategy: 가격 정보 중 '원' 글자 및 콤마를 제거하여 integer로 변환하고, 테이블 내 계층 구조를 안전하게 순회하는
    코드를 작성해야 함.
---

# 시나리오: danawa_02_deep_table_parsing

다나와(danawa.com)에서 '노트북'을 검색한 뒤, 검색 결과에서 현재 판매 중인(품절이 아닌) 첫 번째 상품의 상세 페이지로 이동하세요. 상세 페이지 내 배송비가 포함된 최종 가격을 기준으로 가장 저렴한 입점몰 상위 5곳의 정보를 수집하세요.