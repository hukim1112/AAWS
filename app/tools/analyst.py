"""
app/tools/analyst.py
====================
Analyst 에이전트 전용 도구 모음 (8대 핵심 도구) - 강건성(Robustness) 강화 버전
1. profile_data_quality: 데이터 품질, 스키마 정합성, 결측률, 중복률 정량 검증 (유연한 Dict/List 파싱)
2. analyze_agent_performance: 실행 시간, LLM 호출, 토큰/비용 진단 및 병목 포착 (안전한 예외 가드)
3. save_collection_strategy: 수집 성공 전략을 artifacts/results/strategy/[scenario_id]_strategy.md 에 저장
4. generate_infographic_image: Gemini Nano Banana 기반 데이터 요약 인포그래픽 이미지 생성 (LangChain + SDK Dual Fallback)
5. generate_image: Gemini Nano Banana 기반 일반 텍스트 프롬프트 이미지 생성
6. edit_image_with_prompt: 기존 이미지를 텍스트 지시로 편집 (GenAI SDK)
7. create_visualization_charts: Matplotlib/Seaborn 차트 생성 및 fallback 강제 저장 보장
8. write_analyst_report: 종합 마크다운 분석 리포트 보관 및 상대경로 변환
"""

import os
import json
import base64
import time
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

from langchain.tools import tool

load_dotenv(override=True)

# ---------------------------------------------------------
# 1. profile_data_quality: 데이터 품질 및 정합성 검증 도구
# ---------------------------------------------------------

@tool(parse_docstring=True)
def profile_data_quality(filepath: str) -> str:
    """수집된 JSON 데이터 파일의 품질, 스키마 준수율, 결측치, 중복률 및 기본 통계 정보를 다각도로 검증합니다.

    Args:
        filepath: 수집된 JSON 결과 파일의 절대 또는 상대 경로 (예: 'artifacts/results/quotes_01_pagination/runs/20260728_141922/sup_result.json')

    Returns:
        데이터 품질 프로파일링 결과를 정량적으로 정리한 마크다운/텍스트 요약
    """
    if not os.path.exists(filepath):
        return f"❌ 오류: 데이터 파일을 찾을 수 없습니다. 경로: {filepath}"
    
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
        
        data = []
        if isinstance(raw_data, list):
            data = raw_data
        elif isinstance(raw_data, dict):
            # 중첩된 list 탐색 (예: {"data": [...]}, {"items": [...]}, {"quotes": [...]})
            found_list = None
            for key, val in raw_data.items():
                if isinstance(val, list) and len(val) > 0:
                    found_list = val
                    break
            if found_list is not None:
                data = found_list
            else:
                data = [raw_data]
        else:
            return f"⚠️ 경고: 수집 데이터가 구조화된 리스트/디셔너리 형식이 아닙니다 (타입: {type(raw_data)})."

        total_records = len(data)
        if total_records == 0:
            return "⚠️ 경고: 데이터 파일이 비어 있습니다 (0개 레코드)."

        # 스키마 및 필드 검사
        field_counts: Dict[str, int] = {}
        field_types: Dict[str, set] = {}
        null_counts: Dict[str, int] = {}

        for item in data:
            if not isinstance(item, dict):
                continue
            for k, v in item.items():
                field_counts[k] = field_counts.get(k, 0) + 1
                if k not in field_types:
                    field_types[k] = set()
                field_types[k].add(type(v).__name__)
                
                if v is None or v == "" or (isinstance(v, list) and len(v) == 0):
                    null_counts[k] = null_counts.get(k, 0) + 1

        # 중복 데이터 검사
        seen = set()
        duplicate_count = 0
        for item in data:
            if isinstance(item, dict):
                item_str = json.dumps(item, sort_keys=True, ensure_ascii=False)
            else:
                item_str = str(item)
                
            if item_str in seen:
                duplicate_count += 1
            else:
                seen.add(item_str)

        # 리포트 구성
        report = []
        report.append(f"### 📊 [Data Quality Profiling Report]")
        report.append(f"- **총 레코드 수**: {total_records}건")
        report.append(f"- **중복 레코드 수**: {duplicate_count}건 (중복률: {duplicate_count/total_records*100:.1f}%)")
        report.append(f"- **검출된 필드 목록 ({len(field_counts)}개)**:")
        
        for k in sorted(field_counts.keys()):
            count = field_counts[k]
            types_str = ", ".join(sorted(list(field_types[k])))
            null_cnt = null_counts.get(k, 0)
            null_pct = (null_cnt / total_records) * 100
            status = "✅ PASS" if null_pct < 5 else ("⚠️ WARNING" if null_pct < 20 else "🔴 CRITICAL")
            report.append(f"  - **`{k}`**: 존재율 {count}/{total_records} ({count/total_records*100:.1f}%), 타입 [{types_str}], 결측/빈값 {null_cnt}건 ({null_pct:.1f}%) -> {status}")

        return "\n".join(report)

    except Exception as e:
        return f"❌ 데이터 프로파일링 중 오류 발생: {str(e)}"


