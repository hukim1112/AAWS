"""
Supervisor Agent System Prompt (Trainee Mission 03 & 04)
===============================================================================
Supervisor 에이전트의 페르소나, 오케스트레이션 원칙, 답변 및 UI 렌더링 규칙을 정의합니다.
===============================================================================
"""

from datetime import date

today_date = date.today().strftime("%Y-%m-%d")

# =============================================================================
# Supervisor 시스템 프롬프트 정의 (Mission 03 & 04)
# =============================================================================
# TODO: missions/03_missions.md [2단계] 또는 missions/04_missions.md를 참고하여
#       원칙 중심의 SUPERVISOR_SYSTEM_PROMPT를 완성하세요:
#       1. 작업 규모에 맞게 처리하기 (간단한 일 직접 처리, 여러 단계 작업은 계획 수립)
#       2. 전문가 활용하기 (Scraper 등 전문 에이전트에게 invoke_sub_agent로 위임)
#       3. 실패해도 멈추지 않기 (Backtracking 자가 치유)
#       4. 결과 중심 답변 및 UI 렌더링 태그 규칙 (<Render_HTML>, <Render_Image>, <Render_File>)

SUPERVISOR_SYSTEM_PROMPT = f"""당신은 사용자의 요청을 총괄 오케스트레이션하는 유능한 Supervisor 에이전트입니다.
질문에 답하고, 정보를 검색하고, 코드를 작성하는 등 다양한 범용 작업을 수행하며,
복잡한 웹 데이터 수집은 전문 에이전트에게 위임합니다.

오늘의 날짜: {today_date}
"""

