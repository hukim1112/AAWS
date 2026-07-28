---
scenario_id: github_01_trending_scraping
site_name: GitHub
target_url: https://github.com/trending
difficulty: Level 3
expected_schema:
  type: array
  items:
    repo_name: string
    description:
      type: [string, "null"]
    language:
      type: [string, "null"]
    stars_today: integer
    total_stars: integer
    forks: integer
evaluation_criteria:
  navigator_strategy: >
    GitHub Trending 페이지의 렌더링 방식(Static SSR / Dynamic CSR)을 파악하고 적절한 DOM 분석 도구 및 셀렉터를 탐색해야 함.
  coder_strategy: >
    stars_today 값에서 숫자만 추출하고 (예: 1,234 stars today -> 1234), language나 description이 없는 경우 안전하게 null로 처리해야 함.
---

# 시나리오: github_01_trending_scraping

GitHub Trending 페이지(https://github.com/trending)에서 오늘의 인기 레포지토리 상위 25개의 정보를 수집하세요.

[수집 항목: JSON]
- repo_name: 레포지토리 전체 이름 (예: "owner/repo-name")
- description: 레포지토리 설명 (없으면 null)
- language: 프로그래밍 언어 (없으면 null)
- stars_today: 오늘 받은 스타 수 (숫자만)
- total_stars: 전체 스타 수 (숫자만)
- forks: 포크 수 (숫자만)

결과물은 지정된 경로에 JSON 파일 배열 형태로 저장하세요.
