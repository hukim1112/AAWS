# 💡 Agentic AI 개발의 4가지 핵심 교훈 (Lessons Summary)

AAWS 데이터 수집 멀티에이전트 프로젝트를 설계, 개발, 관찰, 평가하며 도출한 **Agentic AI 구축 4가지 핵심 원칙**입니다.

---

## 1. 🪵 로깅 체계 확립 (Observability & Traceability)
> *"로그가 없는 에이전트 개발은 캄캄한 방에서 안대를 쓰고 코딩하는 것과 같다."*

### 🤔 왜 로깅이 중요한가? (Why Logging Matters)
1. **시나리오 수행 과정 검토**: 내 에이전트가 시나리오 목표를 실제로 어떻게 이해하고 어떤 절차로 작업을 수행하는지 투명하게 검토할 수 있습니다.
2. **도구 세부 동작 및 오작동 진단**: 어떤 도구를 어떤 순서로 쓰는지, 각 도구가 예상대로 동작하는지, 어디서 시행착오(루프, 셀렉터 미발견) 및 컨텍스트 오류/단절이 발생하는지 포착할 수 있습니다.
3. **AI 개발 어시스턴트와의 디버깅 컨텍스트**: 인간 개발자와 코딩 어시스턴트(AI)가 에이전트를 함께 개발하고 디버깅할 수 있는 가장 확실하고 객관적인 컨텍스트를 제공합니다.
4. **실행 간 정량적 성능 비교**: 이전 실행과 현재 실행의 소요시간, 도구 호출 분포, 결과 변화를 데이터 기반으로 비교 분석할 수 있습니다.

### 🛠️ 어떻게 로깅을 구축했는가? (How We Implemented It - Examples)

#### ① 실시간 마크다운 + browser-use 캡처 (`sup_log.md`)
에이전트의 도구 호출 입출력과 `browser-use`의 Step/Eval/Memory/Action 흐름을 통합 캡처합니다.
```markdown
### 🛠️ [Navigator] Tool: `browse_web`
> 🌐 [browser-use] 📍 Step 1:
> 🌐 [browser-use]   👍 Eval: Page loaded successfully but popup appeared...
> 🌐 [browser-use]   🧠 Memory: On danawa.com homepage with a popup...
> 🌐 [browser-use]   🎯 Next goal: Close the popup overlay...
> 🌐 [browser-use]   ▶️ click: index: 1494
```

#### ② 프로그래매틱 분석용 구조화 로그 (`sup_structured_log.json`)
에이전트 계층 태깅([Supervisor]/[Navigator]/[Coder]), 도구별 소요시간, 이벤트 타임라인을 파싱 가능한 JSON으로 보관합니다.
```json
{
  "scenario_id": "danawa_01_filter_search",
  "run_id": "20260728_075028",
  "total_duration_sec": 348.47,
  "summary": {
    "agent_tool_counts": { "Supervisor": 2, "Navigator": 4, "Coder": 2 },
    "tool_avg_duration_sec": { "browse_web": 42.15, "run_python_script": 12.3 }
  }
}
```

#### ③ 실행별 독립 디렉토리 격리 (`runs/{run_id}/`)
매 실행의 로그와 산출물이 덮어씌워지지 않고 독립 폴더에 자동 보관되어 `log_comparator` 분석을 지원합니다.
```text
artifacts/results/danawa_01_filter_search/runs/20260728_075028/
├── sup_log.md               (실시간 마크다운 + browser-use 캡처)
├── sup_result.json          (최종 수집 결과 JSON)
└── sup_structured_log.json  (구조화 분석 JSON)
```

#### ④ 서브에이전트 재귀 제한 전파 보증 (`recursion_limit` propagation)
최상위 러너에서 `recursion_limit=100`을 설정하더라도 Handoff 도구가 서브에이전트(`GLOBAL_CODER_AGENT` 등)를 서브 그래프로 실행할 때 `inner_config`에 `recursion_limit`을 명시적으로 넘겨주지 않으면 기본값(50)으로 복귀하여 `GraphRecursionError`가 발생하는 버그를 포착 및 보안했습니다.

---

## 2. 🛠️ 도구 설계: 에이전트의 핵심 지능 (Tool Design & Capability)
> *"프롬프트가 '전략'을 결정한다면, 도구는 에이전트의 '물리적 능력'과 '지능'을 결정한다."*

