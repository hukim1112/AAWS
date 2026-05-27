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

# ═══════════════════════════════════════════════════════
# DOM 스켈레톤 뷰어 (Lesson 10: 정보의 압축 원칙 적용)
# ═══════════════════════════════════════════════════════

def _build_skeleton(element, depth: int = 0, max_depth: int = 6, sibling_limit: int = 3) -> list[str]:
    """HTML 요소를 재귀적으로 순회하며 구조 맵을 생성합니다.
    
    - 같은 태그+클래스가 반복되면 그룹으로 축약 (예: li.prod_item ×30)
    - 각 노드에 첫 번째 텍스트와 주요 속성(href, src 등)을 샘플로 표시
    - 광고/실제 상품 등 구조적 차이가 있으면 별도 그룹으로 분리되어 자연스럽게 드러남
    """
    from bs4 import Tag
    from collections import Counter
    
    if depth > max_depth or not hasattr(element, 'children'):
        return []
    
    lines = []
    indent = "  " * depth
    
    # 자식 요소를 시그니처(tag+class)별로 그룹화
    children = [c for c in element.children if isinstance(c, Tag)]
    signature_groups = {}  # {signature: [elements]}
    order = []  # 등장 순서 보존
    
    for child in children:
        cls = " ".join(child.get("class", []))
        sig = f"{child.name}.{cls}" if cls else child.name
        if sig not in signature_groups:
            signature_groups[sig] = []
            order.append(sig)
        signature_groups[sig].append(child)
    
    for sig in order:
        group = signature_groups[sig]
        representative = group[0]
        count = len(group)
        
        # 주요 속성 수집 (href, src 등)
        attrs = []
        href = representative.get("href", "")
        if href:
            # URL은 앞 80자만 표시
            attrs.append(f'href="{href[:80]}{"..." if len(href) > 80 else ""}"')
        src = representative.get("src", "")
        if src:
            attrs.append(f'src="{src[:60]}..."')
        id_attr = representative.get("id", "")
        if id_attr:
            attrs.append(f'id="{id_attr}"')
        
        # 직접 텍스트 (자식 태그 제외) 샘플
        direct_text = representative.get_text(strip=True)[:60] if representative.string or (not list(representative.children) or len(list(representative.children)) <= 2) else ""
        
        # 자식 수
        child_count = len([c for c in representative.children if isinstance(c, Tag)])
        
        # 한 줄 생성
        attr_str = f" [{', '.join(attrs)}]" if attrs else ""
        text_str = f' → "{direct_text}"' if direct_text and len(direct_text) > 1 else ""
        count_str = f" (×{count})" if count > 1 else ""
        children_str = f" (children: {child_count})" if child_count > 0 else ""
        
        line = f"{indent}├─ {sig}{count_str}{attr_str}{children_str}{text_str}"
        lines.append(line)
        
        # 반복 그룹이면: 대표 1개 + (구조가 다른 것이 있으면) 변형 1개만 펼침
        if count > 1:
            # 대표 요소만 재귀 (sibling_limit으로 제한)
            child_lines = _build_skeleton(representative, depth + 1, max_depth, sibling_limit)
            lines.extend(child_lines)
            
            # 구조적 변형 탐지: 두 번째 요소의 시그니처가 다르면 별도 표시
            if count > 1 and len(group) > 1:
                second = group[1]
                second_child_sigs = [f"{c.name}.{' '.join(c.get('class', []))}" for c in second.children if isinstance(c, Tag)]
                first_child_sigs = [f"{c.name}.{' '.join(c.get('class', []))}" for c in representative.children if isinstance(c, Tag)]
                if second_child_sigs != first_child_sigs:
                    lines.append(f"{indent}  ⚠️ 구조 변형 발견 — 2번째 {sig}의 자식 구조가 다름:")
                    variant_lines = _build_skeleton(second, depth + 1, max_depth, sibling_limit)
                    lines.extend(variant_lines)
        else:
            child_lines = _build_skeleton(representative, depth + 1, max_depth, sibling_limit)
            lines.extend(child_lines)
    
    return lines


