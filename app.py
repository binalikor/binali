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
st.write("화풍의 개성이 프롬프트 최우선 순위로 반영되어 뚜렷한 스타일 차이를 만듭니다.")

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

# 화풍의 키워드가 맨 앞으로 오도록 접두사(Prefix) 형태로 재설계
STYLE_CONFIG = {
    "🌿 지브리 수채화 애니": {
        "prefix": "Studio Ghibli aesthetic, anime hand-drawn watercolor painting, Hayao Miyazaki artwork, lush painted scenery,",
        "suffix": ", traditional animation background, gouache paint texture, warm nostalgic light, masterpiece, 2D anime"
    },
    "✨ 신카이 마코토 극장판": {
        "prefix": "Makoto Shinkai visual style, CoMix Wave Films cinematic anime movie, blinding lens flare, ultra detailed sky and clouds,",
        "suffix": ", hyper-saturated anime scenery, dramatic lighting, modern Japanese theatrical animation still"
    },
    "📺 90년대 고전 레트로 셀애니": {
        "prefix": "1990s retro anime screengrab, classic vintage cel animation, visible hand-drawn ink lines,",
        "suffix": ", retro anime aesthetic, VHS tape grain, 90s OVA anime still, muted vintage tones"
    },
    "🎨 포근한 동화책 수채화 삽화": {
        "prefix": "Children's storybook illustration, whimsical hand-painted watercolor art, soft pencil outlines,",
        "suffix": ", gentle pastel colors, storybook page drawing, charming fairy-tale aesthetic, traditional paper texture"
    },
    "📖 판타지 소설/라이트노벨 표지": {
        "prefix": "Japanese light novel cover illustration, high-end fantasy digital painting, delicate sharp anime lineart,",
        "suffix": ", dynamic rim lighting, intricate fantasy costume details, polished character concept art"
    },
    "🖌️ 다크 판타지 수묵화 (먹화풍)": {
        "prefix": "Traditional Japanese sumi-e ink wash painting, dynamic black ink anime art, bold fluid brush strokes,",
        "suffix": ", stark monochrome with blood red accents, dramatic ink splatter, wabi-sabi oriental fantasy aesthetic"
    },
    "💥 흑백 주간 만화 원고 (만화책)": {
        "prefix": "Black and white manga panel, manga ink drawing, sharp G-pen ink lines, detailed screentones,",
        "suffix": ", no colors, purely monochrome manga page, hatched shading, graphic novel print"
    },
    "🧸 3D 극장 애니메이션 (디즈니/픽사)": {
        "prefix": "Pixar Disney 3D animation character render, octane 3D render, smooth stylized textures,",
        "suffix": ", soft studio lighting, cute expressive design, clay render aesthetic, high-end CGI movie"
    }
}

st.subheader("1. 장면 구상 및 화풍 선택")

col_ko, col_style = st.columns([1.8, 1.2])
with col_ko:
    ko_input = st.text_area(
        "장면 설명 (한국어)",
        value="대지를 닮은 거대한 창조신. 무표정하고 과묵하지만 정직한 거인.",
        height=90
    )
with col_style:
    style_choice = st.selectbox(
        "애니메이션 화풍 선택",
        list(STYLE_CONFIG.keys())
    )

if "final_en_prompt" not in st.session_state:
    st.session_state["final_en_prompt"] = ""

if st.button("🌐 프롬프트 조합 (화풍 최우선 배치)"):
    translated = safe_translate_ko_to_en(ko_input)
    style_info = STYLE_CONFIG[style_choice]
    # 화풍 키워드를 문장 맨 앞에 강제 배치
    st.session_state["final_en_prompt"] = f"{style_info['prefix']} {translated} {style_info['suffix']}".strip()

final_prompt = st.text_area(
    "AI 엔진에 전송될 최종 프롬프트 (수정 가능)",
    value=st.session_state["final_en_prompt"],
    height=90
)

# 2. 이미지 생성
if st.button("🎨 애니메이션 컷 생성 시작 🚀"):
    prompt_to_use = final_prompt.strip()
    if not prompt_to_use:
        translated = safe_translate_ko_to_en(ko_input)
        style_info = STYLE_CONFIG[style_choice]
        prompt_to_use = f"{style_info['prefix']} {translated} {style_info['suffix']}".strip()
        st.session_state["final_en_prompt"] = prompt_to_use

    with st.spinner("선택한 화풍을 강하게 적용하여 원화를 렌더링 중입니다..."):
        try:
            encoded = urllib.parse.quote(prompt_to_use)
            
            # 스타일이 흑백만화/3D/셀애니 등 극단적으로 갈리도록 시드 난수 및 모델 지정
            seed_val = np.random.randint(1, 999999)
            image_url = f"https://image.pollinations.ai/prompt/{encoded}?width=1024&height=1024&nologo=true&seed={seed_val}&model=flux"
            
            res = requests.get(image_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=60)

            if res.status_code == 200:
                img_data = res.content
                st.session_state["base_image"] = Image.open(io.BytesIO(img_data))
                st.session_state["image_bytes"] = img_data
                st.success("원화 생성 성공!")
            else:
                st.error("서버 통신 실패")
        except Exception as e:
            st.error(f"오류 발생: {e}")

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
