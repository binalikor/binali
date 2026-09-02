import io
import os
import tempfile
import urllib.parse
import cv2
import numpy as np
from PIL import Image
import requests
import streamlit as st

st.set_page_config(page_title="무료 AI 모션 스튜디오", layout="centered")
st.title("🎨 100% 무료 AI 이미지 & 모션 비디오 스튜디오")
st.write("가입이나 토큰 입력 없이 바로 고화질 AI 그림을 그리고 줌인 영상으로 변환합니다.")

# 프롬프트 입력
prompt = st.text_area(
    "그림 설명 (영어로 적으면 훨씬 퀄리티가 좋습니다)",
    value="A cute fluffy red panda wearing an astronaut helmet floating in space, colorful nebula background, 3D render, Pixar style",
    height=100
)

# 줌인 모션 비디오 연산 함수 (내 서버 자체 연산)
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

# 이미지 생성 버튼 동작
if st.button("무료 이미지 바로 생성 🚀"):
    if not prompt:
        st.warning("그림 설명을 먼저 입력해주세요!")
    else:
        with st.spinner("AI가 무료로 그림을 생성하고 있습니다 (약 5~10초 소요)..."):
            try:
                # 공용 무료 AI 엔드포인트 사용 (토큰/키 필요 없음)
                encoded_prompt = urllib.parse.quote(prompt.strip())
                image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true&model=flux"

                headers = {"User-Agent": "Mozilla/5.0"}
                response = requests.get(image_url, headers=headers, timeout=60)

                if response.status_code == 200:
                    img_data = response.content
                    image = Image.open(io.BytesIO(img_data))

                    st.session_state["image_bytes"] = img_data
                    st.session_state["generated_image"] = image
                    st.success("이미지 생성 성공!")
                else:
                    st.error(f"서버 응답 오류 (코드 {response.status_code})")

            except Exception as e:
                st.error(f"생성 중 오류 발생: {e}")

# 결과 화면
if "generated_image" in st.session_state:
    st.divider()
    st.subheader("1. 완성된 AI 그림")
    img = st.session_state["generated_image"]
    st.image(img, use_container_width=True)

    st.download_button(
        label="💾 이미지(PNG) 다운로드",
        data=st.session_state["image_bytes"],
        file_name="ai_image.png",
        mime="image/png"
    )

    st.divider()
    st.subheader("2. 줌인 애니메이션 영상 제작")
    if st.button("🎬 모션 비디오(MP4) 렌더링"):
        with st.spinner("서버에서 카메라 줌인 비디오를 합성 중입니다..."):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_file:
                video_path = tmp_file.name

            create_zoom_video(img, video_path, fps=30, duration_sec=3, max_zoom=1.2)

            with open(video_path, "rb") as f:
                video_bytes = f.read()

            st.video(video_bytes)

            st.download_button(
                label="📥 모션 비디오(MP4) 다운로드",
                data=video_bytes,
                file_name="motion_video.mp4",
                mime="video/mp4"
            )

            if os.path.exists(video_path):
                os.remove(video_path)
