import io
import os
import tempfile
import urllib.parse
import cv2
import numpy as np
from PIL import Image
import requests
import streamlit as st

st.set_page_config(page_title="애니메이션 만화 삽화 스튜디오", layout="centered")
st.title("🎨 만화 & 삽화 전문 AI 영상 스튜디오")
st.write("제작사 이름이 아닌 순수 미술/만화 기법(펜화, 웹툰, 수채화, 그래픽 노블 등)으로 화풍을 명확히 구현합니다.")

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

# 기법 중심의 정통 만화/삽화 화풍 정의
ILLUST_STYLES = {
    "✒️ 흑백 만화 펜화 (선화 & 스크린톤)": {
        "prefix": "pure black and white manga panel, traditional ink drawing, sharp G-pen lines, hatched crosshatching shading, screentone textures,",
        "suffix": ", monochrome, no colors, authentic manga page layout, graphic novel drawing"
    },
    "📱 컬러 웹툰 채색 (선명한 외곽선)": {
        "prefix": "digital webtoon illustration, vibrant cell shading, bold and clean black outlines, crisp dynamic anime lineart,",
        "suffix": ", modern Korean manhwa art style, cinematic lighting, vivid digital coloration"
    },
    "🎨 동화/소설 수채화 삽화 (손그림)": {
        "prefix": "storybook watercolor illustration, soft wet-on-wet paint texture, delicate graphite pencil outlines,",
        "suffix": ", pastel color wash, hand-painted on textured paper, artistic whimsical illustration"
    },
    "🦇 다크 그래픽 노블 (강렬한 음영)": {
        "prefix": "American graphic novel illustration, heavy chiaroscuro, high contrast bold ink shadows, dramatic comic book art,",
        "suffix": ", gritty pulp comic aesthetic, cinematic composition, bold ink strokes"
    },
    "🖌️ 고전 수묵 담채화 (먹선과 붓터치)": {
        "prefix": "traditional oriental brush painting, ink wash sumi-e illustration, expressive calligraphy brush strokes,",
        "suffix": ", soft colored ink washes, visible brush splatters, antique art paper texture"
    },
    "🖍️ 빈티지 크레용/색연필 동화 삽화": {
        "prefix": "vintage children's book illustration, colored pencil and wax crayon textures, rough sketched outlines,",
        "suffix": ", warm matte paper texture, naive folk art charm, nostalgic hand-drawn illustration"
    },
    "🖼️ 판타지 소설 표지화 (정밀 유채화)": {
        "prefix": "fantasy novel cover illustration, intricate digital oil painting, detailed rendered textures, rich brushwork,",
        "suffix": ", atmospheric painterly lighting, majestic concept art, detailed character art"
    },
    "✏️ 연필 스케치 / 크로키": {
        "prefix": "detailed graphite pencil sketch, rough charcoal croquis, crosshatching pencil shading, artistic drafting lines,",
        "suffix": ", monochrome sketchbook drawing, realistic paper grain, unfinished artistic aesthetic"
    }
}

st.subheader("1. 장면 설명 및 삽화 기법 선택")

col_ko, col_style = st.columns([1.7, 1.3])
with col_ko:
    ko_input = st.text_area(
        "장면 설명 (한국어)",
        value="대지를 닮은 거대한 창조신. 무표정하고 과묵하지만 정직한 거인.",
        height=95
    )
with col_style:
    style_choice = st.selectbox(
        "만화 / 삽화 기법 선택",
        list(ILLUST_STYLES.keys())
    )

if "final_en_prompt" not in st.session_state:
    st.session_state["final_en_prompt"] = ""

if st.button("🌐 번역 및 기법 프롬프트 조합"):
    translated = safe_translate_ko_to_en(ko_input)
    style_info = ILLUST_STYLES[style_choice]
    st.session_state["final_en_prompt"] = f"{style_info['prefix']} {translated} {style_info['suffix']}".strip()

final_prompt = st.text_area(
    "AI 엔진에 전달될 최종 영어 프롬프트 (수정 가능)",
    value=st.session_state["final_en_prompt"],
    height=85
)

# 2. 이미지 생성
if st.button("🎨 삽화/원화 생성 시작 🚀"):
    prompt_to_use = final_prompt.strip()
    if not prompt_to_use:
        translated = safe_translate_ko_to_en(ko_input)
        style_info = ILLUST_STYLES[style_choice]
        prompt_to_use = f"{style_info['prefix']} {translated} {style_info['suffix']}".strip()
        st.session_state["final_en_prompt"] = prompt_to_use

    with st.spinner("선택하신 만화/삽화 기법으로 원화를 그리는 중입니다..."):
        try:
            encoded = urllib.parse.quote(prompt_to_use)
            seed_val = np.random.randint(1, 999999)
            image_url = f"https://image.pollinations.ai/prompt/{encoded}?width=1024&height=1024&nologo=true&seed={seed_val}&model=flux"
            res = requests.get(image_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=60)

            if res.status_code == 200:
                img_data = res.content
                st.session_state["base_image"] = Image.open(io.BytesIO(img_data))
                st.session_state["image_bytes"] = img_data
                st.success("삽화 생성 완료!")
            else:
                st.error("이미지 서버 통신 실패")
        except Exception as e:
            st.error(f"생성 중 오류: {e}")

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

    if st.button("🎬 모션 컷(MP4) 렌더링"):
        with st.spinner("카메라 연출을 합성 중입니다..."):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_file:
                target_video = tmp_file.name

            render_motion(base_img, target_video, motion_type, duration)

            with open(target_video, "rb") as f:
                v_bytes = f.read()

            st.video(v_bytes)
            st.download_button(
                label="📥 렌더링된 비디오(MP4) 저장",
                data=v_bytes,
                file_name="animated_cut.mp4",
                mime="video/mp4"
            )

            if os.path.exists(target_video):
                os.remove(target_video)
