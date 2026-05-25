import os
import base64
import json
import mimetypes
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

@tool
def read_image_and_analyze(image_path: str, query_hint: str = "이 이미지의 내용을 상세히 설명해줘.") -> str:
    """
    로컬 이미지 파일을 읽고, Vision AI를 사용하여 이미지의 내용을 텍스트로 상세히 분석하여 반환합니다.

    Args:
        image_path (str): 분석할 이미지의 파일 경로
        query_hint (str): 이미지에서 중점적으로 파악해야 할 내용
    """
    if not os.path.exists(image_path):
        return f"Error: 파일을 찾을 수 없습니다. 경로: {image_path}"

    try:
        mime_type, _ = mimetypes.guess_type(image_path)
        if not mime_type: mime_type = "image/png"

        with open(image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')

        vision_llm = ChatOpenAI(model="gpt-5-mini", temperature=0)

        messages = [
            HumanMessage(
                content=[
                    {"type": "text", "text": f"당신은 유능한 이미지 분석가입니다. 다음 요청에 맞춰 이미지를 분석하세요: {query_hint}"},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime_type};base64,{encoded_string}"}
                    }
                ]
            )
        ]

        result = vision_llm.invoke(messages)
        return f"[이미지 분석 결과 - {os.path.basename(image_path)}]\n{result.content}"

    except Exception as e:
        return f"Error: 이미지 분석 중 오류 발생. {str(e)}"

# --- Web Search Tool ---
try:
    from langchain_tavily import TavilySearch
    tavily_search = TavilySearch(max_results=5, topic="general", search_depth="advanced", include_raw_content=True)
except Exception:
    # TAVILY_API_KEY가 없거나 라이브러리가 없으면 None으로 대체
    tavily_search = None

@tool
def web_search_custom_tool(query: str) -> str:
    """
    웹 검색을 수행하여 최신 정보를 수집합니다.
    """
    print(f"---웹 검색 도구 호출: {query}---")

    try:
        response = tavily_search.invoke({"query": query})
    except Exception as e:
        return f"검색 중 오류가 발생했습니다: {e}"

    processed_results = []
    MAX_LENGTH = 4000

    if isinstance(response, list):
        items = response
    elif isinstance(response, dict) and "results" in response:
        items = response["results"]
    else:
        return "검색 결과가 없습니다."

    for item in items:
        raw_text = item.get("raw_content")
        snippet_text = item.get("content", "")

        if raw_text and len(raw_text) > 500:
            final_content = raw_text
            data_source = "raw_full_text"
        else:
            final_content = snippet_text
            data_source = "snippet_fallback"

        if len(final_content) > MAX_LENGTH:
            final_content = final_content[:MAX_LENGTH] + "...(중략)"

        doc_data = {
            "title": item.get("title"),
            "url": item.get("url"),
            "content": final_content,
            "source_type": data_source
        }

        processed_results.append(json.dumps(doc_data, ensure_ascii=False))

    return "\n\n".join(processed_results)
