import io
import os
import tempfile
import urllib.parse
import cv2
import numpy as np
from PIL import Image
import requests
import streamlit as st

st.set_page_config(page_title="AI 영상 제작 스튜디오", layout="centered")
st.title("🎬 AI 비디오 & 모션 연출 스튜디오")
st.write("이미지를 먼저 만들고, 원하는 카메라 무빙 및 영상 텍스트 지시어를 설정해 MP4 영상을 제작합니다.")

# 1. 원본 이미지 생성용 프롬프트
img_prompt = st.text_area(
    "1. 기준 이미지 설명 (영어로 자세히 입력)",
    value="A futuristic cybernetic tiger resting in a neon Tokyo alley, rainy street, reflections, cinematic lighting",
    height=80
)

# 1단계: 기준 이미지 무료 생성
if st.button("1단계: 기준 이미지 먼저 생성하기 🎨"):
    if not img_prompt:
        st.warning("그림 설명을 입력해주세요!")
    else:
        with st.spinner("AI가 기준 이미지를 생성 중입니다..."):
            try:
                encoded_prompt = urllib.parse.quote(img_prompt.strip())
                image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true&model=flux"
                
                headers = {"User-Agent": "Mozilla/5.0"}
                res = requests.get(image_url, headers=headers, timeout=60)
                if res.status_code == 200:
                    img_data = res.content
                    st.session_state["base_image"] = Image.open(io.BytesIO(img_data))
                    st.session_state["image_bytes"] = img_data
                    st.success("기준 이미지 완성!")
                else:
                    st.error("이미지 서버 연결 실패")
            except Exception as e:
                st.error(f"오류: {e}")

# 2단계: 영상 연출 지시어 및 렌더링 영역
if "base_image" in st.session_state:
    st.divider()
    st.subheader("1. 생성된 기준 이미지")
    base_img = st.session_state["base_image"]
    st.image(base_img, use_container_width=True)

    st.divider()
    st.subheader("2. 영상 제작을 위한 연출 텍스트 설정")
    st.write("카메라 움직임과 영상 분위기를 텍스트 지시어로 제어합니다.")

    # 영상 연출 텍스트 입력창
    video_motion_prompt = st.text_area(
        "영상 연출/무빙 지시어 (Prompt for Video Motion)",
        placeholder="예: Slow cinematic pan left to right, neon lights blinking, smooth camera drift",
        value="Cinematic slow forward zoom-in, smooth motion, high visual depth"
    )

    # 연출 프리셋 선택
    motion_type = st.selectbox(
        "카메라 무빙 스타일 (위 텍스트 지시어와 연동)",
        ["천천히 줌인 (Slow Zoom In)", "빠른 돌진 (Dynamic Push In)", "오른쪽으로 패닝 (Pan Right)", "왼쪽으로 패닝 (Pan Left)"]
    )

    duration = st.slider("영상 길이(초)", min_value=2, max_value=5, value=3)

    # 영상 렌더링 함수
    def render_motion(pil_img, out_path, mode, duration_sec):
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

            if mode == "천천히 줌인 (Slow Zoom In)":
                scale = 1.0 + 0.25 * ratio
                crop_w, crop_h = int(w / scale), int(h / scale)
                x1, y1 = (w - crop_w) // 2, (h - crop_h) // 2

            elif mode == "빠른 돌진 (Dynamic Push In)":
                scale = 1.0 + 0.5 * (ratio ** 1.5)
                crop_w, crop_h = int(w / scale), int(h / scale)
                x1, y1 = (w - crop_w) // 2, (h - crop_h) // 2

            elif mode == "오른쪽으로 패닝 (Pan Right)":
                scale = 1.15
                crop_w, crop_h = int(w / scale), int(h / scale)
                y1 = (h - crop_h) // 2
                max_shift = w - crop_w
                x1 = int(max_shift * ratio)

            elif mode == "왼쪽으로 패닝 (Pan Left)":
                scale = 1.15
                crop_w, crop_h = int(w / scale), int(h / scale)
                y1 = (h - crop_h) // 2
                max_shift = w - crop_w
                x1 = int(max_shift * (1.0 - ratio))

            x2, y2 = min(w, x1 + crop_w), min(h, y1 + crop_h)
            cropped = img_np[y1:y2, x1:x2]
            frame = cv2.resize(cropped, (w, h), interpolation=cv2.INTER_LINEAR)
            out.write(frame)

        out.release()

    # 영상 제작 실행 버튼
    if st.button("🎬 지시어 반영하여 비디오(MP4) 렌더링"):
        with st.spinner(f"입력한 지시어({motion_type})를 바탕으로 비디오 프레임을 연산 중입니다..."):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_file:
                target_video = tmp_file.name

            render_motion(base_img, target_video, motion_type, duration)

            with open(target_video, "rb") as f:
                v_bytes = f.read()

            st.video(v_bytes)
            st.download_button(
                label="📥 렌더링된 MP4 비디오 다운로드",
                data=v_bytes,
                file_name="ai_video.mp4",
                mime="video/mp4"
            )

            if os.path.exists(target_video):
                os.remove(target_video)
