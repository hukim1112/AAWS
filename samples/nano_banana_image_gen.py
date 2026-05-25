"""
Nano Banana (Gemini Image Generation) 샘플 코드
=============================================
Gemini의 이미지 생성 기능(일명 Nano Banana)을 사용하여
텍스트 프롬프트로부터 이미지를 생성하는 예제입니다.

두 가지 방식을 제공합니다:
  1. LangChain 통합 (ChatGoogleGenerativeAI) — 에이전트 도구로 바로 활용 가능
  2. Google GenAI SDK 직접 호출 — 이미지 편집 등 고급 기능 사용 시

사전 설치:
    pip install langchain-google-genai google-genai pillow python-dotenv

환경 변수:
    GOOGLE_API_KEY가 .env 파일에 설정되어 있어야 합니다.
"""

import os
import base64
from dotenv import load_dotenv

load_dotenv(override=True)


# ═══════════════════════════════════════════════
# 방법 1: LangChain 통합 (권장 — 에이전트 연동 용이)
# ═══════════════════════════════════════════════

def generate_image_langchain(
    prompt: str,
    output_path: str = "generated_image.png",
    model_name: str = "gemini-3.1-flash-image-preview",
) -> str:
    """LangChain의 ChatGoogleGenerativeAI를 사용하여 이미지를 생성합니다.

    Args:
        prompt: 생성할 이미지를 설명하는 텍스트
        output_path: 저장할 이미지 파일 경로
        model_name: 사용할 Gemini 이미지 생성 모델 ID

    Returns:
        저장된 이미지 파일의 절대 경로
    """
    from langchain_google_genai import ChatGoogleGenerativeAI, Modality

    # 이미지 생성 모달리티를 지정하여 모델 초기화
    llm = ChatGoogleGenerativeAI(
        model=model_name,
        response_modalities=[Modality.IMAGE, Modality.TEXT],
    )

    # 프롬프트를 전달하여 이미지 생성
    response = llm.invoke(prompt)

    # 디버그: 응답 구조 확인
    print(f"🔍 [DEBUG] response.content 타입: {type(response.content)}")
    if isinstance(response.content, list):
        for i, block in enumerate(response.content):
            print(f"🔍 [DEBUG] block[{i}] 타입={type(block)}, 값={str(block)[:200]}")
    
    # 응답에서 이미지 블록 추출 및 저장
    if isinstance(response.content, list):
        for block in response.content:
            # 형식 1: dict with "type": "image" (표준)
            if isinstance(block, dict) and block.get("type") == "image":
                image_data = base64.b64decode(block["data"])
                with open(output_path, "wb") as f:
                    f.write(image_data)
                print(f"✅ [LangChain] 이미지 저장 완료: {os.path.abspath(output_path)}")
                return os.path.abspath(output_path)
            
            # 형식 2: dict with "type": "image_url" 
            elif isinstance(block, dict) and block.get("type") == "image_url":
                url_data = block.get("image_url", {}).get("url", "")
                if url_data.startswith("data:"):
                    # data:image/png;base64,xxxxx 형식
                    b64_str = url_data.split(",", 1)[1]
                    image_data = base64.b64decode(b64_str)
                    with open(output_path, "wb") as f:
                        f.write(image_data)
                    print(f"✅ [LangChain] 이미지 저장 완료: {os.path.abspath(output_path)}")
                    return os.path.abspath(output_path)

            # 형식 3: dict with "type": "media"
            elif isinstance(block, dict) and block.get("type") == "media":
                media_data = block.get("data", "") or block.get("content", "")
                if media_data:
                    image_data = base64.b64decode(media_data) if isinstance(media_data, str) else media_data
                    with open(output_path, "wb") as f:
                        f.write(image_data)
                    print(f"✅ [LangChain] 이미지 저장 완료: {os.path.abspath(output_path)}")
                    return os.path.abspath(output_path)

            elif isinstance(block, dict) and block.get("type") == "text":
                print(f"📝 [LangChain] 텍스트 응답: {block.get('text', '')}")

    # content가 문자열인 경우 (텍스트만 반환된 경우)
    elif isinstance(response.content, str):
        print(f"📝 [LangChain] 텍스트 응답: {response.content}")

    print("⚠️ 이미지를 생성하지 못했습니다.")
    return ""


# ═══════════════════════════════════════════════
# 방법 2: Google GenAI SDK 직접 호출 (고급 기능용)
# ═══════════════════════════════════════════════