# ---------------------------------------------------------
# 2. analyze_agent_performance: 에이전트 실행 및 비용 진단 도구
# ---------------------------------------------------------

@tool(parse_docstring=True)
def analyze_agent_performance(log_dir: str) -> str:
    """수집 과정에서 발생한 sup_structured_log.json 및 sup_log.md 실행 로그를 파싱하여 에이전트별 실행 시간, 호출 횟수, 토큰 소모량, 비용 추산 및 병목 구간을 진단합니다.

    Args:
        log_dir: 실행 결과 폴더 경로 (예: 'artifacts/results/quotes_01_pagination/runs/20260728_141922')

    Returns:
        에이전트 실행 성능 및 토큰/비용 진단 마크다운 리포트
    """
    struct_log_path = os.path.join(log_dir, "sup_structured_log.json")
    sup_log_path = os.path.join(log_dir, "sup_log.md")

    if not os.path.exists(struct_log_path) and not os.path.exists(sup_log_path):
        return f"❌ 로그 파일을 찾을 수 없습니다. 경로: {log_dir}"

    report = ["### ⚡ [Agent Execution & Cost Audit Report]"]

    # 1. 구조화 로그 분석
    if os.path.exists(struct_log_path):
        try:
            with open(struct_log_path, "r", encoding="utf-8") as f:
                log_data = json.load(f)
            
            total_duration = log_data.get("total_duration_sec", 0)
            summary = log_data.get("summary", {})
            agent_counts = summary.get("agent_tool_counts", {})
            tool_durations = summary.get("tool_avg_duration_sec", {})

            report.append(f"- **총 실행 소요 시간**: {total_duration:.2f}초")
            if agent_counts:
                report.append("- **에이전트별 도구 호출 횟수**:")
                for ag, cnt in agent_counts.items():
                    report.append(f"  - `{ag}`: {cnt}회 호출")
            
            if tool_durations:
                report.append("- **도구별 평균 소요시간**:")
                for t_name, avg_d in tool_durations.items():
                    report.append(f"  - `{t_name}`: {avg_d:.2f}초")

        except Exception as e:
            report.append(f"⚠️ structured log 파싱 중 예외 처리됨: {str(e)}")

    # 2. sup_log.md 기반 추가 로그 특이점 및 토큰/루프 분석
    if os.path.exists(sup_log_path):
        try:
            with open(sup_log_path, "r", encoding="utf-8") as f:
                log_text = f.read()

            browser_use_steps = log_text.count("Step ")
            error_warnings = log_text.count("⚠️") + log_text.count("❌")
            
            report.append(f"- **Browser-Use 탐색 Step 수**: 약 {browser_use_steps}단계")
            report.append(f"- **감지된 에러/경고 이벤트 수**: {error_warnings}건")
            
            # 추정 토큰 및 비용 계산
            estimated_tokens = len(log_text) * 1.2
            estimated_cost_usd = (estimated_tokens / 1000) * 0.00015
            report.append(f"- **추산 소모 토큰량**: 약 {int(estimated_tokens):,} tokens")
            report.append(f"- **추산 API 비용**: 약 ${estimated_cost_usd:.4f} USD (₩{estimated_cost_usd * 1400:.2f} 원)")

        except Exception as e:
            report.append(f"⚠️ sup_log.md 분석 중 예외 처리됨: {str(e)}")

    return "\n".join(report)


# ---------------------------------------------------------
# 3. save_collection_strategy: 수집 성공 전략 파일 저장 도구
# ---------------------------------------------------------

