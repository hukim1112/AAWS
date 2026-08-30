# 🎯 Mission 01: Chatbot 에이전트에 커스텀 기억 도구(읽기/갱신) 연결 및 UI 테스트

본 미션은 `1_Create_agent.ipynb`에서 학습한 내용을 바탕으로, 교육생 여러분이 직접 커스텀 도구를 작성하고 실제 프로덕션 코드베이스인 `app/agents/chatbot.py`에 연결하여 **FastAPI 서버와 Chainlit UI 환경에서 양방향 장기 기억(읽기 & 갱신)을 실시간으로 테스트**하는 실습 과제입니다.

---

## 📂 실습 대상 파일
* **커스텀 도구 작성 파일 (빈 파일 제공)**: `app/tools/custom_tools.py`  
  👉 **이 빈 파일을 열고 직접 도구 코드를 작성하세요!**
* **에이전트 조립 파일**: `app/agents/chatbot.py`
* **사용자 기억 데이터 파일**: `app/database/USER.md`

---

## 📋 미션 목표
1. **[미션 1-1] 기억 읽기 도구 (`read_user_memory`) 구현**:
   - `app/tools/custom_tools.py`에 `USER.md`를 읽는 도구를 직접 작성하고 `chatbot.py`에 탑재하여 맞춤형 첫 인사를 수행합니다.
2. **[미션 1-2] 기억 전체 갱신 도구 (`update_user_memory`) 구현**:
   - 대화 중 사용자의 취미, 연차, 전문 분야가 변경되거나 추가되면, 기존 프로필과 통합(Consolidation)하여 `USER.md` 파일을 최신 마크다운으로 덮어써서 갱신(Update)하는 도구를 구현하고 에이전트에 연결합니다.
3. **[서버 & UI 통합 검증]**:
   - FastAPI 서버(`server.py`)와 Chainlit UI(`chainlit_ui.py`)를 가동하여 웹 화면에서 기억의 **읽기 ➔ 대화 ➔ 프로필 갱신 ➔ 파일 확인** 전체 사이클이 정상 작동하는지 확인합니다.

---

## 🛠️ 단계별 수행 가이드

### 1단계: `app/tools/custom_tools.py`에 도구 2종 직접 작성하기

빈 파일로 준비된 `app/tools/custom_tools.py`를 열고, 아래의 `read_user_memory`와 `update_user_memory` 도구를 작성하세요:

```python
# app/tools/custom_tools.py

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
```

---

### 2단계: `app/agents/chatbot.py`에 도구 임포트 및 시스템 프롬프트 연결

`app/agents/chatbot.py` 파일을 열고, 방금 작성한 `custom_tools` 모듈로부터 도구들을 임포트하여 에이전트 도구 목록에 추가합니다:

```python
# app/agents/chatbot.py

# 1. custom_tools에서 도구 임포트
from app.tools.custom_tools import read_user_memory, update_user_memory
from app.tools import tools_chatbot
# ...

async def create_agent_executor():
    # ...
    # 2. tools_chatbot 목록에 커스텀 기억 도구들 추가
    active_tools = tools_chatbot + [read_user_memory, update_user_memory]
    
    # 3. 에이전트 시스템 프롬프트 정의 (기억 조회 및 갱신 지침 명시)
    SYSTEM_PROMPT = """
    당신은 사용자 맞춤형 지능형 비서입니다.
    
    [행동 규칙]
    1. 사용자와의 대화가 시작되면 가장 먼저 `read_user_memory`를 호출하여 사용자의 프로필을 확인하고 맞춤 인사를 건네세요.
    2. 사용자가 대화 중에 새로운 취미, 경력 변동, 전문 분야 변경 등 자신의 프로필 정보를 알려주면,
       기존 프로필 내용에 해당 변경 사항을 자연스럽게 반영/통합하여 `update_user_memory` 도구를 호출해 USER.md를 최신 상태로 갱신하세요.
    """
    
    chatbot_agent = create_agent(
        model=llm,
        tools=active_tools,
        system_prompt=SYSTEM_PROMPT,
        middleware=middleware,
        checkpointer=checkpointer,
        context_schema=AgentContext
    )
    return chatbot_agent
```

---

### 3단계: 서버 및 웹 UI 실행

터미널 2개를 열어 각각 백엔드와 프론트엔드를 구동합니다:

#### 🖥️ 터미널 1 (FastAPI 백엔드 서버 가동):
```bash
python app/server.py --port 8000
```
*(성공 메시지: `Uvicorn running on http://0.0.0.0:8000`)*

#### 🌐 터미널 2 (Chainlit 웹 채팅 UI 가동):
```bash
chainlit run app/chainlit_ui.py --port 8080
```
*(성공 메시지: `Your app is available at http://localhost:8080`)*

---

### 4단계: 브라우저 접속 및 양방향 기억 테스트 시나리오

1. 웹 브라우저에서 `http://localhost:8080`에 접속합니다.
2. 로그인 창에서 아이디: `user`, 비밀번호: `1234`로 로그인합니다.
3. 좌측 상단 프로필에서 **`chatbot`** 에이전트를 선택합니다.

#### 🧪 테스트 시나리오 A: [기존 프로필 읽기 확인]
- **사용자 입력**: `"안녕! 오늘 나 뭐 도와줄 수 있어?"`
- **기대 동작**: 에이전트가 `read_user_memory`를 호출하여 사용자의 직업과 취미(골프, 헬스, 자전거, 수영)를 언급하며 맞춤 인사를 건넴.

#### 🧪 테스트 시나리오 B: [프로필 정보 갱신(Update) 확인]
- **사용자 입력**: `"나 최근에 테니스도 새로 배우기 시작했어. 그리고 연차가 쌓여서 이제 6년차가 되었어. 내 프로필에 반영해줘!"`
- **기대 동작**: 
  1. 에이전트가 `read_user_memory`로 기존 내용을 확인(또는 이전 맥락 참조)
  2. 직업(`6년차`), 취미(`골프, 헬스, 자전거, 수영, 테니스`)로 수정된 전체 마크다운 문서를 생성하여 `update_user_memory(content=...)` 호출
  3. 완료 응답 반환

#### 🧪 테스트 시나리오 C: [파일 갱신 검증 & 재조회]
- `app/database/USER.md` 파일을 직접 열어 6년차 및 테니스가 깔끔하게 반영되었는지 확인합니다.
- **사용자 입력**: `"내 취미 목록과 연차가 어떻게 등록되어 있어?"`
- **기대 동작**: 갱신된 프로필을 바탕으로 `"김철수 님은 6년차 AI 소프트웨어 엔지니어이시며, 취미로는 골프, 헬스, 자전거, 수영, 테니스를 즐기십니다."`라고 완벽하게 답변함!

---

## ✅ 성공 검증 체크리스트
- [ ] `app/tools/custom_tools.py`에 `read_user_memory`와 `update_user_memory`를 직접 작성했는가?
- [ ] `app/agents/chatbot.py`에서 `custom_tools`로부터 도구를 임포트하여 에이전트에 등록했는가?
- [ ] `update_user_memory` 호출 후 실제 `app/database/USER.md` 파일 내용이 최신 상태로 덮어써져 갱신되었는가?
- [ ] Chainlit UI에서 읽기/갱신 도구 실행 스텝이 시각적으로 표시되는가?

축하합니다! 이제 여러분은 단순 메모리 누적이 아닌, **정보를 스스로 통합하고 갱신(Consolidation & Update)**하는 진정한 프로덕션 레벨의 에이전트 메모리 시스템을 구축했습니다. 🚀
