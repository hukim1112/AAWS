---
name: anti_bot_stealth
description: Cloudflare, 403 Forbidden 차단, User-Agent 위장, Playwright stealth 설정 및 봇 탐지 우회 플레이북
---

# 🛡️ 봇 탐지 우회 및 헤드리스 스텔스 플레이북 (Anti-Bot & Stealth)


웹사이트가 자동화 툴(Headless Chrome, Playwright, Puppeteer)을 감지하여 `403 Forbidden`, Cloudflare Turnstile, CAPTCHA 또는 빈 화면을 반환할 때 적용하는 우회 패턴입니다.

---

## 1. 봇 탐지 주요 원인과 진단

1. **`navigator.webdriver` 노출**: 기본 헤드리스 브라우저는 `window.navigator.webdriver === true`로 설정되어 즉시 탐지됩니다.
2. **비정상적인 Request Headers**: `User-Agent`에 `HeadlessChrome`이 포함되어 있거나, `Sec-Ch-Ua`, `Accept-Language` 헤더가 결여된 경우.
3. **지나치게 빠른 요청 간격**: 기계적인 0.1초 단위 요청 발생 시 IP 차단(Rate Limiting, HTTP 429).
4. **쿠키 및 세션 미수립**: 메인 페이지를 거치지 않고 내부 상세 URL이나 API에 직접 접근하는 경우.

---

## 2. 해결 패턴: Playwright Stealth 코드 스니펫

크롤링 스크립트 작성 시 아래 패턴을 적용하여 실제 사용자의 브라우저처럼 위장합니다:

```python
import asyncio
from playwright.async_api import async_playwright

async def run_stealth_crawler():
    async with async_playwright() as p:
        # 1. 자동화 탐지 플래그 비활성화
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-infobars"
            ]
        )
        
        # 2. 실제 일반 데스크톱 브라우저의 Context 구성
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="ko-KR",
            timezone_id="Asia/Seoul"
        )
        
        page = await context.new_page()
        
        # 3. navigator.webdriver 속성 은닉 (CDP 레벨 스텔스 주입)
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            window.chrome = { runtime: {} };
        """)
        
        # 4. 페이지 이동 및 안전한 대기
        await page.goto("https://target-site.com", wait_until="networkidle", timeout=30000)
        await asyncio.sleep(2)  # 동적 JS 렌더링 추가 여유 대기
        
        # 추출 로직 수행...
        content = await page.content()
        await browser.close()
        return content
```

---

## 3. 대규모 수집 시 Rate Limiting & 세션 유지

1. **랜덤 딜레이**: 요청 간 반드시 1.5초 ~ 3.5초 사이의 난수 대기를 삽입하세요:
   ```python
   import random, time
   time.sleep(random.uniform(1.5, 3.5))
   ```
2. **초기 세션 워밍업(Warming Up)**:
   - 곧바로 내부 데이터 페이지로 직행하지 말고, 메인 홈페이지(`https://target-site.com/`)를 먼저 1회 방문하여 세션 쿠키를 발급받은 뒤 대상 페이지로 이동하세요.
