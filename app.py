import io
import os
import tempfile
import cv2
import numpy as np
from PIL import Image
import requests
import streamlit as st

st.set_page_config(page_title="무료 AI 모션 스튜디오", layout="centered")
st.title("🎨 무료 AI 이미지 & 모션 비디오 생성기")
st.write("비용 없이 무료 오픈소스 AI(FLUX / SDXL)로 그림을 그리고 줌인 영상으로 변환합니다.")

# 1. Hugging Face 무료 토큰 입력
hf_token = st.sidebar.text_input(
    "Hugging Face 토큰 (hf_...)", 
    type="password",
    help="huggingface.co/settings/tokens 에서 무료로 발급받을 수 있습니다."
)

prompt = st.text_area(
    "그림 설명 (영어로 자세히 적을수록 멋지게 나옵니다)",
    placeholder="A cute cyberpunk kitten with glowing eyes in a neon city, highly detailed 3d render"
)

# 2. 줌인 모션 비디오 생성 함수
def create_zoom_video(pil_image, output_path, fps=30, duration_sec=3, max_zoom=1.25):
    img_np = np.array(pil_image)
    if len(img_np.shape) == 2:
        img_np = cv2.cvtColor(img_np, cv2.COLOR_GRAY2BGR)
    elif img_np.shape[2] == 4:
        img_np = cv2.cvtColor(img_np, cv2.COLOR_RGBA2BGR)
    else:
        img_np = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)

    h, w, _ = img_np.shape
    total_frames = fps * duration_sec
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (w, h))

    center_x, center_y = w // 2, h // 2

    for i in range(total_frames):
        scale = 1.0 + (max_zoom - 1.0) * (i / total_frames)
        crop_w = int(w / scale)
        crop_h = int(h / scale)

        x1 = max(0, center_x - crop_w // 2)
        y1 = max(0, center_y - crop_h // 2)
        x2 = min(w, x1 + crop_w)
        y2 = min(h, y1 + crop_h)

        cropped = img_np[y1:y2, x1:x2]
        frame = cv2.resize(cropped, (w, h), interpolation=cv2.INTER_LINEAR)
        out.write(frame)

    out.release()

# 3. 이미지 생성 버튼 클릭 시 동작
if st.button("무료 이미지 생성 시작 🚀"):
    if not hf_token:
        st.error("왼쪽 사이드바에 Hugging Face 무료 토큰(hf_...)을 먼저 입력해주세요.")
    elif not prompt:
        st.warning("그림 설명을 입력해주세요.")
    else:
        with st.spinner("무료 AI 서버에서 그림을 생성하고 있습니다 (약 5~15초 소요)..."):
            try:
                # 고성능 무료 오픈소스 모델 엔드포인트
                API_URL = "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-schnell"
                headers = {"Authorization": f"Bearer {hf_token.strip()}"}
                payload = {"inputs": prompt}

                response = requests.post(API_URL, headers=headers, json=payload, timeout=60)

                # 혹시 모델이 로딩 중인 경우 대비 (fallback)
                if response.status_code != 200:
                    API_URL_BACKUP = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"
                    response = requests.post(API_URL_BACKUP, headers=headers, json=payload, timeout=60)

                if response.status_code == 200:
                    img_data = response.content
                    image = Image.open(io.BytesIO(img_data))

                    st.session_state["image_bytes"] = img_data
                    st.session_state["generated_image"] = image
                else:
                    st.error(f"오류가 발생했습니다 (코드 {response.status_code}): {response.text}")

            except Exception as e:
                st.error(f"실행 중 예외 발생: {e}")

# 생성된 이미지 및 비디오 렌더링 영역
if "generated_image" in st.session_state:
    st.divider()
    st.subheader("1. 완성된 무료 AI 그림")
    img = st.session_state["generated_image"]
    st.image(img, use_container_width=True)

    st.download_button(
        label="💾 이미지(PNG) 다운로드",
        data=st.session_state["image_bytes"],
        file_name="free_ai_art.png",
        mime="image/png"
    )

    st.divider()
    st.subheader("2. 모션 비디오 변환")
    if st.button("🎬 모션 비디오(MP4) 렌더링"):
        with st.spinner("영상 프레임을 합성 중입니다..."):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_file:
                video_path = tmp_file.name

            create_zoom_video(img, video_path, fps=30, duration_sec=3, max_zoom=1.2)

            with open(video_path, "rb") as f:
                video_bytes = f.read()

            st.video(video_bytes)

            st.download_button(
                label="📥 모션 비디오(MP4) 저장",
                data=video_bytes,
                file_name="motion_video.mp4",
                mime="video/mp4"
            )

            if os.path.exists(video_path):
                os.remove(video_path)