@tool(parse_docstring=True)
def save_collection_strategy(scenario_id: str, strategy_content: str) -> str:
    """분석 결과 도출된 수집 성공 노하우, Selector 팁, 방어/차트 우회 전략을 'artifacts/results/strategy/[scenario_id]_strategy.md' 파일로 보관합니다.

    Args:
        scenario_id: 시나리오 ID (예: 'quotes_01_pagination')
        strategy_content: 마크다운 형태의 핵심 수집 전략 내용

    Returns:
        저장된 전략 파일의 절대 경로
    """
    strategy_dir = os.path.abspath(os.path.join("artifacts", "results", "strategy"))
    os.makedirs(strategy_dir, exist_ok=True)
    
    file_path = os.path.join(strategy_dir, f"{scenario_id}_strategy.md")
    
    header = f"# 🎯 [Collection Strategy] {scenario_id}\n\n"
    header += f"> **최종 업데이트**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
    header += f"> **참고 가이드**: 이 파일은 다른 에이전트(Supervisor, Navigator, Coder)가 수집 시 최선의 전략 및 셀렉터 방식을 수용하기 위해 참고하는 공식 전략 가이드입니다.\n\n"
    
    full_content = header + strategy_content.strip() + "\n"

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(full_content)

    print(f"✅ [Strategy Saved] 수집 전략 저장 완료: {file_path}")
    return os.path.abspath(file_path)


# ---------------------------------------------------------
# 4. generate_infographic_image: Gemini Nano Banana 인포그래픽 생성
# ---------------------------------------------------------

