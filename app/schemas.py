import json
from typing import Optional, Any
from pydantic import BaseModel, Field, field_validator
from dataclasses import dataclass, field

# ==========================================
# 1. 멀티에이전트 Blueprint 파서 데이터 모델
# ==========================================
class PageLayer(BaseModel):
    """하나의 탐색 계층을 표현하는 단위 블록"""
    layer_name: str = Field(description="이 계층의 역할 이름 (예: '기사 목록', '상품 상세')")
    url_pattern: str = Field(description="이 계층의 URL 구조 예시 또는 진입점 URL")
    container_selector: Optional[str] = Field(default=None, description="반복 항목의 부모 컨테이너 CSS 셀렉터 (예: 'table.mall_list tbody tr'). Coder는 이 셀렉터로 루프를 돌고, selectors의 각 필드를 하위에서 찾습니다.")
    selectors: dict[str, str] = Field(description="이 계층에서 수집할 데이터의 CSS 셀렉터 딕셔너리. CSS 셀렉터로 안정적으로 표현 가능한 필드만 포함합니다.")
    extraction_notes: Optional[dict[str, str]] = Field(default=None, description="CSS 셀렉터로 표현할 수 없는 필드의 추출 전략을 자연어로 기술합니다. 키는 필드명, 값은 Coder가 구현할 수 있는 구체적 추출 방법입니다. (예: {'switch_type': 'table.spec_tbl의 th에서 스위치 포함 행의 td 값. 없으면 null', 'connection_type': 'table.spec_tbl의 th에서 연결 포함 행의 td 값'})")
    pre_actions: Optional[list[str]] = Field(default=None, description="데이터 로드 전 수행해야 할 브라우저 액션 목록 (예: ['더보기 버튼(.btn_list_more) 클릭', '탭 전환: 쇼핑몰별 최저가']). 순서대로 실행됩니다.")
    navigate_to_next: Optional[str] = Field(default=None, description="다음 계층으로 이동하는 링크의 CSS 셀렉터. 마지막 계층이면 무조건 None.")
    pagination_method: Optional[str] = Field(default=None, description="페이지네이션 방식 (URL파라미터 / AJAX버튼 / 무한스크롤 / None)")
    pagination_details: Optional[str] = Field(default=None, description="페이지네이션 구현 세부사항. URL파라미터면 패턴(예: '?page={n}'), AJAX버튼이면 JS 함수명(예: 'movePage(n)') 또는 버튼 셀렉터, 무한스크롤이면 트리거 조건. Coder가 정확히 구현할 수 있도록 구체적으로 작성합니다.")
    exclude_selectors: Optional[list[str]] = Field(default=None, description="이 계층에서 제외해야 할 요소들의 CSS 셀렉터 목록. Navigator가 DOM 분석 중 발견한 광고, 스폰서, 더미 요소 등의 패턴을 Coder에게 전달합니다. (예: ['.ad_product', '[class*=\"sponsor\"]'])")

    @field_validator("selectors", "extraction_notes", mode="before")
    @classmethod
    def parse_dict_fields(cls, v):
        """dict 필드가 JSON 문자열로 전달될 때 자동 파싱"""
        if isinstance(v, str):
            try: return json.loads(v)
            except Exception: pass
        return v

    @field_validator("navigate_to_next", "pagination_method", "pagination_details", mode="before")
    @classmethod
    def parse_none_string(cls, v):
        if v in ("None", "null", "없음", "N/A", ""): return None
        return v

class NavigatorBlueprint(BaseModel):
    """Navigator가 Coder에게 전달하는 동적 N계층 크롤링 설계 도면"""
    entry_urls: list[str] = Field(description="크롤링을 시작할 URL 목록 (구조가 같다면 복수 가능)")
    total_layers: int = Field(description="탐색에 필요한 총 계층 수")
    layers: list[PageLayer] = Field(description="탐색 순서대로 정렬된 PageLayer 목록")
    rendering_type: str = Field(description="Static SSR 또는 Dynamic CSR/JS")
    anti_bot_notes: str = Field(description="로그인, 캡차 등 안티봇 주의사항. 제약이 없으면 '없음'")
    navigator_notes: Optional[str] = Field(default=None, description="Navigator가 Supervisor/Coder에게 전달하는 자유 형식 메모. 분석 과정에서 발견한 주의사항, 권장 구현 방식, 사이트 특이점 등을 기록합니다.")

class NavigatorBlueprintCollection(BaseModel):
    """Navigator가 반환하는 Blueprint 모음"""
    total_jobs: int = Field(description="총 Blueprint 구조체 수")
    blueprints: list[NavigatorBlueprint] = Field(description="수집 작업별 Blueprint 목록")

# ==========================================
# 2. 에이전트 Context 및 State
# ==========================================
@dataclass
class NavigatorContext:
    shared_browser: Optional[Any] = None  # Browser 인스턴스 주입용
    response_mode: str = field(default="chat") # "chat" or "blueprint"

@dataclass
class SeniorCoderContext:
    pass
