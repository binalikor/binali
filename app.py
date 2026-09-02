import io
import os
import tempfile
import urllib.parse
from PIL import Image
import imageio
import numpy as np
import requests
import streamlit as st

st.set_page_config(page_title="16:9 한국 설화 애니메이션 스튜디오", layout="wide")
st.title("🎬 16:9 애니메이션 원화 & 모션 스튜디오")
st.caption("가벼운 엔진으로 메모리 충돌 없이 16:9 규격 원화와 모션 컷을 생성합니다.")

# 사이드바 설정
DEFAULT_HF_TOKEN = "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"

with st.sidebar:
    st.header("🔑 API 설정")
    hf_token = st.text_input("Hugging Face Token", value=DEFAULT_HF_TOKEN, type="password")
    model_choice = st.selectbox(
        "사용 모델",
        ["stabilityai/sdxl-turbo", "ByteDance/SDXL-Lightning"]
    )

st.subheader("1. 장면 묘사 입력")
user_desc = st.text_area(
    "장면 설명 (한국어)",
    value="한국 전래동화 이야기책 스타일 삽화. 거대한 신 미륵의 전신 모습. 얼굴 턱까지 덮는 큰 짚 고깔모자를 쓰고, 칡넝쿨로 짠 갈색 원시 옷을 입고 있다. 흙빛 피부에 눈빛은 따뜻하다. 부드러운 먹선과 수채화 채색, 동화책 삽화 스타일, 흰색 배경",
    height=100
)

# 번역 및 프롬프트 생성
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

# 원화 생성 실행
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
                status_box.success(f"원화 생성 성공! ({img.size[0]}x{img.size[1]})")
            else:
                status_box.error(err)
        except Exception as e:
            status_box.error(f"오류: {e}")

# 16:9 모션 비디오 렌더링 (OpenCV 제거 -> imageio 경량 처리)
if "base_image" in st.session_state:
    st.divider()
    base_img = st.session_state["base_image"]
    st.image(base_img, use_container_width=True)

    st.subheader("2. 16:9 애니메이션 모션 비디오")
    col1, col2 = st.columns(2)
    with col1:
        motion_type = st.selectbox("카메라 연출", ["천천히 줌인 (Slow Zoom In)", "좌->우 패닝 (Pan Right)"])
    with col2:
        duration = st.slider("영상 길이(초)", min_value=2, max_value=5, value=3)

    def render_lightweight_video(pil_img, out_path, mode, sec):
        w, h = pil_img.size
        fps = 24
        total_frames = fps * sec
        frames = []

        for i in range(total_frames):
            ratio = i / total_frames
            if "Slow Zoom In" in mode:
                scale = 1.0 + 0.15 * ratio
                cw, ch = int(w / scale), int(h / scale)
                x1, y1 = (w - cw) // 2, (h - ch) // 2
            else:
                scale = 1.12
                cw, ch = int(w / scale), int(h / scale)
                y1 = (h - ch) // 2
                x1 = int((w - cw) * ratio)

            cropped = pil_img.crop((x1, y1, x1 + cw, y1 + ch))
            resized = cropped.resize((w, h), Image.Resampling.BILINEAR)
            frames.append(np.array(resized))

        imageio.mimwrite(out_path, frames, fps=fps, codec="libx264")

    if st.button("🎬 16:9 모션 비디오 생성"):
        with st.spinner("비디오 렌더링 중..."):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
                out_video = tmp.name
            
            render_lightweight_video(base_img, out_video, motion_type, duration)

            with open(out_video, "rb") as f:
                v_bytes = f.read()

            st.video(v_bytes)
            st.download_button("📥 비디오(MP4) 다운로드", data=v_bytes, file_name="scene.mp4", mime="video/mp4")
            if os.path.exists(out_video):
                os.remove(out_video)
