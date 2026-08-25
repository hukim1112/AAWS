---
scenario_id: danawa_02_deep_table_parsing
site_name: Danawa
target_url: https://www.danawa.com/
difficulty: Level 4.5
expected_schema:
  type: object
  required: ["search_keyword", "target_product", "top_5_cheapest_malls"]
  properties:
    search_keyword:
      type: string
    target_product:
      type: object
      required: ["product_name", "product_url"]
      properties:
        product_name:
          type: string
        product_url:
          type: string
        min_price:
          type: integer
    top_5_cheapest_malls:
      type: array
      items:
        type: object
        required: ["mall_name", "final_price"]
        properties:
          mall_name:
            type: string
          final_price:
            type: integer
          base_price:
            type: integer
          delivery_fee:
            type: integer
          delivery_info:
            type: string
          link:
            type: string
evaluation_criteria:
  navigator_strategy: >
    검색 결과 첫 번째 상품 상세 페이지 진입 후 '배송비 포함' 옵션 및 가격비교 테이블(ul.list__mall-price)의 계층 구조를 분석해야 함.
  coder_strategy: >
    배송비가 포함된 최종 가격(final_price)을 기준으로 최저가 입점몰 상위 5곳의 정보(mall_name, final_price integer 변환, link 등)를 안정적으로 수집하여 저장해야 함.
---

# 시나리오: danawa_02_deep_table_parsing

다나와(danawa.com)에서 '노트북'을 검색한 뒤, 검색 결과에서 현재 판매 중인(품절이 아닌) 첫 번째 상품의 상세 페이지로 이동하세요. 
상세 페이지 내 배송비가 포함된 최종 가격을 기준으로 가장 저렴한 입점몰 상위 5곳의 정보를 수집하세요.

[수집 및 JSON 출력 구조 가이드]
- `search_keyword`: 검색 키워드 ("노트북", 필수)
- `target_product`: 선택한 상품 객체 (필수)
  - `product_name`: 상품명 (필수)
  - `product_url`: 상세 페이지 URL (필수)
  - `min_price`: 최저가 (정수, 선택)
- `top_5_cheapest_malls`: 배송비 포함 최종 최저가 상위 5곳 입점몰 목록 (배열, 필수)
  - `mall_name`: 쇼핑몰명 (필수)
  - `final_price`: 배송비 포함 최종 가격 (정수, 필수)
  - `base_price`: 상품 기본 가격 (정수)
  - `delivery_fee`: 배송비 (정수, 무료배송은 0)
  - `delivery_info`: 배송 조건 문자열 (예: "무료배송")
  - `link`: 구매 이동 링크 URL

결과물은 지정된 경로에 위 스키마 구조의 JSON 객체 형태로 저장하세요.