### 🤔 왜 도구(Tool)가 중요한가? (Why Tools Matter)
1. **에이전트 지능의 물리적 한계 확장**: 프롬프트를 아무리 정교하게 써도 도구가 비효율적이면 행동의 한계에 부딪힙니다. 최적화된 도구는 최소한의 토큰과 시간으로 문제를 해결하는 핵심 지능이 됩니다.
2. **환각(Hallucination) 및 비용 폭증 차단**: raw 텍스트/HTML 전체를 LLM에 전달하면 주의력 분산과 토큰 비용이 폭증합니다. 에이전트가 명확하게 판단할 수 있도록 가공된 뷰(View)를 제공해야 합니다.
3. **사실 검증(Fact-Checking) 내재화**: LLM의 비결정론적 추론 결과를 실제 환경에서 테스트해 보는 검증 루프 도구를 제공함으로써 실패율을 획기적으로 낮춥니다.
4. **역할(Role)의 명확한 정의**: 어떤 도구 셋을 제공하느냐에 따라 에이전트의 역할(분석가, 개발자, 검증가)이 비로소 결정됩니다.

### 🛠️ 어떻게 도구를 설계하고 구축했는가? (How We Implemented It - Examples)

#### ① DOM 스켈레톤 압축 도구 (`extract_dom_skeleton`)
300KB 원문 HTML 전체 대신, 태그/클래스/ID/자식 수/샘플 텍스트만 추출한 경량 트리(~5KB)를 제공합니다. 반복 노드의 구조적 차이(광고 노드 vs 실제 상품 노드)를 한눈에 파악하게 합니다.
```python
# app/tools/navigator.py
@tool(parse_docstring=True)
async def extract_dom_skeleton(url: str, root_selector: str = "body", max_depth: int = 6) -> str:
    """HTML 원문 전체 대신, 태그/클래스/ID/자식 수/샘플 텍스트만 추출한 경량 트리(~5KB)를 제공하여
    광고/실제 상품 노드의 구조적 차이를 효율적으로 식별하도록 돕습니다."""
```

#### ② 셀렉터 샘플 검증 도구 (`verify_selectors_with_samples`)
Navigator가 추출한 CSS 셀렉터가 실제로 대상 페이지에서 데이터를 정상 추출하는지 Playwright로 5개의 샘플을 뽑아 미리 확인합니다.
```python
# app/tools/navigator.py
@tool(parse_docstring=True)
async def verify_selectors_with_samples(url: str, selectors_json: str) -> str:
    """찾아낸 CSS 셀렉터가 실제로 데이터를 가져오는지 브라우저로 5개 샘플을 추출해 직관적으로 검증합니다.
    출력: [✅ OK] name: 샘플 ['ASUS TUF...', 'MSI GF...'] / [⚠️ FAILED] price: 매칭 0건"""
```

#### ③ 미세 브라우저 제어 및 실행 요약 도구 (`browse_web`) & Context Isolation (맥락 격리)
상위 에이전트(Supervisor/Navigator)가 하위 브라우저 에이전트의 구체적인 작업 진행 과정("어떤 스텝과 시행착오를 거쳤는가")을 파악하는 것은 정교한 데이터 수집 전략 수립에 필수적입니다. 그러나 브라우저 조작 과정의 무거운 raw DOM 트리와 수십 단계의 이벤트를 상위 에이전트 컨텍스트에 통째로 전파하면 **토큰 포화(Token Overflow) 및 API 비용 폭증**이 발생합니다.

이를 해결하기 위해 `browse_web` 도구는 팝업 닫기, 검색, 필터 UI 클릭 등 복잡한 브라우저 조작을 내부에서 완수한 뒤, 상위 에이전트가 완벽한 판단 맥락을 가질 수 있도록 **핵심 작업 수행 요약, 방문 URL, 시행착오/장애물, 반복 패턴 피드백을 정교하게 요약(Summary)하여 반환**하도록 구현했습니다. 이것이 상위/하위 에이전트 간 맥락 단절을 막고 토큰 폭증을 차단하는 **Context Isolation (맥락 격리)**의 대표적 설계 사례입니다.

```text
[browse_web 실행 요약] 스텝: 8/15, 성공: ✅, 최종 URL: https://search.danawa.com/dsearch.php?...
--- [에이전트 상세 분석 리포트] ---
## 작업 요약 리포트
1. 작업 수행 요약: danawa.com 이동 ➔ '게이밍 노트북' 검색 ➔ 'RAM 32GB' 필터 적용 ➔ '인기상품순' 정렬
2. 방문한 주요 URL 목록: https://search.danawa.com/dsearch.php?k1=게이밍노트북&option=RAM_32GB&sort=popular
3. 시행착오 및 장애물: 모달 팝업 자동 감지 및 닫기 조치 이행
4. 핵심 성공 요인: RAM 32GB 필터 클릭 후 쿼리 파라미터가 반영된 최종 결과 URL 확보
```

