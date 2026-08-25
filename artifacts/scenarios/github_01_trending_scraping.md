---
scenario_id: github_01_trending_scraping
site_name: GitHub
target_url: https://github.com/trending
difficulty: Level 3
expected_schema:
  type: array
  items:
    type: object
    required: ["repo_name", "description", "language", "stars_today", "total_stars", "forks"]
    properties:
      repo_name:
        type: string
      description:
        type: [string, "null"]
      language:
        type: [string, "null"]
      stars_today:
        type: integer
      total_stars:
        type: integer
      forks:
        type: integer
evaluation_criteria:
  navigator_strategy: >
    GitHub Trending 페이지의 DOM 구조('article.Box-row')를 분석하고, description이나 language가 명시되지 않은 레포지토리가 존재할 수 있음을 인지해야 함.
  coder_strategy: >
    description과 language의 결측치를 안전하게 null로 처리하고, stars_today("1,234 stars today"), total_stars, forks 텍스트에서 콤마(,)와 문자열을 정제하여 순수 integer 타입으로 변환 수집해야 함.
---

# 시나리오: github_01_trending_scraping

GitHub Trending 페이지(https://github.com/trending)에서 오늘의 인기 레포지토리 상위 목록을 수집하세요.

[수집 항목: JSON]
- repo_name: 레포지토리 전체 이름 (예: "owner/repo-name")
- description: 레포지토리 설명 (없으면 null)
- language: 프로그래밍 언어 (없으면 null)
- stars_today: 오늘 받은 스타 수 (숫자만)
- total_stars: 전체 스타 수 (숫자만)
- forks: 포크 수 (숫자만)

결과물은 지정된 경로에 JSON 파일 배열 형태로 저장하세요.
