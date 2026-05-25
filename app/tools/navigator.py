import json
import re
from langchain.tools import tool, ToolRuntime
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from browser_use import Agent, Browser, ChatGoogle, ChatOpenAI
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage
from app.schemas import NavigatorContext
from app.tools.common import CostTracker
from app.prompts.navigator import BROWSER_AGENT_GUIDE

_cost_tracker = CostTracker()

@tool(parse_docstring=True)
async def get_page_structure(url: str, scraping_goal: str, wait_seconds: float = 2.0) -> str:
    """웹페이지 HTML을 내부 LLM이 직접 분석하여 CSS 셀렉터 결과만 반환합니다.
    
    Args:
        url: 분석할 웹페이지 URL
        scraping_goal: 수집하려는 데이터 설명
        wait_seconds: 페이지 로드 후 AJAX 대기 시간(초). 정적 사이트는 기본값(2초), AJAX가 많은 동적 사이트는 5~8초를 권장합니다.
    """
    print(f"\n📐 [get_page_structure] {url} (Goal: {scraping_goal}, Wait: {wait_seconds}s)")
    browser_cfg = BrowserConfig(headless=True, java_script_enabled=True)
    run_cfg = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, page_timeout=30000, delay_before_return_html=wait_seconds)

    try:
        async with AsyncWebCrawler(config=browser_cfg) as crawler:
            result = await crawler.arun(url=url, config=run_cfg)
    except Exception as e:
        return f"[Error] HTML 수집 실패: {e}\n→ browse_web을 사용하세요."

    raw_html = result.html or ""
    soup = BeautifulSoup(raw_html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "path", "header", "footer"]):
        tag.decompose()
        
    structured_html = soup.prettify()
    if not structured_html.strip():
        return "[Warning] HTML이 비어 있습니다. JS 로드 실패 가능성."

    structured_html = structured_html[:300000] # 토큰 제한
    analysis_llm = init_chat_model("google_genai:gemini-2.5-flash", temperature=0)
    
    prompt = f"""
    아래 HTML에서 "{scraping_goal}" 요소를 찾아 CSS 셀렉터를 반환하세요. 응답은 JSON만 출력.
    
    [주의사항]
    - 광고/스폰서 영역(PowerShopping, ad, sponsored 등)의 셀렉터는 절대 반환하지 마세요.
    - bridge, redirect, tracking, affiliate 등이 포함된 URL을 href로 가진 링크는 광고 링크이므로 무시하세요.
    - 실제 콘텐츠 영역(main, article, product list 등)에서만 셀렉터를 찾으세요.
    
    [HTML] {structured_html}
    [구조]
    {{"selectors": {{"필드": "셀렉터"}}, "samples": {{...}}, "navigate_to_next": "셀렉터 또는 null", "pagination": "방식", "confidence": "high/low"}}
    """
    resp = await analysis_llm.ainvoke([HumanMessage(prompt)])
    content = resp.content
    if isinstance(content, list): content = "".join([c.get("text", "") if isinstance(c, dict) else str(c) for c in content])
    
    json_match = re.search(r'\{.*\}', content, re.DOTALL)
    if json_match:
        return json.dumps(json.loads(json_match.group()), ensure_ascii=False, indent=2)
    return content

@tool(parse_docstring=True)
async def verify_selectors_with_samples(url: str, selectors_json: str) -> str:
    """찾아낸 CSS 셀렉터가 실제로 데이터를 가져오는지 검증합니다.
    
    Args:
        url: 검증할 웹페이지 URL
        selectors_json: JSON 문자열로 된 셀렉터 딕셔너리 예) '{"title": "a.title"}'
    """
    print(f"\n🔍 [verify_selectors] {url}")
    try: sel_dict = json.loads(selectors_json)
    except: return "[Error] 유효한 JSON 문자열 포맷이어야 합니다."
    
    results = {k: [] for k in sel_dict.keys()}
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=15000)
            await page.wait_for_timeout(2000)
            
            for k, sel in sel_dict.items():
                act_sel = sel
                attr_name = ""
                if "::attr(" in sel:
                    match = re.search(r'(.*?)::attr\((.*?)\)', sel)
                    if match:
                        act_sel, attr_name = match.group(1).strip(), match.group(2).strip()
                elements = await page.query_selector_all(act_sel)
                for el in elements[:5]:
                    val = await el.get_attribute(attr_name) if attr_name else await el.text_content()
                    if val: results[k].append(val.strip())
            await browser.close()
            
            out = []
            for k, v in results.items():
                out.append(f"[✅ OK] {k}: 샘플 {v}" if len(v) > 0 else f"[⚠️ FAILED] {k}: 매칭 0건")
            return "\\n".join(out)
    except Exception as e:
        return f"[Error] 브라우저 검증 중 오류: {e}"

@tool(parse_docstring=True)
async def browse_web(runtime: ToolRuntime[NavigatorContext], url: str, instruction: str, purpose: str = "", context: str = "") -> str:
    """동적 인터랙션 및 시각적 검증이 필요할 때 실제 브라우저로 웹을 제어합니다.
    
    Args:
        url: 이동할 URL (이어서 작업하려면 빈 문자열)
        instruction: 수행할 단일 마이크로 액션 (예: '더보기 버튼 클릭 후 변경된 URL 반환')
        purpose: 이 액션의 목적 (예: '쇼핑몰 리스트를 전부 펼치기 위해')
        context: Navigator가 파악한 현재까지의 전략적 상황
    """
    # Navigator가 전달한 전략적 컨텍스트 조합
    task_parts = [BROWSER_AGENT_GUIDE]
    if purpose:
        task_parts.append(f"[이 작업의 목적]\n{purpose}")
    if context:
        task_parts.append(f"[현재 상황 (상위 에이전트 제공)]\n{context}")
    if url:
        task_parts.append(f"[작업]\nNavigate to '{url}' and perform this task: {instruction}")
    else:
        task_parts.append(f"[작업]\nPerform this task on the current page: {instruction}")
    
    task = "\n\n".join(task_parts)

    llm = ChatOpenAI(model="gpt-4.1-mini")
    user_browser = getattr(runtime.context, "shared_browser", None)
    
    if user_browser:
        agent = Agent(task=task, llm=llm, browser=user_browser, calculate_cost=True)
        history = await agent.run(max_steps=15)
    else:
        tb = Browser(headless=True)
        agent = Agent(task=task, llm=llm, browser=tb, calculate_cost=True)
        history = await agent.run(max_steps=15)
        await tb.stop()
    
    # 비용 기록
    _cost_tracker.record_usage(instruction[:50], history.usage)
    
    return history.final_result() or "결과 반환 없음"