@tool(parse_docstring=True)
async def extract_dom_skeleton(url: str, root_selector: str = "body", max_depth: int = 6, wait_seconds: float = 3.0) -> str:
    """페이지의 DOM 트리 구조를 간결한 스켈레톤(구조 맵)으로 반환합니다.
    
    300KB의 HTML 원문 대신, 태그/클래스/ID/자식 수/샘플 텍스트만 추출한 경량 트리(~5KB)를 제공합니다.
    이를 통해 반복되는 노드 그룹의 구조적 차이(예: 광고 vs 실제 상품, 일반 행 vs 헤더 행)를
    LLM이 효율적으로 식별할 수 있습니다.
    
    [사용 시나리오]
    - get_page_structure가 잘못된 셀렉터를 반환할 때 → 이 도구로 DOM 구조를 직접 확인
    - 복잡한 사이트에서 광고/실제 콘텐츠의 구조적 차이를 파악해야 할 때
    - 페이지네이션, 탭, 더보기 등 동적 UI 요소의 DOM 위치를 파악해야 할 때
    
    Args:
        url: 분석할 웹페이지 URL
        root_selector: 분석을 시작할 루트 요소의 CSS 셀렉터 (기본값: body). 특정 영역만 분석하고 싶을 때 사용합니다. (예: '.main_prodlist', '#content')
        max_depth: DOM 트리 탐색 최대 깊이 (기본값: 6). 너무 깊으면 출력이 길어지고, 너무 얕으면 세부 구조를 놓칩니다.
        wait_seconds: 페이지 로드 후 AJAX 대기 시간(초). 동적 사이트는 5~8초를 권장합니다.
    """
    print(f"\n🦴 [extract_dom_skeleton] {url} (root: {root_selector}, depth: {max_depth}, wait: {wait_seconds}s)")
    
    browser_cfg = BrowserConfig(headless=True, java_script_enabled=True)
    run_cfg = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, page_timeout=30000, delay_before_return_html=wait_seconds)

    try:
        async with AsyncWebCrawler(config=browser_cfg) as crawler:
            result = await crawler.arun(url=url, config=run_cfg)
    except Exception as e:
        return f"[Error] HTML 수집 실패: {e}\n→ browse_web으로 시각적 분석을 시도하세요."

    raw_html = result.html or ""
    soup = BeautifulSoup(raw_html, "html.parser")
    
    # 불필요한 비콘텐츠 태그만 제거 (script, style 등)
    # ⚠️ 광고 등 특정 클래스는 절대 제거하지 않음 — LLM이 구조적 차이를 보고 스스로 판단해야 함
    for tag in soup(["script", "style", "noscript", "svg", "path", "link", "meta"]):
        tag.decompose()
    
    # 루트 요소 탐색
    root = soup.select_one(root_selector)
    if not root:
        return f"[Warning] '{root_selector}' 셀렉터에 해당하는 요소를 찾지 못했습니다.\n사용 가능한 최상위 요소: {[t.name + ('.' + '.'.join(t.get('class', [])) if t.get('class') else '') for t in soup.body.children if hasattr(t, 'name') and t.name][:10]}"
    
    # 스켈레톤 생성
    skeleton_lines = _build_skeleton(root, depth=0, max_depth=max_depth)
    
    root_cls = " ".join(root.get("class", []))
    root_sig = f"{root.name}.{root_cls}" if root_cls else root.name
    header = f"🦴 DOM Skeleton: {url}\n📍 Root: {root_sig}\n{'─' * 60}"
    
    skeleton_text = header + "\n" + "\n".join(skeleton_lines)
    
    # 크기 제한 (안전장치)
    if len(skeleton_text) > 15000:
        skeleton_text = skeleton_text[:15000] + "\n\n⚠️ [출력 잘림] max_depth를 줄이거나 root_selector를 더 구체적으로 지정하세요."
    
    print(f"  → 스켈레톤 생성 완료: {len(skeleton_lines)}줄, {len(skeleton_text)}자")
    return skeleton_text

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
    
    # 에러 페이지 조기 감지: LLM 호출 비용을 절약하기 위해 명확한 에러 시그널을 사전 필터링
    page_title = soup.title.string.strip() if soup.title and soup.title.string else ""
    page_text_sample = soup.get_text(strip=True)[:500].lower()
    error_signals = ["페이지를 찾을 수 없습니다", "404", "not found", "page not found", 
                     "오류가 발생", "error", "접근이 거부", "403 forbidden", "서비스 점검"]
    detected_errors = [sig for sig in error_signals if sig in page_text_sample]
    if detected_errors:
        return (f"[Error] 에러 페이지 감지: {', '.join(detected_errors)}. "
                f"페이지 제목: '{page_title}'. "
                f"→ URL이 올바른지 확인하세요. browse_web으로 올바른 URL을 확보하거나 URL 인코딩을 점검하세요.")
    
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
    """찾아낸 CSS 셀렉터가 실제로 데이터를 가져오는지 브라우저로 검증합니다.
    기본적으로 요소의 텍스트를 반환하며, 속성(href, src 등)이 필요하면 ::attr() 구문을 사용하세요.
    
    Args:
        url: 검증할 웹페이지 URL
        selectors_json: JSON 문자열로 된 셀렉터 딕셔너리. 텍스트 추출 예) '{"title": "a.title"}'. 속성 추출 시 ::attr() 구문 사용 예) '{"link": "a.title::attr(href)", "image": "img.thumb::attr(src)"}'
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
    
    # 실행 요약: Navigator가 browse_web의 내부 동작을 파악하고 디버깅 가능
    steps = history.number_of_steps()
    final_urls = history.urls()
    final_url = final_urls[-1] if final_urls else "알 수 없음"
    success = history.is_successful()
    result_text = history.final_result() or "결과 반환 없음"
    
    summary = f"[browse_web 실행 요약] 스텝: {steps}/{15}, 성공: {'✅' if success else '❌'}, 최종 URL: {final_url}\n"
    return summary + result_text

