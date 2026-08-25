# 🎯 Mission 02: Scraper 에이전트 평가(Evaluation) 파이프라인 가동 및 아티팩트 분석

본 미션은 구축된 Scraper 에이전트(`app/agents/scraper.py`)가 실제 웹사이트 시나리오를 바탕으로 **DOM 탐색 ➔ 스크립트 작성 ➔ 데이터 수집 ➔ 자가 검증**의 전 과정을 스스로 완수하는지 **벤치마크 평가 파이프라인(`evaluate`)을 직접 실행하고 생성된 아티팩트를 관찰·분석**하는 실습 과제입니다.

---

## 📂 실습 대상 및 핵심 경로
* **평가 시나리오 설정 파일**: `evaluate/evaluate_config.yaml`
* **평가 실행 파이프라인 스크립트**: `evaluate/run_scraper_scenarios.py`
* **평가 대상 마크다운 시나리오 보관함**: `artifacts/scenarios/`
* **실행 산출물(로그 및 수집 데이터) 저장소**: `artifacts/runs/`

---

## 📋 미션 목표
1. **[평가 시나리오 설정]**: `evaluate/evaluate_config.yaml`에서 평가를 수행할 대상 시나리오를 설정합니다.
2. **[평가 파이프라인 실행]**: 터미널에서 평가 스크립트를 가동하여 에이전트의 자율 스크래핑 및 채점 과정을 확인합니다.
3. **[아티팩트 5종 분석]**: `artifacts/runs/scraper_<timestamp>_<id>/` 폴더에 생성된 산출물(계획서, 코드, 데이터, 로그)을 직접 열람하고 에이전트의 문제 해결 과정을 추적합니다.
4. **[평가 피드백 검토]**: LLM-as-a-Judge 평가 엔진이 매긴 스키마 점수, 전략 점수 및 합격(PASS) 여부를 확인합니다.

---

## 🛠️ 단계별 수행 가이드

### 1단계: 평가 시나리오 설정 (`evaluate/evaluate_config.yaml`)

`evaluate/evaluate_config.yaml` 파일을 열고, 테스트할 시나리오가 활성화되어 있는지 확인합니다.  
처음에는 가장 기본이 되는 **`quotes_01_pagination.md`** 시나리오를 실행해 봅니다:

```yaml
# evaluate/evaluate_config.yaml

scenarios:
  # ── Level 1 (정적 다중 페이지 수집 테스트) ──
  - quotes_01_pagination.md
  
  # 추가 실습 시 아래 시나리오의 주석(#)을 해제하여 순차적으로 도전해 보세요:
  # - quotes_02_tag_filter.md
  # - ajax_01_playwright_wait.md
```

> 💡 `artifacts/scenarios/` 폴더를 열어보면 각 시나리오 파일에 대상 URL, 목표 데이터 스키마, 난이도가 상세히 정의되어 있습니다.

---

### 2단계: 평가 파이프라인 실행

터미널(WSL 환경)에서 다음 명령어를 실행하여 자동 평가를 시작합니다:

```bash
python -m evaluate.run_scraper_scenarios
```

#### 🖥️ 터미널 출력 관찰 포인트:
1. **시나리오 로드**: 대상 사이트(`http://quotes.toscrape.com`) 및 요구사항 확인
2. **에이전트 실행**:
   - `extract_dom_skeleton` / `get_page_section`을 통한 DOM 구조 탐색
   - `verify_selectors`를 통한 CSS 셀렉터 1초 검증
   - `file_writer`를 통한 `scraper.py` 스크립트 작성
   - `bash_command`를 통한 스크립트 실행 및 JSON 생성
3. **LLM-as-a-Judge 평가**:
   - 수집된 데이터의 스키마 일치도(`schema_score`), 수집 전략 점수(`strategy_score`), 최종 합격(`PASS/FAIL`) 및 개선 피드백 출력

---

### 3단계: `artifacts/runs/` 내부 산출물 5종 집중 관찰

평가가 완료되면 `artifacts/runs/` 아래에 타임스탬프가 포함된 고유 폴더(예: `artifacts/runs/scraper_20260826_012048_a337fd/`)가 생성됩니다.  
해당 폴더 내부의 파일들을 하나씩 열어보며 에이전트의 작업 결과를 분석하세요:

| 산출물 파일명 | 역할 및 관찰 내용 |
|:---|:---|
| **`extraction_plan.json`** | 에이전트가 탐색을 마친 뒤 도출한 URL 패턴, CSS 셀렉터, 페이지네이션 방식 청사진 |
| **`scraper.py`** | 에이전트가 작성한 순수 파이썬 크롤링 코드 (requests + BeautifulSoup / Playwright 등) |
| **`*_result.json`** | 실제로 웹사이트에서 수집되어 디스크에 저장된 최종 데이터셋 |
| **`*_run.log` / `scrape.log`** | 스크립트 실행 로그 및 에이전트의 턴별 생각(Thought)과 도구 호출 내역 |
| **`*_structured.json`** | 전체 ReAct 루프의 입력, 도구 호출(Tool Calls), 응답이 JSON으로 기록된 전체 Trajectory |

---

### 4단계: 심화 실습 (상위 레벨 시나리오 도전)

`quotes_01_pagination.md`를 통과했다면, `evaluate/evaluate_config.yaml`에서 상위 난이도 시나리오를 활성화하여 에이전트의 도구 에스컬레이션 능력을 테스트해 보세요:

1. **`quotes_02_tag_filter.md`**: 태그별 필터링 페이지 이동 및 수집
2. **`ajax_01_playwright_wait.md`**: 동적 지연 렌더링(AJAX) 대기 후 데이터 수집
3. **`danawa_01_filter_search.md`**: 복잡한 쇼핑몰 필터 탐색 및 테이블 데이터 파싱

---

## ✅ 성공 검증 체크리스트
- [ ] `python -m evaluate.run_scraper_scenarios` 명령어로 평가가 정상 완료되었는가?
- [ ] `artifacts/runs/` 하위 폴더에 `scraper.py` 및 결과 JSON 파일이 생성되었는가?
- [ ] 최종 평가 피드백에서 `is_pass: True` 및 높은 스키마 점수를 획득했는가?
- [ ] 로그 파일을 통해 에이전트의 `탐색 ➔ 코드작성 ➔ 실행 ➔ 저장` 전 과정을 확인했는가?

수고하셨습니다! 이제 여러분은 에이전트를 단순히 실행하는 것을 넘어, **에이전트의 성능을 정량적으로 평가하고 분석하는 관측성(Observability) 체계**를 이해했습니다. 🚀