def generate_image_sdk(
    prompt: str,
    output_path: str = "generated_image.png",
    model_name: str = "gemini-3.1-flash-image-preview",
) -> str:
    """Google GenAI SDK를 직접 사용하여 이미지를 생성합니다.
    이미지 편집 등 고급 기능이 필요할 때 사용합니다.

    Args:
        prompt: 생성할 이미지를 설명하는 텍스트
        output_path: 저장할 이미지 파일 경로
        model_name: 사용할 모델 ID

    Returns:
        저장된 이미지 파일의 절대 경로
    """
    from google import genai
    from google.genai import types
    from PIL import Image
    from io import BytesIO

    client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

    response = client.models.generate_content(
        model=model_name,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE", "TEXT"],
        ),
    )

    for part in response.candidates[0].content.parts:
        if part.inline_data and part.inline_data.mime_type.startswith("image/"):
            image = Image.open(BytesIO(part.inline_data.data))
            image.save(output_path)
            print(f"✅ [SDK] 이미지 저장 완료: {os.path.abspath(output_path)}")
            return os.path.abspath(output_path)
        elif part.text:
            print(f"📝 [SDK] 텍스트 응답: {part.text}")

    print("⚠️ 이미지를 생성하지 못했습니다.")
    return ""


def edit_image_with_prompt(
    image_path: str,
    edit_prompt: str,
    output_path: str = "edited_image.png",
    model_name: str = "gemini-3.1-flash-image-preview",
) -> str:
    """기존 이미지를 로드하고, 텍스트 프롬프트로 이미지를 편집합니다.
    (SDK 직접 호출 — LangChain에서는 아직 이미지 입력+생성 조합이 제한적)

    Args:
        image_path: 편집할 원본 이미지 경로
        edit_prompt: 편집 지시사항 (예: "배경을 우주로 바꿔줘")
        output_path: 편집된 이미지를 저장할 경로
        model_name: 사용할 모델 ID

    Returns:
        편집된 이미지 파일의 절대 경로
    """
    from google import genai
    from google.genai import types
    from PIL import Image
    from io import BytesIO

    client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
    original_image = Image.open(image_path)

    response = client.models.generate_content(
        model=model_name,
        contents=[edit_prompt, original_image],
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE", "TEXT"],
        ),
    )

    for part in response.candidates[0].content.parts:
        if part.inline_data and part.inline_data.mime_type.startswith("image/"):
            image = Image.open(BytesIO(part.inline_data.data))
            image.save(output_path)
            print(f"✅ [SDK] 편집된 이미지 저장 완료: {os.path.abspath(output_path)}")
            return os.path.abspath(output_path)
        elif part.text:
            print(f"📝 [SDK] 텍스트 응답: {part.text}")

    print("⚠️ 이미지 편집에 실패했습니다.")
    return ""


# ─────────────────────────────────────────────
# 실행 예시
# ─────────────────────────────────────────────
if __name__ == "__main__":
    # 저장 경로를 samples/ 폴더로 설정
    SAMPLES_DIR = os.path.dirname(os.path.abspath(__file__))

    test_prompt = (
        "A tiny hamster wearing a little hard hat and safety goggles, "
        "sitting inside a teacup, reading a huge book titled 'DATA SCIENCE', "
        "surrounded by floating bar charts and pie charts made of cheese, "
        "watercolor illustration style, warm pastel colors, cozy atmosphere"
    )

    # ── 방법 1: LangChain 통합 ──
    print("=" * 50)
    print("🎨 [방법 1] LangChain 통합으로 이미지 생성")
    print("=" * 50)
    generate_image_langchain(
        prompt=test_prompt,
        output_path=os.path.join(SAMPLES_DIR, "sample_langchain.png"),
    )

    # ── 방법 2: SDK 직접 호출 ──
    print("\n" + "=" * 50)
    print("🎨 [방법 2] Google GenAI SDK로 이미지 생성")
    print("=" * 50)
    sdk_path = os.path.join(SAMPLES_DIR, "sample_sdk.png")
    generate_image_sdk(
        prompt=test_prompt,
        output_path=sdk_path,
    )

    # ── 이미지 편집 (SDK only) ──
    if os.path.exists(sdk_path):
        print("\n" + "=" * 50)
        print("✏️ [방법 2] 이미지 편집 (SDK)")
        print("=" * 50)
        edit_image_with_prompt(
            image_path=sdk_path,
            edit_prompt="배경을 판타지 숲속으로 바꾸고, 햄스터 주변에 반딧불이와 작은 버섯집들을 추가해줘",
            output_path=os.path.join(SAMPLES_DIR, "sample_edited.png"),
        )
