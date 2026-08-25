import json
import os
from typing import Dict, Any, Tuple
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from app.utils import init_chat_model
from evaluate.scenario_parser import Scenario
import jsonschema
from jsonschema.exceptions import ValidationError


class EvaluationFeedback(BaseModel):
    is_pass: bool = Field(description="전체 평가 통과 여부 (True: 통과, False: 실패)")
    schema_score: int = Field(description="스키마 준수 점수 (0~100)")
    strategy_score: int = Field(description="전략 준수 점수 (0~100)")
    feedback: str = Field(description="평가 사유 및 개선이 필요한 점에 대한 상세 피드백")


def validate_schema(data: Any, expected_schema: Dict[str, Any]) -> Tuple[bool, str]:
    """JSON 데이터가 expected_schema에 맞는지 검증합니다."""
    if not expected_schema:
        return True, "스키마 검증 생략 (expected_schema가 비어있음)"
    
    try:
        jsonschema.validate(instance=data, schema=expected_schema)
        return True, "스키마 검증 통과"
    except ValidationError as e:
        return False, f"스키마 검증 실패: {e.message}"
    except Exception as e:
        return False, f"스키마 검증 중 알 수 없는 오류: {str(e)}"


async def evaluate_scenario_result(
    scenario: Scenario,
    json_output_path: str,
    agent_code: str,
    agent_report: str
) -> EvaluationFeedback:
    """
    주어진 시나리오에 대해 데이터 스키마 및 수집 전략을 종합적으로 평가합니다.
    """
    # 1. Schema Validation
    schema_pass = False
    schema_feedback_msg = "결과 파일 없음"
    data = None
    
    if os.path.exists(json_output_path):
        try:
            with open(json_output_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            schema_pass, schema_feedback_msg = validate_schema(data, scenario.expected_schema)
        except json.JSONDecodeError:
            schema_pass = False
            schema_feedback_msg = f"JSON 파일 파싱 실패: {json_output_path}"
    else:
        schema_pass = False
        schema_feedback_msg = f"결과 파일이 존재하지 않음: {json_output_path}"

    # 2. Strategy Validation (LLM-as-a-Judge)
    eval_model = init_chat_model("gemini-3.7-flash", temperature=0.0)
    structured_evaluator = eval_model.with_structured_output(EvaluationFeedback)
    
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", "당신은 멀티에이전트 크롤링 파이프라인과 스크래핑 에이전트의 작업 결과물을 공정하고 엄격하게 평가하는 시니어 AI 평가자(Evaluator)입니다."),
        ("user", """
다음 시나리오에 대한 에이전트의 작업 결과물을 평가해주세요.

[시나리오 정보]
- 시나리오 ID: {scenario_id}
- 난이도: {difficulty}
- 목표 사이트: {target_url}

[평가 기준 (evaluation_criteria)]
{evaluation_criteria}

[작업 결과]
- 스키마 검증 결과: {schema_validation_result}

[에이전트가 작성한 코드]
```python
{agent_code}
```

[에이전트 최종 보고서]
{agent_report}

위 정보를 바탕으로, 다음을 수행하세요:
1. 에이전트가 작성한 코드와 보고서가 '평가 기준(Navigator/Coder 전략)'을 제대로 충족했는지 면밀히 검토하세요. (예: 가벼운 HTTP 클라이언트 활용, 지연 시간/대기 처리, 엔드포인트 역공학, 결측치 null 처리 등)
2. 스키마 검증이 실패했다면 최종 is_pass는 무조건 False가 되어야 합니다.
3. 평가 기준(strategy)을 충실히 지켰다면 90~100점, 부분적으로 미흡하다면 적절히 감점하세요.
4. 개선점에 대한 명확한 피드백을 제공하세요.
        """)
    ])

    criteria_str = json.dumps(scenario.evaluation_criteria, ensure_ascii=False, indent=2)
    chain = prompt_template | structured_evaluator
    
    print(f"\n🧠 [Evaluator] '{scenario.scenario_id}' 시나리오 결과 채점 중 (LLM-as-a-Judge)...")
    
    result: EvaluationFeedback = await chain.ainvoke({
        "scenario_id": scenario.scenario_id,
        "difficulty": scenario.difficulty,
        "target_url": scenario.target_url,
        "evaluation_criteria": criteria_str,
        "schema_validation_result": "Pass" if schema_pass else f"Fail ({schema_feedback_msg})",
        "agent_code": agent_code[:4000],
        "agent_report": agent_report[:3000]
    })

    # 스키마 통과 여부에 따른 보정
    if not schema_pass:
        result.is_pass = False
        if result.schema_score > 0:
            result.schema_score = 0
            
    print(f"  -> 평가 완료: {'✅ PASS' if result.is_pass else '❌ FAIL'} (스키마: {result.schema_score}점, 전략: {result.strategy_score}점)")
    return result
