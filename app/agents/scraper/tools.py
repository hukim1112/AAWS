"""
===============================================================================
[AAWS Tools] Scraper — 네비게이팅 및 코딩 14종 통합 도구 바인딩
===============================================================================
Navigator(탐색/인터랙션/브라우징) 6종 + Common(파일/코딩/검색) 8종 = 14종
===============================================================================
"""

from app.tools.navigator import (
    extract_dom_skeleton,
    get_page_section,
    verify_selectors,
    interact_page,
    take_screenshot,
    browse_web,
    PlaywrightManager,
)

from app.tools.common import (
    file_writer,
    file_read,
    file_edit,
    grep_search,
    glob_search,
    bash_command,
    web_search,
    web_fetch,
)

# 🕷️ Scraper용 도구 바인딩: 네비게이팅(5종) + L3(1종) + 코딩/파일탐색(8종) = 14종
tools_scraper = [
    # L1 + L2 네비게이팅 도구
    extract_dom_skeleton,
    get_page_section,
    verify_selectors,
    interact_page,
    take_screenshot,
    # L3 browser-use 자율 탐색 에이전트
    browse_web,
    # 코딩 및 파일 탐색 도구 (common.py)
    file_writer,
    file_read,
    file_edit,
    grep_search,
    glob_search,
    bash_command,
    web_search,
    web_fetch,
]

__all__ = [
    "tools_scraper",
    "extract_dom_skeleton",
    "get_page_section",
    "verify_selectors",
    "interact_page",
    "take_screenshot",
    "browse_web",
    "PlaywrightManager",
]
