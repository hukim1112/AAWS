---
name: scraper-advanced-skills
description: Advanced web scraping playbooks for anti-bot detection bypass, network API reverse engineering, and dynamic DOM diagnosis.
license: Apache-2.0
---

# Scraper Advanced Skill Hub

This skill package provides specialized, on-demand troubleshooting playbooks for complex scraping scenarios where standard static/dynamic DOM parsing fails (anti-bot protection, obfuscated SPAs, dynamic hydration, nested iframes).

## Skill Structure & Progressive Disclosure

When encountering obstacles during the 6-step workflow, inspect and read the relevant playbook on demand:

| Obstacle / Trigger Signal | Guide File | Key Strategies & Patterns |
|---|---|---|
| **Zero selector matches (0 items) / Empty extraction** | `app/agents/scraper/skills/dynamic_content_diagnosis.md` | Decision tree: hydration delay, `<iframe>` isolation, Shadow DOM, lazy loading, virtual DOM escalation |
| **Bot detection / Cloudflare / 403 Forbidden / 429** | `app/agents/scraper/skills/anti_bot_stealth.md` | Playwright stealth launch flags, `navigator.webdriver` masking, header spoofing, randomized delay, session warm-up |
| **Obfuscated DOM / Next.js SSR / Hidden JSON API** | `app/agents/scraper/skills/api_reverse_engineering.md` | Pre-flight `__NEXT_DATA__` extraction, Playwright network request sniffing (XHR/Fetch), high-speed direct API collection |

## Operating Principles
1. **Baseline First**: Always start with the lightweight 6-step pipeline (skeleton → section analysis → selector verification) defined in the system prompt.
2. **Signal-Driven Invocation**: Only consult these skill playbooks when concrete failure signals arise (e.g., selector count == 0, HTTP 403/429, obfuscated class names).
