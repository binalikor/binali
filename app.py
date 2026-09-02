import io
import os
import tempfile
import urllib.parse
import cv2
import numpy as np
from PIL import Image
import requests
import streamlit as st

st.set_page_config(page_title="애니메이션 AI 영상 스튜디오", layout="centered")
st.title("🎬 애니메이션 & 삽화 전문 AI 영상 스튜디오")
st.write("애니메이션 제작에 특화된 화풍 프리셋과 자동 한글 번역으로 영상 소스를 생성합니다.")

# 안정적인 경량 웹 번역 함수
def safe_translate_ko_to_en(text):
    if not text.strip():
        return ""
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

# 애니메이션/삽화 전용 화풍 프리셋 정의
STYLE_TAGS = {
    "🌿 서정적 판타지 애니 (지브리풍)": "Studio Ghibli style, hand-drawn anime aesthetic, lush watercolor scenery, warm natural light, painted background, nostalgic atmosphere, masterpiece",
    "✨ 빛 연출 극장판 애니 (신카이 마코토풍)": "Makoto Shinkai style, CoMix Wave Films aesthetic, dramatic lens flare, highly detailed sky and clouds, vibrant colors, cinematic anime movie still",
    "📺 90년대 레트로 셀 애니메이션": "1990s anime screenshot, retro cel animation style, slightly softened lines, classic anime grain, nostalgic color palette",
    "🎨 동화책 일러스트 (수채화 삽화)": "children book illustration, soft watercolor texture, storybook art style, whimsical, gentle pastel tones, detailed artistic illustration",
    "📖 판타지 소설/동양풍 정밀 삽화": "detailed digital painting, light novel illustration, fantasy concept art, delicate linework, rich textures, atmospheric lighting",
    "🖌️ 다크 판타지 수묵화/먹화풍": "Japanese ink wash painting style, sumi-e aesthetic, dramatic brush strokes, dynamic contrast, anime ink art",
    "💥 일본 주간 만화 원고 (흑백 스케치)": "black and white manga panel, highly detailed ink linework, screentone shading, dynamic composition, graphic novel illustration",
    "🧸 3D 극장용 애니 (픽사/디즈니풍)": "Pixar Disney 3D animation style, expressive character, vibrant subsurface scattering, soft volumetric lighting, 3D render",
    "⚙️ 스타일 태그 없음 (직접 작성)": ""
}

# 1. 프롬프트 입력 영역
st.subheader("1. 씬(Scene) 구상 및 화풍 선택")

col_ko, col_style = st.columns([1.8, 1.2])
with col_ko:
    ko_input = st.text_area(
        "장면 설명 (한국어)",
        value="언덕 위 거대한 신목 아래에서 하늘을 올려다보는 소년, 바람에 흔들리는 풀밭",
        height=100
    )
with col_style:
    style_choice = st.selectbox(
        "애니메이션 화풍 선택",
        list(STYLE_TAGS.keys())
    )

if "final_en_prompt" not in st.session_state:
    st.session_state["final_en_prompt"] = ""

if st.button("🌐 번역 및 애니메이션 프롬프트 조합"):
    translated = safe_translate_ko_to_en(ko_input)
    style_suffix = STYLE_TAGS[style_choice]
    st.session_state["final_en_prompt"] = f"{translated}, {style_suffix}".strip(", ")

final_prompt = st.text_area(
    "AI 엔진 전달용 영문 프롬프트 (수정 가능)",
    value=st.session_state["final_en_prompt"],
    height=80
)

# 2. 이미지 생성
if st.button("🎨 애니메이션 컷 생성 시작 🚀"):
    prompt_to_use = final_prompt.strip()
    if not prompt_to_use:
        translated = safe_translate_ko_to_en(ko_input)
        style_suffix = STYLE_TAGS[style_choice]
        prompt_to_use = f"{translated}, {style_suffix}".strip(", ")
        st.session_state["final_en_prompt"] = prompt_to_use

    with st.spinner("애니메이션 원화를 생성 중입니다..."):
        try:
            encoded = urllib.parse.quote(prompt_to_use)
            image_url = f"https://image.pollinations.ai/prompt/{encoded}?width=1024&height=1024&nologo=true&model=flux"
            res = requests.get(image_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=60)

            if res.status_code == 200:
                img_data = res.content
                st.session_state["base_image"] = Image.open(io.BytesIO(img_data))
                st.session_state["image_bytes"] = img_data
                st.success("원화 생성 완료!")
            else:
                st.error("서버 연결 실패")
        except Exception as e:
            st.error(f"오류: {e}")

# 3. 비디오 렌더링
if "base_image" in st.session_state:
    st.divider()
    base_img = st.session_state["base_image"]
    st.image(base_img, use_container_width=True)

    st.subheader("2. 애니메이션 카메라 워크 (모션 영상)")
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        motion_type = st.selectbox(
            "카메라 연출 기법",
            [
                "천천히 줌인 (Slow Zoom In) - 감정 집중",
                "배경 패닝 좌->우 (Pan Right) - 공간 조망",
                "배경 패닝 우->좌 (Pan Left) - 공간 조망",
                "빠른 돌진 (Dynamic Push In) - 긴박한 씬"
            ]
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

            if "Slow Zoom In" in mode:
                scale = 1.0 + 0.22 * ratio
                crop_w, crop_h = int(w / scale), int(h / scale)
                x1, y1 = (w - crop_w) // 2, (h - crop_h) // 2

            elif "Dynamic Push In" in mode:
                scale = 1.0 + 0.45 * (ratio ** 1.5)
                crop_w, crop_h = int(w / scale), int(h / scale)
                x1, y1 = (w - crop_w) // 2, (h - crop_h) // 2

            elif "Pan Right" in mode:
                scale = 1.15
                crop_w, crop_h = int(w / scale), int(h / scale)
                y1 = (h - crop_h) // 2
                x1 = int((w - crop_w) * ratio)

            elif "Pan Left" in mode:
                scale = 1.15
                crop_w, crop_h = int(w / scale), int(h / scale)
                y1 = (h - crop_h) // 2
                x1 = int((w - crop_w) * (1.0 - ratio))

            x2, y2 = min(w, x1 + crop_w), min(h, y1 + crop_h)
            cropped = img_np[y1:y2, x1:x2]
            frame = cv2.resize(cropped, (w, h), interpolation=cv2.INTER_LINEAR)
            out.write(frame)

        out.release()

    if st.button("🎬 애니메이션 모션 컷(MP4) 렌더링"):
        with st.spinner("카메라 워크를 적용 중입니다..."):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_file:
                target_video = tmp_file.name

            render_motion(base_img, target_video, motion_type, duration)

            with open(target_video, "rb") as f:
                v_bytes = f.read()

            st.video(v_bytes)
            st.download_button(
                label="📥 애니메이션 비디오(MP4) 저장",
                data=v_bytes,
                file_name="anime_scene.mp4",
                mime="video/mp4"
            )

            if os.path.exists(target_video):
                os.remove(target_video)
