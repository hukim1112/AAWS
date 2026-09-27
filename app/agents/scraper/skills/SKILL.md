---
name: scraper-advanced-skills
description: Advanced web scraping playbooks for anti-bot detection bypass, network API reverse engineering, and dynamic DOM diagnosis.
license: Apache-2.0
---

# Scraper Advanced Skill Hub

This skill package provides specialized, on-demand troubleshooting playbooks for complex scraping scenarios where standard static/dynamic DOM parsing fails (anti-bot protection, obfuscated SPAs, dynamic hydration, nested iframes).

## Skill Structure & Progressive Disclosure

Choose a playbook when the task requirements or observed page behavior match its scope. Read its entrypoint before applying it:

| Obstacle / Trigger Signal | Guide File | Key Strategies & Patterns |
|---|---|---|
| **Zero selector matches (0 items) / Empty extraction** | `app/agents/scraper/skills/dynamic_content_diagnosis.md` | Decision tree: hydration delay, `<iframe>` isolation, Shadow DOM, lazy loading, virtual DOM escalation |
| **Bot detection / Cloudflare / 403 Forbidden / 429** | `app/agents/scraper/skills/anti_bot_stealth.md` | Playwright stealth launch flags, `navigator.webdriver` masking, header spoofing, randomized delay, session warm-up |
| **Obfuscated DOM / Next.js SSR / Hidden JSON API** | `app/agents/scraper/skills/api_reverse_engineering.md` | Pre-flight `__NEXT_DATA__` extraction, Playwright network request sniffing (XHR/Fetch), high-speed direct API collection |

## Operating Principles
1. **Evidence-Based Selection**: Use the default DOM workflow when appropriate. API or embedded-data playbooks may replace DOM analysis when observations support that strategy.
2. **Progressive Loading**: Read relevant playbooks and their required references only. New skills are listed in the catalog automatically; this table is not an exhaustive registry.
3. **Bounded Recovery**: Apply a relevant skill to recoverable failures within the task budget. Report missing authorization, required human intervention, or exhausted recovery attempts to the supervisor.
