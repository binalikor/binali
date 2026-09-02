import io
import os
import tempfile
import urllib.parse
import cv2
import numpy as np
from PIL import Image
import requests
import streamlit as st

st.set_page_config(page_title="AI 영상 스튜디오", layout="centered")
st.title("🎬 안정적인 한글 지원 AI 이미지 & 모션 스튜디오")
st.write("한국어로 자유롭게 입력하면 안정적인 번역 엔진이 고품질 영문 프롬프트로 변환하여 생성합니다.")

# 안정적인 경량 웹 번역 함수 (외부 라이브러리 의존성 없음)
def safe_translate_ko_to_en(text):
    if not text.strip():
        return ""
    # 영문 위주 입력 시 그대로 반환
    if all(ord(char) < 128 for char in text.replace(" ", "")):
        return text.strip()
    
    url = "https://translate.googleapis.com/translate_a/single"
    params = {
        "client": "gtx",
        "sl": "ko",
        "tl": "en",
        "dt": "t",
        "q": text
    }
    try:
        res = requests.get(url, params=params, timeout=5)
        if res.status_code == 200:
            data = res.json()
            translated_pieces = [item[0] for item in data[0] if item[0]]
            return "".join(translated_pieces).strip()
    except Exception:
        pass
    return text.strip()

# 1. 사용자 프롬프트 입력 영역
st.subheader("1. 그림 설명 입력")

col_ko, col_style = st.columns([2, 1])
with col_ko:
    ko_input = st.text_area(
        "한국어 설명",
        value="대지를 닮은 거대한 창조신. 무표정하고 과묵하지만 정직한 거인.",
        height=90
    )
with col_style:
    style_choice = st.selectbox(
        "화풍 선택",
        [
            "극실사/영화적 (Cinematic Photorealistic)",
            "3D 애니메이션 (Pixar Style)",
            "판타지 컨셉 아트 (Epic Fantasy)",
            "사이버펑크 네온 (Cyberpunk)",
            "스타일 추가 없음 (Raw)"
        ]
    )

STYLE_TAGS = {
    "극실사/영화적 (Cinematic Photorealistic)": "photorealistic, 8k resolution, cinematic lighting, hyperrealistic, detailed texture",
    "3D 애니메이션 (Pixar Style)": "3D render, Pixar style, vivid lighting, detailed 3D assets",
    "판타지 컨셉 아트 (Epic Fantasy)": "epic fantasy concept art, atmospheric lighting, ultra-detailed scenery, mythical",
    "사이버펑크 네온 (Cyberpunk)": "cyberpunk style, glowing neon reflections, futuristic night lighting",
    "스타일 추가 없음 (Raw)": ""
}

# 세션 상태 초기화
if "final_en_prompt" not in st.session_state:
    st.session_state["final_en_prompt"] = ""

# 번역 버튼
if st.button("🌐 한국어 ➜ 영어 프롬프트 변환 및 확인"):
    translated = safe_translate_ko_to_en(ko_input)
    style_suffix = STYLE_TAGS[style_choice]
    st.session_state["final_en_prompt"] = f"{translated}, {style_suffix}".strip(", ")

# 최종 전송 영문 프롬프트 (수정 가능)
final_prompt = st.text_area(
    "AI에 전달될 최종 영어 프롬프트 (직접 수정 가능)",
    value=st.session_state["final_en_prompt"],
    height=80
)

# 2. 이미지 생성
if st.button("🎨 이미지 생성 시작 🚀"):
    prompt_to_use = final_prompt.strip()
    if not prompt_to_use:
        # 번역 버튼을 누르지 않고 바로 생성을 눌렀을 경우 자동 번역 실행
        translated = safe_translate_ko_to_en(ko_input)
        style_suffix = STYLE_TAGS[style_choice]
        prompt_to_use = f"{translated}, {style_suffix}".strip(", ")
        st.session_state["final_en_prompt"] = prompt_to_use

    with st.spinner("AI 엔진에서 이미지를 렌더링 중입니다..."):
        try:
            encoded = urllib.parse.quote(prompt_to_use)
            image_url = f"https://image.pollinations.ai/prompt/{encoded}?width=1024&height=1024&nologo=true&model=flux"
            res = requests.get(image_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=60)

            if res.status_code == 200:
                img_data = res.content
                st.session_state["base_image"] = Image.open(io.BytesIO(img_data))
                st.session_state["image_bytes"] = img_data
                st.success("이미지 생성 완료!")
            else:
                st.error("이미지 서버 통신 실패")
        except Exception as e:
            st.error(f"생성 중 에러: {e}")

# 3. 비디오 렌더링 영역
if "base_image" in st.session_state:
    st.divider()
    base_img = st.session_state["base_image"]
    st.image(base_img, use_container_width=True)

    st.subheader("2. 줌인 모션 비디오 렌더링")
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        motion_type = st.selectbox(
            "카메라 연출",
            ["천천히 줌인 (Slow Zoom In)", "빠른 돌진 (Dynamic Push In)", "오른쪽 패닝 (Pan Right)", "왼쪽 패닝 (Pan Left)"]
        )
    with col_m2:
        duration = st.slider("영상 길이(초)", min_value=2, max_value=6, value=4)

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

            elif mode == "오른쪽 패닝 (Pan Right)":
                scale = 1.15
                crop_w, crop_h = int(w / scale), int(h / scale)
                y1 = (h - crop_h) // 2
                x1 = int((w - crop_w) * ratio)

            elif mode == "왼쪽 패닝 (Pan Left)":
                scale = 1.15
                crop_w, crop_h = int(w / scale), int(h / scale)
                y1 = (h - crop_h) // 2
                x1 = int((w - crop_w) * (1.0 - ratio))

            x2, y2 = min(w, x1 + crop_w), min(h, y1 + crop_h)
            cropped = img_np[y1:y2, x1:x2]
            frame = cv2.resize(cropped, (w, h), interpolation=cv2.INTER_LINEAR)
            out.write(frame)

        out.release()

    if st.button("🎬 모션 비디오(MP4) 생성"):
        with st.spinner("모션 비디오를 생성 중입니다..."):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_file:
                target_video = tmp_file.name

            render_motion(base_img, target_video, motion_type, duration)

            with open(target_video, "rb") as f:
                v_bytes = f.read()

            st.video(v_bytes)
            st.download_button(
                label="📥 비디오(MP4) 다운로드",
                data=v_bytes,
                file_name="motion_video.mp4",
                mime="video/mp4"
            )

            if os.path.exists(target_video):
                os.remove(target_video)
