import os
import json
import subprocess
from langchain.tools import tool
from .common import ARTIFACT_DIR

@tool(parse_docstring=True)
def read_code_file(filepath: str, start_line: int = 1, end_line: int = None) -> str:
    """파일 내용을 줄 번호와 함께 읽어옵니다.
    
    Args:
        filepath: 읽을 파일명 (artifacts/code 폴더 기준)
        start_line: 시작 줄
        end_line: 끝 줄
    """
    sf = os.path.join(ARTIFACT_DIR, os.path.basename(filepath))
    if not os.path.exists(sf): return "[Error] 존재하지 않는 파일입니다."
    with open(sf, "r", encoding="utf-8") as f: lines = f.readlines()
    end = end_line if end_line else len(lines)
    start = max(1, start_line)
    return "\n".join([f"{i+1:03d} | {lines[i].rstrip()}" for i in range(start-1, min(end, len(lines)))])

@tool(parse_docstring=True)
def edit_code_file(filepath: str, start_line: int, end_line: int, new_content: str) -> str:
    """기존 파이썬 파일의 특정 라인 구간만 외과수술처럼 교체합니다.
    
    Args:
        filepath: 수정할 파일명
        start_line: 시작 줄
        end_line: 교체가 완료될 줄 번호
        new_content: 새로 삽입될 코드 덩어리
    """
    sf = os.path.join(ARTIFACT_DIR, os.path.basename(filepath))
    with open(sf, "r", encoding="utf-8") as f: lines = f.readlines()
    nl = [l+"\n" for l in new_content.split("\n")]
    lines = lines[:start_line-1] + nl + lines[end_line:]
    with open(sf, "w", encoding="utf-8") as f: f.writelines(lines)
    return f"[Success] {filepath} 교체 완료"

@tool(parse_docstring=True)
def create_new_file(filepath: str, content: str) -> str:
    """파이썬 또는 텍스트 파일을 새로 완전히 생성합니다.
    
    Args:
       filepath: 파일명
       content: 담길 코드 원문
    """
    with open(os.path.join(ARTIFACT_DIR, os.path.basename(filepath)), "w", encoding="utf-8") as f:
        f.write(content)
    return f"[Success] {filepath} 생성"

@tool(parse_docstring=True)
def write_text_file(filepath: str, content: str) -> str:
    """JSON, Markdown, CSV 등 텍스트 문서를 작성합니다 (create_new_file 동일 스펙).
    
    Args:
        filepath: 파일명
        content: 파일에 기록할 텍스트 내용
    """
    return create_new_file.invoke({"filepath":filepath, "content":content})

@tool(parse_docstring=True)
def run_python_script(filepath: str, script_args: str = "") -> str:
    """작성한 특정 파이썬 코드를 로컬 환경에서 비동기가 아닌 서브프로세스로 실행해 봅니다.
    
    Args:
       filepath: 파일 명
       script_args: CLI 어규먼트
    """
    sf = os.path.basename(filepath)
    cmd = ["python", sf]
    if script_args: cmd.extend(script_args.split())
    
    try:
        res = subprocess.run(cmd, cwd=ARTIFACT_DIR, capture_output=True, text=True, timeout=120)
        out = res.stdout
        if res.stderr: out += f"\n[Error Output]\n{res.stderr}"
        return out if out.strip() else "[시스템] 실행되었으나 표준 출력이 없습니다."
    except Exception as e:
        return f"[시스템 에러] {e}"

@tool(parse_docstring=True)
def validate_collected_data(filepath: str) -> str:
    """수집된 JSON 데이터 파일(리스트 딕셔너리 구조)의 품질 및 정합성을 체크합니다.
    
    Args:
        filepath: 검증할 JSON 파일명
    """
    if os.path.exists(filepath):
        sf = filepath
    elif os.path.exists(os.path.join(ARTIFACT_DIR, os.path.basename(filepath))):
        sf = os.path.join(ARTIFACT_DIR, os.path.basename(filepath))
    else:
        sf = filepath
        
    try:
        with open(sf, 'r', encoding='utf-8') as f: data = json.load(f)
    except Exception as e: 
        return f"[Error] 파일 읽기 또는 파싱 불가: {e}"
    
    if not isinstance(data, list): return "[Info] 최상위가 배열이 아닙니다."
    if not data: return "[Warning] 수집된 데이터가 0건입니다!"
    
    fields = list(data[0].keys())
    rep = [f"📊 총 {len(data)}건 수집"]
    for field in fields:
        empty = sum(1 for d in data if not d.get(field))
        rep.append(f"   필드 '{field}'의 빈 값 수: {empty}")
    return "\n".join(rep)
