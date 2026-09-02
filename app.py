import io
import os
import tempfile
import cv2
import numpy as np
from PIL import Image
import requests
import streamlit as st
from openai import OpenAI

st.set_page_config(page_title="AI 모션 스튜디오", layout="centered")
st.title("🎨 AI 이미지 & 모션 비디오 생성기")
st.write("그림을 생성하고 카메라가 줌인되는 3초 모션 영상(MP4)으로 바꿉니다.")

# 1. 사이드바 API 키 입력
api_key = st.sidebar.text_input("OpenAI API 키 입력", type="password")
prompt = st.text_area(
    "그림 설명 (영어로 적으면 더 정교합니다)",
    placeholder="A futuristic cybernetic cat in neon city, highly detailed, 3d render"
)

# 2. 무료 줌인 모션 연산 함수
def create_zoom_video(pil_image, output_path, fps=30, duration_sec=3, max_zoom=1.25):
    img_np = np.array(pil_image)
    if img_np.shape[2] == 4:
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

# 3. 이미지 생성 버튼 동작
if st.button("이미지 생성 시작 🚀"):
    if not api_key:
        st.error("왼쪽 사이드바에 OpenAI API 키를 먼저 입력해주세요.")
    elif not prompt:
        st.warning("그림 설명을 입력해주세요.")
    else:
        with st.spinner("AI가 그림을 그리는 중입니다..."):
            try:
                client = OpenAI(api_key=api_key)
                response = client.images.generate(
                    model="dall-e-3",
                    prompt=prompt,
                    size="1024x1024",
                    quality="standard",
                    n=1,
                )
                image_url = response.data[0].url
                img_data = requests.get(image_url).content

                st.session_state["image_bytes"] = img_data
                st.session_state["generated_image"] = Image.open(io.BytesIO(img_data))
                st.session_state["prompt_used"] = prompt
            except Exception as e:
                st.error(f"오류 발생: {e}")

# 이미지가 생성된 후 노출되는 영역
if "generated_image" in st.session_state:
    st.divider()
    st.subheader("1. 완성된 그림")
    img = st.session_state["generated_image"]
    st.image(img, use_container_width=True)

    st.download_button(
        label="💾 이미지(PNG) 다운로드",
        data=st.session_state["image_bytes"],
        file_name="ai_art.png",
        mime="image/png"
    )

    st.divider()
    st.subheader("2. 모션 비디오 변환")
    if st.button("🎬 모션 비디오(MP4) 렌더링"):
        with st.spinner("서버에서 부드러운 줌 영상을 제작 중입니다..."):
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
