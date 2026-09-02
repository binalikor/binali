import io
import os
import tempfile
import time
import urllib.parse
import cv2
import numpy as np
from PIL import Image
import requests
import streamlit as st

st.set_page_config(page_title="HuggingFace 16:9 애니메이션 스튜디오", layout="wide")
st.title("🎬 16:9 정규 애니메이션 원화 & 모션 스튜디오")
st.write("Hugging Face SDXL 엔진을 연동하여 1:1 늘림 없는 진짜 16:9 규격으로 원화를 렌더링합니다.")

# 사이드바: Hugging Face API 토큰 설정
with st.sidebar:
    st.header("🔑 Hugging Face 인증 설정")
    default_token = "HFAKSvPAybq4fZRqpzhhbCeuO3LW4OL"
    hf_token = st.text_input(
        "Hugging Face Access Token",
        value=default_token,
        type="password",
        help="hf_ 로 시작하는 Read 권한 토큰을 입력하세요."
    )
    # 모델 선택: SDXL 기반 애니메이션/일러스트 특화
    model_id = st.selectbox(
        "사용할 SDXL 모델",
        [
            "stabilityai/stable-diffusion-xl-base-1.0",
            "animagine-xl-3.1"
        ],
        index=0
    )

# 1. 장면 묘사 입력 영역
st.subheader("1. 장면 묘사 및 프롬프트 최적화")

user_desc = st.text_area(
    "장면 설명 (한국어)",
    value="한국 전래동화 이야기책 스타일 삽화. 거대한 신 미륵의 전신 모습. 얼굴 턱까지 덮는 큰 짚 고깔모자를 쓰고, 칡넝쿨로 짠 갈색 원시 옷을 입고 있다. 흙빛 피부에 눈빛은 따뜻하다. 부드러운 먹선과 수채화 채색, 동화책 삽화 스타일, 흰색 배경",
    height=100
)

# 번역 및 한국 설화 프롬프트 구조화 함수
def build_korean_folktale_prompt(text):
    if not text.strip():
        return ""
    
    # 미륵 및 한국 고유 요소 명시적 영문화 보정
    replaced = text.replace("미륵", "giant Korean mythical creator god Mireuk")
    
    url = "https://translate.googleapis.com/translate_a/single"
    params = {"client": "gtx", "sl": "ko", "tl": "en", "dt": "t", "q": replaced}
    base_en = replaced
    try:
        r = requests.get(url, params=params, timeout=5)
        if r.status_code == 200:
            pieces = [item[0] for item in r.json()[0] if item[0]]
            base_en = "".join(pieces).strip()
    except Exception:
        pass

    # 16:9 구도와 전래동화 수채화 질감을 강제하는 품질 태그
    style_boost = "storybook illustration style, soft sumi-e ink linework, gentle watercolor textures, cinematic 16:9 composition, wide angle, masterpiece, sharp details"
    return f"{base_en}, {style_boost}"

# Hugging Face API 호출 함수 (콜드 스타트 자동 재시도 포함)
def query_huggingface(prompt, token, model_name, max_retries=3):
    api_url = f"https://api-inference.huggingface.co/models/{model_name}"
    headers = {"Authorization": f"Bearer {token.strip()}"}
    
    # SDXL 16:9 정규 해상도 (1152 x 648)
    payload = {
        "inputs": prompt,
        "parameters": {
            "width": 1152,
            "height": 648,
            "negative_prompt": "blurry, deformed, cropped, ugly, extra limbs, stretched, 1:1 aspect ratio, modern clothing, photo, 3d render"
        }
    }

    for attempt in range(max_retries):
        response = requests.post(api_url, headers=headers, json=payload, timeout=60)
        
        if response.status_code == 200:
            return response.content, None
        
        # 모델 로딩 중 (Cold Start 503) 발생 시 대기 후 재시도
        elif response.status_code == 503:
            wait_time = 15
            try:
                err_data = response.json()
                wait_time = int(err_data.get("estimated_time", 15))
            except Exception:
                pass
            st.info(f"⏳ 서버가 모델을 로딩 중입니다. {wait_time}초 후 자동으로 재시도합니다... (시도 {attempt+1}/{max_retries})")
            time.sleep(wait_time)
        else:
            return None, f"오류 코드 {response.status_code}: {response.text}"
            
    return None, "서버 대기 시간 초과. 잠시 후 다시 시도해 주세요."