#### ④ 범용 열람 도구의 컨텍스트 안전 가드레일 (`read_file`)
중복 도구(`read_code_file`, `write_text_file`)를 `read_file` 단일 도구로 정리하고, 대용량 수집 결과(JSON/로그) 열람 시 LLM 토큰이 폭발(Overflow)하지 않도록 기본 100줄 캡핑(`max_display_lines=100`)과 전체 라인 수 및 추천 다음/끝 구간(`start_line`, `end_line`) 메타안내 정보를 자동 반환하게 구축했습니다.

---

## 3. 🎯 프롬프트 엔지니어링: 패치(Patch)가 아닌 원칙(Principle)이다
> *"프롬프트 다이어트는 토큰 절감이자 에이전트 지능의 향상이다."*

### 1. 📦 Prompt-as-Code (코드로서의 프롬프트 모듈화)
* **왜 중요한가 (Why)**: 파이썬 비즈니스 로직 코드 안에 프롬프트를 하드코딩하거나 여러 파일에 흩뿌려두면, 프롬프트 수정이 전체 시스템 오류를 유발하고 독립적인 버전 관리와 튜닝이 불가능해집니다.
* **어떻게 구현했는가 (How)**: `app/prompts/` 패키지로 독립 모듈화하고, 파이썬 코드에서는 이를 임포트(`from app.prompts import CODER_SYSTEM_PROMPT`)하여 사용하여 비즈니스 로직 수정 없이 프롬프트만 단독으로 개정할 수 있게 했습니다.

### 2. 🛡️ 패치(Patch)가 아닌 원칙(Principle) 중심 프롬프팅 (Generalization over Overfitting)
* **왜 중요한가 (Why)**: 
  - 에러가 발생할 때마다 특정 예외 사례용 문구(*"25개 중 13개만 수집되어도 봐줘라"*)를 덧붙이면 프롬프트가 오염되고 과적합(Overfitting)되어 에이전트가 스스로 사고하지 못합니다.
  - 프롬프트에 특정 도메인 용어(*"상품", "스펙"* 등)를 직접 명시하면 뉴스, 주식, 부동산 등 타 도메인 데이터 수집 시 에이전트의 지능이 왜곡되는 과적합이 일어납니다.
* **어떻게 구현했는가 (How)**:
  - 특정 도메인 단어 대신 **"핵심 수집 항목", "수집 대상 개체"** 등 범용적 원칙 용어로 일반화(Generalization)했습니다.
  - Coder가 난관에 부딪혔을 때 무의미한 임시 테스트 파이썬 스크립트를 남발하지 않도록 **"원샷 리포팅 3대 요령(진행 상황, 실패 지점, 요청 사항)"**을 명확하면서도 다이어트된 1줄 원칙으로 주입했습니다.
  ```text
  ❌ 과적합 패치: "25개 기대 시 13개만 수집되어도 봐주고 즉시 중단하라" (진짜 버그 시에도 포기하게 만듦)
  ❌ 도메인 과적합: "상세 페이지의 주요 스펙 셀렉터를 사전 검증하라" (상품 이외 도메인 적용 불임)
  ✅ 범용 원칙: "상세 페이지의 핵심 수집 항목 셀렉터를 사전 검증하라" (모든 데이터 도메인 수집 호환)
  ```

### 3. ⚖️ What & Why에 집중하고 How는 도구 명세로 분리 (정보의 3계층 분리)
* **왜 중요한가 (Why)**: 시스템 프롬프트에 도구 파라미터명과 세부 매뉴얼까지 전부 집어넣으면 LLM의 주의력(Attention)이 매뉴얼 독해에 쏠려 정작 중요한 전략적 판단력을 잃습니다.
* **어떻게 구현했는가 (How)**: 시스템 프롬프트에는 정체성과 행동 철학(**What & Why**)만 남기고, 구체적인 함수 규격(**How**)은 도구 Docstring으로 넘기는 3계층 구조로 프롬프트를 다이어트시켰습니다.
  - **Layer 1 (시스템 프롬프트)**: 에이전트 정체성 & 의사결정 원칙 ("What & Why")
  - **Layer 2 (도구 Docstring)**: 구체적 실행법 및 인자 규격 (`mode="blueprint"`, `wait_seconds=5`) ("How")
  - **Layer 3 (Task Context)**: 런타임에 주입되는 목표 URL 및 세부 수집 제약 사항

