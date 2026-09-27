"""
custom_tools.py — 사용자 커스텀 도구 모음 (Mission 01 완성형)

USER.md 파일 기반의 장기 기억 읽기(read_user_memory) 및 갱신(update_user_memory) 도구를 제공합니다.
"""

import os
from langchain_core.tools import tool

USER_MD_PATH = os.path.abspath("app/database/USER.md")


@tool(parse_docstring=True)
def read_user_memory() -> str:
    """사용자의 프로필, 직업, 전문 분야, 선호 스타일, 취미 등이 기록된 USER.md 파일을 읽어옵니다.
    사용자와의 첫 인사나 개인화된 정보 조회가 필요할 때 호출하세요.
    """
    if not os.path.exists(USER_MD_PATH):
        return "[알림] 사용자 프로필(USER.md) 파일이 존재하지 않습니다."

    with open(USER_MD_PATH, "r", encoding="utf-8") as f:
        return f.read()


@tool(parse_docstring=True)
def update_user_memory(content: str) -> str:
    """사용자의 최신 프로필 정보(이름, 직업, 전문 분야, 취미, 선호 스타일 등)로 USER.md 파일을 전체 갱신(업데이트)합니다.

    사용자와의 대화 중 기존 정보가 변경되거나 새로운 정보가 추가되었을 때,
    기존 프로필 내용과 새로운 사실을 깔끔하게 통합하여 마크다운 텍스트로 전달하세요.

    Args:
        content: 최신 상태로 통합 정리된 전체 사용자 프로필 마크다운 텍스트
    """
    os.makedirs(os.path.dirname(USER_MD_PATH), exist_ok=True)

    with open(USER_MD_PATH, "w", encoding="utf-8") as f:
        f.write(content.strip())

    return "✅ 사용자 프로필(USER.md)이 최신 정보로 성공적으로 업데이트되었습니다."


__all__ = ["read_user_memory", "update_user_memory"]