# 2. 이미지 생성 버튼
if st.button("🎨 16:9 네이티브 원화 생성 시작 🚀"):
    if not hf_token.strip():
        st.error("사이드바에 Hugging Face 토큰을 입력해주세요!")
    elif not user_desc.strip():
        st.warning("장면 설명을 입력해주세요!")
    else:
        with st.spinner("한국 설화 묘사를 16:9 와이드 화폭으로 렌더링 중입니다..."):
            en_prompt = build_korean_folktale_prompt(user_desc)
            st.session_state["used_prompt"] = en_prompt
            
            # 실제 모델 이름 매핑
            target_model = "stabilityai/stable-diffusion-xl-base-1.0"
            if model_id == "animagine-xl-3.1":
                target_model = "cagliostrolab/animagine-xl-3.1"
                
            img_bytes, err = query_huggingface(en_prompt, hf_token, target_model)
            
            if img_bytes:
                img = Image.open(io.BytesIO(img_bytes))
                st.session_state["base_image"] = img
                st.session_state["image_bytes"] = img_bytes
                st.success(f"원화 생성 성공! (실제 규격: {img.size[0]} x {img.size[1]} - 16:9 왜곡 없음)")
            else:
                st.error(f"생성 실패: {err}")

# 3. 결과 확인 및 16:9 비디오 렌더링
if "base_image" in st.session_state:
    st.divider()
    st.caption(f"🔍 **전송된 최적화 프롬프트:** `{st.session_state.get('used_prompt', '')}`")
    base_img = st.session_state["base_image"]
    st.image(base_img, use_container_width=True)

    st.subheader("2. 16:9 애니메이션 모션 비디오 렌더링")
    col1, col2 = st.columns(2)
    with col1:
        motion_type = st.selectbox("카메라 연출 기법", ["천천히 줌인 (Slow Zoom In)", "좌->우 패닝 (Pan Right)"])
    with col2:
        duration = st.slider("영상 길이(초)", min_value=2, max_value=6, value=4)

    def render_16_9_motion(pil_img, out_path, mode, duration_sec):
        img_np = np.array(pil_img)
        if len(img_np.shape) == 2:
            img_np = cv2.cvtColor(img_np, cv2.COLOR_GRAY2BGR)
        elif img_np.shape[2] == 4:
            img_np = cv2.cvtColor(img_np, cv2.COLOR_RGBA2BGR)
        else:
            img_np = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)

        h, w, _ = img_np.shape
        fps = 30
        total_frames = fps * duration_sec
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(out_path, fourcc, fps, (w, h))

        for i in range(total_frames):
            ratio = i / total_frames
            if "Slow Zoom In" in mode:
                scale = 1.0 + 0.16 * ratio
                crop_w, crop_h = int(w / scale), int(h / scale)
                x1, y1 = (w - crop_w) // 2, (h - crop_h) // 2
            else:
                scale = 1.1
                crop_w, crop_h = int(w / scale), int(h / scale)
                y1 = (h - crop_h) // 2
                x1 = int((w - crop_w) * ratio)

            x2, y2 = min(w, x1 + crop_w), min(h, y1 + crop_h)
            cropped = img_np[y1:y2, x1:x2]
            frame = cv2.resize(cropped, (w, h), interpolation=cv2.INTER_LINEAR)
            out.write(frame)

        out.release()

    if st.button("🎬 16:9 모션 비디오(MP4) 렌더링"):
        with st.spinner("16:9 비디오 프레임을 합성 중입니다..."):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_file:
                target_video = tmp_file.name

            render_16_9_motion(base_img, target_video, motion_type, duration)

            with open(target_video, "rb") as f:
                v_bytes = f.read()

            st.video(v_bytes)
            st.download_button(
                label="📥 16:9 애니메이션 비디오 다운로드",
                data=v_bytes,
                file_name="folktale_16_9.mp4",
                mime="video/mp4"
            )

            if os.path.exists(target_video):
                os.remove(target_video)
