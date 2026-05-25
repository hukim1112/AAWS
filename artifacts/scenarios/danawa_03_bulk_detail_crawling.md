---
scenario_id: danawa_03_bulk_detail_crawling
site_name: Danawa
target_url: https://prod.danawa.com/list/?cate=112782
difficulty: Level 5
expected_schema:
  type: array
  items:
    product_name: string
    price: integer
    switch_type: string
    connection_type: string
    review_count: integer
evaluation_criteria:
  navigator_strategy: 목록 페이지의 페이지네이션 방식과 개별 상품 상세 페이지의 DOM 구조를 모두 파악하는 '2단계(List -> Detail) Blueprint'를 설계해야 함.
  coder_strategy: 안정적인 대량 수집을 위해 100개의 상품 URL을 먼저 확보한 뒤, 재시도(Retry) 로직과 적절한 딜레이를 포함하여 상세 페이지들을 순회하는 견고한 크롤링 코드를 작성해야 함.
---

# 시나리오: danawa_03_bulk_detail_crawling

다나와 컴퓨터 카테고리의 '키보드' 목록(인기상품순 기본 정렬)에서 상위 100개 제품의 상세 스펙을 대량으로 수집하세요.

작업은 두 단계로 이루어집니다:
1. 목록 페이지에서 상위 100개 키보드의 '상세 페이지 링크(URL)'를 수집합니다. (1페이지당 보통 30개가 노출되므로, 페이지네이션을 처리해야 합니다.)
2. 수집한 100개의 상세 페이지 URL을 순회하면서 각 키보드의 상세 스펙을 추출합니다.

[수집 항목: JSON]
- product_name: 상품명
- price: 최저가 (숫자만)
- switch_type: 스위치 종류 (예: '청축', '갈축', '광축' 등. 명시되지 않은 경우 null)
- connection_type: 연결 방식 (예: '유선', '무선', '블루투스' 등)
- review_count: 상품평(리뷰) 개수 (숫자만)

결과물은 'danawa_03_bulk_detail_crawling.json' 파일에 배열 형태로 저장하세요. 다나와는 동적 로딩과 봇 차단 로직이 있을 수 있으므로, 에이전트는 코드에 적절한 예외 처리(try-except)와 지연 시간(sleep/wait)을 반드시 포함해야 합니다.