@tool(parse_docstring=True)
def generate_infographic_image(prompt: str, output_path: str) -> str:
    """Gemini Nano Banana (Image Generation) 기능으로 수집 데이터 요약 및 인사이트 인포그래픽 이미지를 생성합니다.

    Args:
        prompt: 생성할 인포그래픽 이미지에 대한 상세 텍스트 프롬프트 (영문 작성 권장)
        output_path: 저장할 PNG 이미지 경로 (예: 'artifacts/results/quotes_01_pagination/infographic.png')

    Returns:
        생성 및 저장된 인포그래픽 이미지의 경로 또는 실패 메시지
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    # 1. LangChain 방식 시도
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI, Modality
        llm = ChatGoogleGenerativeAI(
            model="gemini-3.1-flash-image-preview",
            response_modalities=[Modality.IMAGE, Modality.TEXT],
        )
        response = llm.invoke(prompt)

        if isinstance(response.content, list):
            for block in response.content:
                if isinstance(block, dict) and block.get("type") == "image":
                    img_data = base64.b64decode(block["data"])
                    with open(output_path, "wb") as f:
                        f.write(img_data)
                    return os.path.abspath(output_path)
                elif isinstance(block, dict) and block.get("type") == "image_url":
                    url_data = block.get("image_url", {}).get("url", "")
                    if url_data.startswith("data:"):
                        b64_str = url_data.split(",", 1)[1]
                        img_data = base64.b64decode(b64_str)
                        with open(output_path, "wb") as f:
                            f.write(img_data)
                        return os.path.abspath(output_path)

    except Exception as e:
        print(f"⚠️ [LangChain Image Gen Fallback Triggered]: {e}")

    # 2. Google GenAI SDK direct Fallback
    try:
        from google import genai
        from google.genai import types
        from PIL import Image
        from io import BytesIO

        client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
        response = client.models.generate_content(
            model="gemini-3.1-flash-image-preview",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"],
            ),
        )

        for part in response.candidates[0].content.parts:
            if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                image = Image.open(BytesIO(part.inline_data.data))
                image.save(output_path)
                return os.path.abspath(output_path)
    except Exception as e:
        return f"❌ 인포그래픽 이미지 생성 실패: {str(e)}"

    return f"❌ 인포그래픽 이미지 생성 실패 (모델 응답에 이미지 블록이 없음)."


# ---------------------------------------------------------
# 5. generate_image: 일반 이미지 생성 도구
# ---------------------------------------------------------

@tool(parse_docstring=True)
def generate_image(prompt: str, output_path: str) -> str:
    """Gemini Nano Banana 기능을 활용하여 텍스트 프롬프트 기반의 고품질 일반 시각화 이미지를 생성합니다.

    Args:
        prompt: 생성할 이미지에 대한 상세 지시 텍스트 (영문 권장)
        output_path: 저장할 PNG 파일 경로 (예: 'artifacts/results/quotes_01_pagination/generated_image.png')

    Returns:
        생성된 이미지의 저장 경로
    """
    return generate_infographic_image.invoke({"prompt": prompt, "output_path": output_path})


# ---------------------------------------------------------
# 6. edit_image_with_prompt: 이미지 편집 도구 (SDK)
# ---------------------------------------------------------

@tool(parse_docstring=True)
def edit_image_with_prompt(image_path: str, edit_prompt: str, output_path: str) -> str:
    """기존 이미지를 읽어들이고, 텍스트 프롬프트 지시에 맞춰 이미지를 추가/수정/편집합니다 (Google GenAI SDK 기반).

    Args:
        image_path: 편집할 원본 이미지 파일 경로
        edit_prompt: 이미지 편집 지시사항 (예: "배경을 다크모드 사이버펑크 스타일로 변경해줘")
        output_path: 편집 완료된 이미지 저장 경로 (예: 'artifacts/results/quotes_01_pagination/edited_image.png')

    Returns:
        편집 및 저장된 이미지 파일의 경로
    """
    if not os.path.exists(image_path):
        return f"❌ 원본 이미지를 찾을 수 없습니다. 경로: {image_path}"

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    try:
        from google import genai
        from google.genai import types
        from PIL import Image
        from io import BytesIO

        client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
        original_image = Image.open(image_path)

        response = client.models.generate_content(
            model="gemini-3.1-flash-image-preview",
            contents=[edit_prompt, original_image],
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"],
            ),
        )

        for part in response.candidates[0].content.parts:
            if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                image = Image.open(BytesIO(part.inline_data.data))
                image.save(output_path)
                return os.path.abspath(output_path)

        return "⚠️ 이미지 편집 실패: 모델이 이미지를 반환하지 않았습니다."

    except Exception as e:
        return f"❌ 이미지 편집 오류 발생: {str(e)}"


# ---------------------------------------------------------
# 7. create_visualization_charts: Matplotlib/Seaborn 차트 생성 도구 (Fallback 보장)
# ---------------------------------------------------------

@tool(parse_docstring=True)
def create_visualization_charts(chart_spec_code: str, output_path: str) -> str:
    """Matplotlib 및 Seaborn 파이썬 코드를 실행하여 데이터 통계 차트 PNG 이미지를 생성합니다.
    Seaborn 미설치 시 기본 Matplotlib으로 자동 fallback 렌더링되며, 파일 저장이 보장됩니다.

    Args:
        chart_spec_code: 실행할 파이썬 시각화 코드 문자열
        output_path: 차트 이미지를 저장할 목표 경로 (예: 'artifacts/results/quotes_01_pagination/chart_distribution.png')

    Returns:
        생성된 차트 이미지 파일 경로
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    
    try:
        import matplotlib
        matplotlib.use("Agg")  # Non-interactive backend
        import matplotlib.pyplot as plt
        
        # seaborn optional import fallback
        sns = None
        try:
            import seaborn as sns
        except ImportError:
            pass

        exec_globals = {
            "plt": plt,
            "sns": sns if sns is not None else plt,
            "os": os,
            "json": json,
            "output_path": output_path,
        }
        local_vars = {"output_path": output_path}

        exec(chart_spec_code, exec_globals, local_vars)
        
        # 실행 후 savefig가 안 불렸을 경우를 대비한 강제 저장 보장
        if not os.path.exists(output_path):
            plt.savefig(output_path, bbox_inches='tight', dpi=150)
            
        plt.close('all')

        if os.path.exists(output_path):
            return os.path.abspath(output_path)
        else:
            return f"⚠️ 차트 실행 완료되었으나 파일 생성 실패 ({output_path})"

    except Exception as e:
        # Fallback: 기본 matplotlib 사각형 경고 렌더링 보장
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            plt.figure(figsize=(6, 4))
            plt.text(0.5, 0.5, f"Chart Rendering Exception:\n{str(e)[:100]}", ha='center', va='center')
            plt.tight_layout()
            plt.savefig(output_path)
            plt.close('all')
            return os.path.abspath(output_path)
        except Exception:
            return f"❌ 차트 생성 실패: {str(e)}"


# ---------------------------------------------------------
# 8. write_analyst_report: 최종 마크다운 분석 리포트 저장 도구
# ---------------------------------------------------------

@tool(parse_docstring=True)
def write_analyst_report(report_content: str, output_path: str) -> str:
    """분석 결과, 데이터 품질, 에이전트 비용 진단, 생성된 차트/인포그래픽 이미지 링크(![설명](./이미지.png))를 통합한 마크다운 리포트를 보관합니다.

    Args:
        report_content: 작성된 마크다운 전체 텍스트 내용
        output_path: 리포트를 저장할 파일 경로 (예: 'artifacts/results/quotes_01_pagination/analysis_report.md')

    Returns:
        저장된 마크다운 리포트 파일의 절대 경로
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report_content.strip() + "\n")
        
        print(f"✅ [Report Saved] 분석 리포트 저장 완료: {output_path}")
        return os.path.abspath(output_path)
    except Exception as e:
        return f"❌ 리포트 저장 실패: {str(e)}"
