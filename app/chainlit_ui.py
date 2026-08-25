"""
chainlit_ui.py — Chainlit 기반 Agent Chat UI (FastAPI 클라이언트 모드)

에이전트 실행은 FastAPI 서버(:8000)에 위임하고,
Chainlit은 SSE 스트림을 수신하여 UI만 렌더링하는 프론트엔드 역할을 합니다.
HITL(Human-in-the-Loop): interrupt 이벤트 수신 시 cl.AskActionMessage로 승인/거부 UI를 표시합니다.

사전 조건: FastAPI 서버(server.py)가 :8000 에서 실행 중이어야 합니다.
"""
import os
import sys
import uuid
import re
import json
import chainlit as cl
from chainlit.types import ThreadDict
from typing import Dict, Any, Optional, List

# Setup project root
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

from app.client import AsyncAgentClient
from app.utils.database import ChainlitSQLiteDataLayer, CHAINLIT_DB_PATH
from app.utils.message_utils import sanitize_text

# ── FastAPI 백엔드 클라이언트 ─────────────────────────────────
FASTAPI_BASE_URL = os.getenv("FASTAPI_BASE_URL", "http://localhost:8000")
api_client = AsyncAgentClient(base_url=FASTAPI_BASE_URL)


# ── 1. Chainlit Data Layer (SQLite 기반 사이드바 히스토리) ─────
@cl.data_layer
def get_data_layer():
    return ChainlitSQLiteDataLayer(db_path=CHAINLIT_DB_PATH)


# ── 2. 사용자 인증 콜백 ──────────────────────────────────────
@cl.password_auth_callback
def auth_callback(username: str, password: str) -> Optional[cl.User]:
    if (username == "user" and password == "1234") or (username == "admin" and password == "admin"):
        return cl.User(identifier=username, metadata={"role": username})
    return None


# ── 3. 에이전트 선택 프로필 (FastAPI GET /agents 동적 조회) ───
@cl.set_chat_profiles
async def chat_profile(current_user: Optional[cl.User] = None):
    """FastAPI 서버의 /agents 엔드포인트에서 에이전트 목록을 조회하여 프로필을 동적으로 구성합니다."""
    try:
        agents = await api_client.get_agents()
    except Exception as e:
        print(f"⚠️ Failed to fetch agents from FastAPI: {e}")
        agents = []

    if not agents:
        return [
            cl.ChatProfile(
                name="chatbot",
                markdown_description="🤖 **Chatbot**: FastAPI 서버 연결 실패 (기본 폴백)",
                icon="https://api.dicebear.com/7.x/bottts/svg?seed=chatbot"
            )
        ]

    profiles = []
    for agent in agents:
        name = agent.get("name", "unknown")
        desc = agent.get("description", f"🤖 {name.capitalize()} Agent")
        icon = agent.get("icon", f"https://api.dicebear.com/7.x/bottts/svg?seed={name}")
        profiles.append(
            cl.ChatProfile(name=name, markdown_description=desc, icon=icon)
        )
    return profiles


# ── 4. 새 대화 시작 ──────────────────────────────────────────
@cl.on_chat_start
async def on_chat_start():
    """새 대화방(New Chat) 시작 시 선택된 프로필 이름과 always_allow 목록을 초기화합니다."""
    profile = cl.user_session.get("chat_profile") or "chatbot"
    cl.user_session.set("always_allow_tools", set())  # 세션별 "항상 승인" 목록

    # 서버 연결 상태 확인
    server_ok = await api_client.health_check()
    status_msg = "" if server_ok else "\n⚠️ *FastAPI 서버(:8000) 연결을 확인해 주세요.*"

    await cl.Message(
        content=f"👋 **안녕하세요! [{profile.upper()}] 와의 대화에 오신 것을 환영합니다.**\n과거 대화 목록은 왼쪽 사이드바에서 언제든지 확인하고 다시 열 수 있습니다.{status_msg}",
        author="Agent Assistant"
    ).send()


# ── 5. 기존 대화 복원 ────────────────────────────────────────
@cl.on_chat_resume
async def on_chat_resume(thread: ThreadDict):
    """사이드바에서 기존 대화방 클릭 시 프로필 정보를 복원합니다."""
    tags = thread.get("tags") or []
    profile = thread.get("metadata", {}).get("chat_profile") or (tags[0] if tags else "chatbot")
    cl.user_session.set("chat_profile", profile)
    cl.user_session.set("always_allow_tools", set())  # 복원 시 always_allow 초기화

    await cl.Message(
        content=f"📂 **이전 대화방('{thread.get('name', 'Chat')}')이 성공적으로 복원되었습니다.**\n(에이전트: `{profile}`)\n이어서 지시사항을 입력해 주세요.",
        author="Agent Assistant"
    ).send()