### 4. 🗺️ 프롬프트는 에이전트의 맥락 지도(Context Map)다
* **왜 중요한가 (Why)**: 자율 에이전트가 동작하는 복잡한 시스템에서 프롬프트는 단순한 지시문이 아니라, 에이전트가 자신을 둘러싼 주변 환경과 자원을 조망하고 길을 찾게 해주는 종합 **'맥락 지도(Context Map)'** 역할을 해야 합니다.
* **어떻게 구현했는가 (How)**: 에이전트 프롬프트 안에 다음 5개 청사진 요소들의 접근 경로와 상호작용 규약을 명확히 매핑하여 설계했습니다.
  - **역할 및 페르소나 (Role & Persona)**: 총괄 매니저(Supervisor), 탐색가(Navigator), 개발자(Coder) 정체성 부여
  - **행동 가이드라인 (Behavioral Guidelines)**: 원인 분류 수칙, 조기 중단(Fast Fail) 및 예외 처리 기준
  - **도구 지침 (Tool Instructions)**: 상황별 우선 선택 도구 지침
  - **외부 맥락 접근 경로 (Skills, MCP, 주요 Context 파일, Memory)**: 참조해야 할 시나리오 문서, 가상환경 규칙(`python_execution.md`), 결과물 저장 경로 매핑
  - **상호작용 규약 (User, UI, 다른 에이전트와의 Interaction)**: 에이전트 간 Handoff 메시지 포맷, 이벤트 스트리밍 방식, 최종 보고서 양식 규정

---

## 4. 📊 평가 하네스 구축 (Evaluation Harness & EDD)
> *"결과 파일 존재 여부만으로 에이전트의 성공을 평가해서는 안 된다. TDD를 넘어 EDD(Evaluation-Driven Development)로 진화하라."*

### 🤔 왜 평가 하네스가 중요한가? (Why Evaluation Harness Matters)
1. **단순 실행 성공과 진짜 목표 달성의 분리**: 에이전트가 에러 없이 결과 파일(`sup_result.json`)을 생성했더라도, 그 내용이 요구 스키마를 준수했는지, 또는 편법(URL 파라미터 조작)을 썼는지 인간이 일일이 눈으로 검증할 수 없습니다.
2. **비결정론적(Non-Deterministic) 결과의 품질 통제**: LLM은 매 실행마다 응답과 코드가 달라집니다. "잘 되는 것 같다"는 직관이 아니라, 프롬프트/도구 개정이 성능에 미친 영향을 객관적으로 추적하는 테스트 하네스가 필수적입니다.
3. **편법(Shortcut) 감정 및 튜닝의 선순환**: 에이전트는 본능적으로 쉬운 길만 찾으려 합니다. 정석 수집 전략(UI 필터 클릭)을 이행하지 않았을 때 정당하게 FAIL 처리를 내리고 피드백을 남겨야 에이전트 튜닝의 명확한 나침반이 됩니다.

### 🛠️ 어떻게 평가 하네스를 구축하고 적용했는가? (How We Implemented It - Examples)

#### ① 이중 평가 체계 (Schema Score + Strategy Score)
[app/evaluator.py](file:///c:/Users/hyoun/Desktop/github/AAWS/app/evaluator.py)에서 결정론적 검증과 비결정론적 LLM 평가를 결합한 이중 채점 체계를 적용했습니다.
* **스키마 준수 점수 (`Schema Score`)**: `jsonschema` 검증기를 통해 수집된 JSON 데이터의 필드 존재 여부 및 데이터 타입 계약(가격 int, 스펙 list)을 100점 만점으로 자동 채점.
* **전략 준수 점수 (`Strategy Score`)**: `LLM-as-a-Judge` (`EvaluationFeedback`) 구조화 출력을 통해 에이전트가 작성한 코드와 실행 리포트를 분석하여 지정된 수집 전략(AJAX 대기, UI 클릭 등) 이행률을 정성 채점.

```python
# app/evaluator.py
eval_model = get_llm("gemini-2.5-flash", temperature=0.1)
structured_evaluator = eval_model.with_structured_output(EvaluationFeedback)

# 스키마 검증 실패 시 무조건 최종 FAIL 보정
if not schema_pass:
    result.is_pass = False
    result.schema_score = 0
```

#### ② 시나리오-평가 기준의 단일 진실 공급원 (Single Source of Truth)
시나리오 마크다운 문서 내 Frontmatter에 **목표 URL, 요구 스키마, 평가 수칙**을 하나의 원자(Atom) 단위로 동기화하여 지시와 채점 기준이 서로 어긋나지 않도록 설계했습니다.

#### ③ 실행 후 자동 채점 및 피드백 리포팅
테스트 러너(`run_supervisor_scenarios.py`) 완주 직후 Evaluator가 자동으로 실행되어 통과 여부(`🟢 PASS` / `🔴 FAIL`), 스키마/전략 점수, 개선 피드백을 터미널과 `sup_log.md`에 자동으로 기록합니다.
```text
📊 [평가 리포트]
통과 여부: 🔴 FAIL (스키마 점수: 100/100, 전략 점수: 55/100)
피드백: 필터 UI 클릭 이벤트를 실행하는 대신 URL 파라미터를 조작하는 우회 방식을 사용함.
```
