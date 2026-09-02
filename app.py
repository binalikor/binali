import io
import os
import urllib.parse
from PIL import Image
import requests
import streamlit as st

st.set_page_config(page_title="16:9 한국 설화 원화 스튜디오", layout="wide")
st.title("🎬 16:9 한국 설화 원화 스튜디오")
st.caption("외부 영상 모듈 없이 기본 엔진만으로 1:1 왜곡 없는 16:9 네이티브 원화를 생성합니다.")

# 사이드바 설정
DEFAULT_HF_TOKEN = "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"

with st.sidebar:
    st.header("🔑 API 설정")
    hf_token = st.text_input("Hugging Face Token", value=DEFAULT_HF_TOKEN, type="password")
    model_choice = st.selectbox(
        "사용 모델",
        ["ByteDance/SDXL-Lightning", "stabilityai/sdxl-turbo"]
    )

st.subheader("1. 장면 묘사 입력")
user_desc = st.text_area(
    "장면 설명 (한국어)",
    value="한국 전래동화 이야기책 스타일 삽화. 거대한 신 미륵의 전신 모습. 얼굴 턱까지 덮는 큰 짚 고깔모자를 쓰고, 칡넝쿨로 짠 갈색 원시 옷을 입고 있다. 흙빛 피부에 눈빛은 따뜻하다. 부드러운 먹선과 수채화 채색, 동화책 삽화 스타일, 흰색 배경",
    height=100
)

# 한국 설화 프롬프트 구조화 함수
def build_art_prompt(ko_text):
    if not ko_text.strip():
        return ""
    replaced = ko_text.replace("미륵", "ancient Korean mythical giant creator god Mireuk")
    url = "https://translate.googleapis.com/translate_a/single"
    params = {"client": "gtx", "sl": "ko", "tl": "en", "dt": "t", "q": replaced}
    try:
        res = requests.get(url, params=params, timeout=5)
        if res.status_code == 200:
            en_base = "".join([piece[0] for piece in res.json()[0] if piece[0]]).strip()
        else:
            en_base = replaced
    except Exception:
        en_base = replaced
    return f"{en_base}, Korean traditional fairy tale illustration, watercolor and soft ink brush, 16:9 wide composition, sharp details"

# Hugging Face 인퍼런스 호출 (16:9 정규 규격 1024x576)
def request_hf_image(prompt, token, model):
    clean_token = token.strip()
    if not clean_token.startswith("hf_"):
        clean_token = "hf_" + clean_token

    api_url = f"https://router.huggingface.co/hf-inference/models/{model}"
    headers = {
        "Authorization": f"Bearer {clean_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "inputs": prompt,
        "parameters": {"width": 1024, "height": 576}
    }
    
    res = requests.post(api_url, headers=headers, json=payload, timeout=30)
    if res.status_code == 200:
        return res.content, None
    elif res.status_code == 503:
        return None, "서버가 모델을 로딩 중입니다. 15초 후 다시 눌러주세요."
    elif res.status_code == 401:
        return None, "인증 실패: Hugging Face 토큰을 확인하세요."
    else:
        return None, f"오류 ({res.status_code}): {res.text}"

# 생성 실행
if st.button("🎨 16:9 원화 생성 시작 🚀"):
    if not hf_token.strip():
        st.error("토큰을 입력하세요.")
    elif not user_desc.strip():
        st.warning("설명을 입력하세요.")
    else:
        status_box = st.empty()
        status_box.info("16:9 규격으로 원화를 렌더링 중입니다...")
        try:
            prompt_en = build_art_prompt(user_desc)
            img_bytes, err = request_hf_image(prompt_en, hf_token, model_choice)
            if img_bytes:
                img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
                st.session_state["base_image"] = img
                st.session_state["img_bytes"] = img_bytes
                status_box.success(f"원화 생성 성공! ({img.size[0]}x{img.size[1]} - 16:9 왜곡 없음)")
            else:
                status_box.error(err)
        except Exception as e:
            status_box.error(f"통신 오류: {e}")

# 결과 화면 및 다운로드
if "base_image" in st.session_state:
    st.divider()
    base_img = st.session_state["base_image"]
    st.image(base_img, caption=f"규격: {base_img.size[0]}x{base_img.size[1]} (16:9 와이드)", use_container_width=True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            label="📥 16:9 고화질 원화 다운로드 (PNG)",
            data=st.session_state["img_bytes"],
            file_name="mireuk_scene_16_9.png",
            mime="image/png"
        )
