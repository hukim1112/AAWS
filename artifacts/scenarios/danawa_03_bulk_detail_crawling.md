---
scenario_id: danawa_03_bulk_detail_crawling
site_name: Danawa
target_url: https://prod.danawa.com/list/?cate=112782
difficulty: Level 5
expected_schema:
  type: array
  items:
    type: object
    required: ["product_name", "price", "switch_type", "connection_type", "review_count"]
    properties:
      product_name:
        type: string
      price:
        type: integer
      switch_type:
        type: [string, "null"]
      connection_type:
        type: [string, "null"]
      review_count:
        type: integer
evaluation_criteria:
  navigator_strategy: >
    키보드 카테고리 목록의 페이지네이션(1~4페이지)과 개별 상품 상세 페이지의 스펙 영역 DOM 구조를 연계하는 2단계(List -> Detail) 수집 파이프라인 Blueprint를 설계해야 함.
  coder_strategy: >
    안정적인 대량 수집을 위해 상위 100개 상품 URL을 확보한 뒤, 적절한 Rate Limiting(sleep/delay)과 예외 처리를 포함하여 상세 페이지들을 순회하고, switch_type/connection_type/review_count를 정확히 파싱해야 함.
---

# 시나리오: danawa_03_bulk_detail_crawling

다나와 컴퓨터 카테고리의 '키보드' 목록(인기상품순 기본 정렬)에서 상위 100개 제품의 상세 스펙을 대량으로 수집하세요.

작업은 두 단계로 이루어집니다:
1. 목록 페이지에서 상위 100개 키보드의 '상세 페이지 링크(URL)'를 수집합니다. (1페이지당 30개씩 노출되므로 페이지네이션 처리)
2. 수집한 100개의 상세 페이지 URL을 순회하면서 각 키보드의 상세 스펙을 추출합니다.

[수집 항목: JSON]
- product_name: 상품명
- price: 최저가 (숫자만)
- switch_type: 스위치 종류 (예: '청축', '갈축', '저소음 바다축' 등. 명시되지 않은 경우 null)
- connection_type: 연결 방식 (예: '유선', '무선', '유선+무선' 등. 없으면 null)
- review_count: 상품평(리뷰) 개수 (숫자만)

결과물은 지정된 경로에 JSON 파일 배열 형태로 저장하세요.
