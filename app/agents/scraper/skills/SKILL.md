---
name: scraper-advanced-skills
description: Advanced web scraping playbooks for anti-bot detection bypass and network API reverse engineering.
license: Apache-2.0
---

# Scraper Advanced Skill Hub

본 스킬 패키지는 일반적인 정적/동적 DOM 파싱 절차로 해결하기 어려운 **특수 장애 상황(봇 탐지, Cloudflare 차단, 난독화된 SPA 등)**에 직면했을 때 에이전트가 온디맨드로 참조하는 고급 문제 해결 플레이북입니다.

## Skill Structure & Progressive Disclosure

문제가 발생했을 때 필요한 가이드만 `file_read`로 선별적으로 읽어 전략을 수립합니다:

| 문제 상황 (Obstacle) | 가이드 파일 | 주요 해결 전략 및 패턴 |
|---|---|---|
| **봇 탐지 / Cloudflare 차단 / 403 Forbidden** | `app/agents/scraper/skills/anti_bot_stealth.md` | `playwright-stealth` 주입, User-Agent 위장, 대기 전략, 세션 쿠키 보존 |
| **난독화된 DOM / 무한 렌더링 / API 직수집** | `app/agents/scraper/skills/api_reverse_engineering.md` | 네트워크 요청 가로채기(XHR/Fetch), 숨겨진 JSON 엔드포인트 역추적, 직수집 |

## 원칙
1. **기본 우선 원칙**: 일반적인 웹페이지는 기본 6단계 파이프라인(스켈레톤 ➔ 섹션 분석 ➔ 셀렉터 검증)으로 빠르고 가볍게 처리합니다.
2. **에러 기반 진입**: `verify_selectors` 결과가 0건이거나 HTTP 403/429 등 차단 신호가 감지된 경우에만 이 스킬을 호출합니다.
