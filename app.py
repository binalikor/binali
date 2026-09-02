import io
import os
import urllib.parse
from PIL import Image
import requests
import streamlit as st

st.set_page_config(page_title="16:9 한국 설화 원화 스튜디오", layout="wide")
st.title("🎬 16:9 한국 설화 애니메이션 원화 스튜디오")
st.caption("Hugging Face 검증 엔드포인트(FLUX.1-schnell)를 통해 16:9 규격 원화를 직접 렌더링합니다.")

# 인증 토큰 기본값 설정
DEFAULT_HF_TOKEN = "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"

with st.sidebar:
    st.header("🔑 Hugging Face 설정")
    hf_token = st.text_input("Access Token", value=DEFAULT_HF_TOKEN, type="password")
    # 무료 인퍼런스 라우터 정식 지원 모델로 단일 고정
    model_name = "black-forest-labs/FLUX.1-schnell"
    st.text(f"연결 모델: {model_name}")

st.subheader("1. 장면 묘사 입력")
user_desc = st.text_area(
    "장면 설명 (한국어)",
    value="한국 전래동화 이야기책 스타일 삽화. 거대한 신 미륵의 전신 모습. 얼굴 턱까지 덮는 큰 짚 고깔모자를 쓰고, 칡넝쿨로 짠 갈색 원시 옷을 입고 있다. 흙빛 피부에 눈빛은 따뜻하다. 부드러운 먹선과 수채화 채색, 동화책 삽화 스타일, 흰색 배경",
    height=100
)

def build_art_prompt(ko_text):
    if not ko_text.strip():
        return ""
    replaced = ko_text.replace("미륵", "ancient gigantic Korean mythical creator god Mireuk")
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
        
    return f"{en_base}, Korean traditional fairy tale book illustration, soft sumi-e ink brush linework and gentle watercolor, 16:9 wide aspect ratio, clean white paper background, sharp details"

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
        "inputs": prompt
    }
    
    res = requests.post(api_url, headers=headers, json=payload, timeout=40)
    
    if res.status_code == 200:
        return res.content, None
    elif res.status_code == 503:
        return None, "서버가 모델을 준비 중입니다(Cold Start). 약 15초 후 다시 눌러주세요."
    elif res.status_code == 401:
        return None, "인증 실패: Hugging Face 토큰 권한을 확인해주세요."
    else:
        return None, f"서버 응답 오류 ({res.status_code}): {res.text}"

if st.button("🎨 16:9 원화 생성 시작 🚀"):
    if not hf_token.strip():
        st.error("토큰을 입력해주세요.")
    elif not user_desc.strip():
        st.warning("설명을 입력해주세요.")
    else:
        status_box = st.empty()
        status_box.info("Hugging Face 정규 엔드포인트로 원화를 생성 중입니다...")
        try:
            prompt_en = build_art_prompt(user_desc)
            st.session_state["used_prompt"] = prompt_en
            
            img_bytes, err = request_hf_image(prompt_en, hf_token, model_name)
            
            if img_bytes:
                img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
                st.session_state["base_image"] = img
                st.session_state["img_bytes"] = img_bytes
                status_box.success(f"원화 생성 완료! ({img.size[0]}x{img.size[1]})")
            else:
                status_box.error(err)
        except requests.exceptions.Timeout:
            status_box.error("서버 응답 시간 초과. 잠시 후 다시 시도해주세요.")
        except Exception as e:
            status_box.error(f"통신 오류: {e}")

if "base_image" in st.session_state:
    st.divider()
    st.caption(f"🔍 **적용된 영문 프롬프트:** `{st.session_state.get('used_prompt', '')}`")
    base_img = st.session_state["base_image"]
    st.image(base_img, caption="생성된 원화", use_container_width=True)
    
    st.download_button(
        label="📥 고화질 원화 다운로드 (PNG)",
        data=st.session_state["img_bytes"],
        file_name="mireuk_scene.png",
        mime="image/png"
    )