# ── 6. SSE 스트림 이벤트 처리 헬퍼 ───────────────────────────
async def _process_sse_stream(
    stream_generator,
    final_message: cl.Message,
    active_steps: Dict[str, cl.Step],
) -> Optional[dict]:
    """
    SSE 이벤트를 순회하며 cl.Step / stream_token으로 렌더링합니다.
    interrupt 이벤트가 발생하면 해당 이벤트를 반환하고, 없으면 None을 반환합니다.
    """
    async for event in stream_generator:
        event_type = event.get("type")

        # 1. 도구 호출 시작 → cl.Step 트리 렌더링
        if event_type == "tool_start":
            tool_name = event.get("name", "Tool")
            tool_input = event.get("input", "")
            run_id = event.get("run_id", str(uuid.uuid4()))

            step = cl.Step(name=f"🛠️ {tool_name}", type="tool")
            step.input = sanitize_text(str(tool_input))
            await step.send()
            active_steps[run_id] = step

        # 2. 도구 호출 완료
        elif event_type == "tool_end":
            run_id = event.get("run_id", "")
            if run_id in active_steps:
                step = active_steps[run_id]
                tool_output = event.get("output", "")
                step.output = sanitize_text(str(tool_output))
                await step.update()
                del active_steps[run_id]

        # 3. 모델 토큰 스트리밍
        elif event_type == "token":
            content = event.get("content", "")
            if content:
                await final_message.stream_token(content)

        # 4. HITL Interrupt — 즉시 반환
        elif event_type == "interrupt":
            return event

        # 5. 에러
        elif event_type == "error":
            error_msg = event.get("error") or event.get("content", "알 수 없는 에러")
            await cl.Message(content=f"❌ **에러:** {error_msg}").send()
            return None

    return None  # 정상 종료 (interrupt 없음)


# ── 7. HITL 결정 수집 ────────────────────────────────────────
async def _collect_hitl_decisions(interrupt_event: dict) -> List[dict]:
    """
    interrupt 이벤트에서 action_requests를 파싱하고,
    각 도구에 대해 사용자에게 승인/항상승인/거부를 물어 decisions를 반환합니다.
    always_allow 목록에 있는 도구는 자동 승인합니다.
    """
    always_allow: set = cl.user_session.get("always_allow_tools") or set()
    decisions = []

    interrupts = interrupt_event.get("interrupts", [])
    for intr in interrupts:
        value = intr.get("value", {})
        action_requests = value.get("action_requests", [])
        review_configs = value.get("review_configs", [])

        for i, req in enumerate(action_requests):
            tool_name = req.get("name", "unknown")
            tool_args = req.get("args", {})
            description = req.get("description", "")
            allowed = review_configs[i].get("allowed_decisions", ["approve", "reject"]) if i < len(review_configs) else ["approve", "reject"]

            # "항상 승인" 목록에 있으면 자동 approve
            if tool_name in always_allow:
                decisions.append({"type": "approve"})
                await cl.Message(
                    content=f"🔓 **[{tool_name}]** 항상 승인 설정에 의해 자동 승인되었습니다.",
                    author="System"
                ).send()
                continue

            # 버튼 구성 (allowed_decisions 기반)
            actions = []
            if "approve" in allowed:
                actions.append(cl.Action(name="approve", label="✅ 승인", payload={"type": "approve"}))
                actions.append(cl.Action(name="always_allow", label="✅ 항상 승인", payload={"type": "always_allow"}))
            if "reject" in allowed:
                actions.append(cl.Action(name="reject", label="❌ 거부", payload={"type": "reject"}))

            # 인자 표시용 텍스트
            args_display = json.dumps(tool_args, indent=2, ensure_ascii=False) if tool_args else "(없음)"

            # 사용자에게 결정 요청
            res = await cl.AskActionMessage(
                content=f"🔒 **[{tool_name}]** 도구 실행 승인이 필요합니다.\n\n**인자:**\n```json\n{args_display}\n```",
                actions=actions,
                timeout=300,
            ).send()

            if res and res.get("payload", {}).get("type") == "always_allow":
                always_allow.add(tool_name)
                cl.user_session.set("always_allow_tools", always_allow)
                decisions.append({"type": "approve"})
                await cl.Message(
                    content=f"🔓 **[{tool_name}]** 이후 이 도구는 이 세션에서 자동 승인됩니다.",
                    author="System"
                ).send()
            elif res and res.get("payload", {}).get("type") == "approve":
                decisions.append({"type": "approve"})
            else:
                # 거부 또는 타임아웃
                decisions.append({"type": "reject", "message": "사용자가 실행을 거부했습니다."})

    return decisions


# ── 8. 메시지 처리 (FastAPI SSE 스트리밍 + HITL 연쇄 루프) ────
@cl.on_message
async def on_message(message: cl.Message):
    """
    사용자 메시지를 FastAPI 백엔드로 전달하고,
    SSE 스트림 이벤트를 수신하여 cl.Step / stream_token으로 렌더링합니다.
    HITL interrupt가 발생하면 사용자에게 결정을 요청하고 resume합니다.
    """
    profile = cl.user_session.get("chat_profile") or "chatbot"
    thread_id = cl.context.session.thread_id or str(uuid.uuid4())

    final_message = cl.Message(content="")
    active_steps: Dict[str, cl.Step] = {}

    try:
        # 1. 초기 스트림
        interrupt_event = await _process_sse_stream(
            api_client.stream(profile, message.content, thread_id),
            final_message,
            active_steps,
        )

        # 2. HITL interrupt 연쇄 루프
        while interrupt_event:
            decisions = await _collect_hitl_decisions(interrupt_event)

            # Resume 호출 → 다시 스트리밍 (연쇄 interrupt 가능)
            interrupt_event = await _process_sse_stream(
                api_client.resume(profile, thread_id, decisions),
                final_message,
                active_steps,
            )

        # 3. 이미지 태그 파싱 (<Render_Image>...</Render_Image>)
        raw_content = final_message.content or ""
        elements = []
        image_matches = re.findall(r"<Render_Image>(.*?)</Render_Image>", raw_content)
        for img_path in image_matches:
            img_path = img_path.strip()
            if os.path.exists(img_path):
                elements.append(cl.Image(name=os.path.basename(img_path), path=img_path, display="inline"))

        if elements:
            final_message.elements = elements

        await final_message.send()

    except Exception as e:
        await cl.Message(content=f"❌ **에러가 발생했습니다:** {str(e)}").send()
