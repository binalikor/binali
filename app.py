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
st.title("🎬 한국어 AI 이미지 & 모션 비디오 스튜디오")
st.write("한국어로 원하는 핵심 주제를 적고 화풍을 선택하면, 고화질 영문 프롬프트로 최적화되어 이미지를 생성합니다.")

# 1. 한국어 프롬프트 입력 및 옵션 구성
col_in1, col_in2 = st.columns([2, 1])

with col_in1:
    user_topic = st.text_input(
        "그릴 대상/주제 (한국어)",
        value="우주복을 입은 귀여운 레서판다",
        placeholder="예: 숲속의 신비로운 성, 해변의 스포츠카"
    )

with col_in2:
    style_choice = st.selectbox(
        "화풍/스타일 선택",
        ["3D 애니메이션 (픽사풍)", "극실사 사진 (포토리얼)", "사이버펑크 네온", "판타지 유화", "웹툰/일러스트"]
    )

extra_detail = st.text_input(
    "배경/상세 묘사 (한국어, 선택사항)",
    value="반짝이는 성운과 별빛 배경, 디테일한 조명",
    placeholder="예: 비 내리는 밤거리, 황금빛 일몰"
)

# 간단한 한국어 핵심 단어 사전 (오역 방지용)
KO_EN_DICT = {
    "레서판다": "red panda", "판다": "panda", "고양이": "cat", "강아지": "puppy",
    "호랑이": "tiger", "사자": "lion", "다람쥐": "squirrel", "토끼": "rabbit",
    "우주복": "wearing a tiny astronaut suit", "우주": "deep space",
    "바다": "ocean", "해변": "beach", "일몰": "sunset", "노을": "sunset",
    "숲": "forest", "성": "castle", "도시": "city", "골목": "alley",
    "비": "rainy", "눈": "snowy", "자동차": "sports car", "스포츠카": "sports car",
    "꽃": "flowers", "별": "stars", "케이크": "cake", "커피": "coffee"
}

STYLE_MAP = {
    "3D 애니메이션 (픽사풍)": "3D render, Pixar style, cute, adorable, highly detailed, vibrant colors",
    "극실사 사진 (포토리얼)": "photorealistic, 8k resolution, cinematic lighting, 35mm lens photo, hyperrealistic",
    "사이버펑크 네온": "cyberpunk style, glowing neon lights, futuristic, rainy reflections, cinematic",
    "판타지 유화": "fantasy concept art, ethereal glow, magical atmosphere, detailed oil painting style",
    "웹툰/일러스트": "anime style, vibrant digital art, clean lines, beautiful lighting"
}

def build_refined_prompt(topic, detail, style):
    # 1. 사전 기반 키워드 치환
    eng_parts = []
    combined_ko = f"{topic} {detail}"
    
    matched = False
    for ko_word, en_trans in KO_EN_DICT.items():
        if ko_word in combined_ko:
            eng_parts.append(en_trans)
            matched = True
            
    # 사전에 없는 단어일 경우 기본 영문 변환 요청 (Pollinations 자체 번역 파라미터 활용)
    base_text = ", ".join(eng_parts) if matched else topic
    style_text = STYLE_MAP.get(style, "")
    
    return f"{base_text}, {style_text}, ultra quality"

# 1단계: 생성 버튼
if st.button("1단계: AI 이미지 생성하기 🎨"):
    if not user_topic.strip():
        st.warning("주제를 입력해주세요!")
    else:
        with st.spinner("한국어 지시어를 바탕으로 이미지를 조율 중입니다..."):
            try:
                final_en_prompt = build_refined_prompt(user_topic, extra_detail, style_choice)
                st.session_state["used_prompt"] = final_en_prompt
                
                encoded_prompt = urllib.parse.quote(final_en_prompt)
                image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true&model=flux"
                
                headers = {"User-Agent": "Mozilla/5.0"}
                res = requests.get(image_url, headers=headers, timeout=60)
                
                if res.status_code == 200:
                    img_data = res.content
                    st.session_state["base_image"] = Image.open(io.BytesIO(img_data))
                    st.session_state["image_bytes"] = img_data
                    st.success("이미지 생성 성공!")
                else:
                    st.error("이미지 서버 연결 실패")
            except Exception as e:
                st.error(f"오류 발생: {e}")

# 결과 출력 및 영상 제작
if "base_image" in st.session_state:
    st.divider()
    st.caption(f"🔧 **AI에 전달된 정제 지시어:** `{st.session_state.get('used_prompt', '')}`")
    base_img = st.session_state["base_image"]
    st.image(base_img, use_container_width=True)

    st.divider()
    st.subheader("2. 줌인 모션 비디오 연출")

    motion_type = st.selectbox(
        "카메라 무빙 방식",
        ["천천히 줌인 (Slow Zoom In)", "빠른 돌진 (Dynamic Push In)", "오른쪽 패닝 (Pan Right)", "왼쪽 패닝 (Pan Left)"]
    )
    duration = st.slider("영상 길이(초)", min_value=2, max_value=5, value=3)

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

    if st.button("🎬 모션 비디오(MP4) 렌더링"):
        with st.spinner("비디오를 렌더링 중입니다..."):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_file:
                target_video = tmp_file.name

            render_motion(base_img, target_video, motion_type, duration)

            with open(target_video, "rb") as f:
                v_bytes = f.read()

            st.video(v_bytes)
            st.download_button(
                label="📥 렌더링된 비디오(MP4) 저장",
                data=v_bytes,
                file_name="motion_video.mp4",
                mime="video/mp4"
            )

            if os.path.exists(target_video):
                os.remove(target_video)
