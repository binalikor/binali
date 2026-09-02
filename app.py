import io
import os
import tempfile
import urllib.parse
import cv2
import numpy as np
from PIL import Image
import requests
import streamlit as st

st.set_page_config(page_title="애니메이션 스튜디오", layout="wide")
st.title("🎬 애니메이션 & 삽화 전문 제작 스튜디오")
st.write("한국어 묘사를 디테일 태그로 구조화하여 설명 누락 없이 16:9 정규 비율로 생성합니다.")

# 1. 문맥 및 디테일 보존 번역 함수
def convert_to_anime_tags(text):
    if not text.strip():
        return ""
    # 영문 위주 입력 시 그대로 반환
    if all(ord(c) < 128 for c in text.replace(" ", "")):
        return text.strip()

    system_prompt = (
        "Convert the user's Korean animation scene description into detailed, high-priority English tags and descriptive phrases. "
        "Preserve every single specific detail (e.g. 1.5 head ratio, chibi, glowing ember on tail tip, bronze coin necklace, straw hat). "
        "Output ONLY the comma-separated English prompt, nothing else."
    )
    url = f"https://text.pollinations.ai/{urllib.parse.quote(text)}?system={urllib.parse.quote(system_prompt)}"
    
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200 and res.text.strip():
            return res.text.strip().strip('"')
    except Exception:
        pass

    # 백업 번역
    try:
        backup_url = "https://translate.googleapis.com/translate_a/single"
        params = {"client": "gtx", "sl": "ko", "tl": "en", "dt": "t", "q": text}
        r = requests.get(backup_url, params=params, timeout=5)
        if r.status_code == 200:
            return "".join([item[0] for item in r.json()[0] if item[0]]).strip()
    except Exception:
        pass
    return text.strip()

# 2. 입력 UI
st.subheader("1. 장면 및 캐릭터 묘사")

col_input, col_opt = st.columns([3, 1])
with col_input:
    user_prompt = st.text_area(
        "묘사 내용 (한국어 또는 영어)",
        value="Character design sheet of a tiny mystical Korean field mouse spirit, 1.5 head ratio chibi cute style, wise and clever expression, large curious golden eyes, soft textured brown fur, tiny glowing ember sparks drifting from its tail tip, wearing a tiny red cord necklace with a miniature bronze coin, multiple poses, clean off-white background, anime concept art",
        height=110
    )
with col_opt:
    model_choice = st.selectbox(
        "생성 엔진",
        ["애니메이션 특화 (flux-anime)", "표준 고화질 (flux)"]
    )

selected_model = "flux-anime" if "flux-anime" in model_choice else "flux"

# 3. 이미지 생성 (정규 16:9 해상도 1024x576 고정으로 찌그러짐 방지)
if st.button("🎨 이미지 생성 시작 🚀"):
    if not user_prompt.strip():
        st.warning("설명을 입력해주세요!")
    else:
        with st.spinner("지시어를 분석하여 원화를 생성 중입니다..."):
            try:
                # 프롬프트 번역 및 정제
                final_tags = convert_to_anime_tags(user_prompt)
                
                # 미드저니 파라미터(--ar 등) 잔여물 자동 제거
                clean_tags = final_tags.replace("--ar 16:9", "").replace("--ar", "").strip()
                st.session_state["used_prompt"] = clean_tags

                encoded = urllib.parse.quote(clean_tags)
                seed_val = np.random.randint(1, 999999)

                # 16:9 정규 와이드 규격 (1024x576)
                image_url = (
                    f"https://image.pollinations.ai/prompt/{encoded}"
                    f"?width=1024&height=576&nologo=true&seed={seed_val}&model={selected_model}"
                )

                res = requests.get(image_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=60)
                if res.status_code == 200:
                    img_data = res.content
                    st.session_state["base_image"] = Image.open(io.BytesIO(img_data))
                    st.session_state["image_bytes"] = img_data
                    st.success("원화 생성 완료!")
                else:
                    st.error("이미지 서버 통신 실패")
            except Exception as e:
                st.error(f"생성 중 오류: {e}")

# 4. 결과 출력 및 16:9 모션 비디오 렌더링
if "base_image" in st.session_state:
    st.divider()
    st.caption(f"🔍 **반영된 지시어 태그:** `{st.session_state.get('used_prompt', '')}`")
    base_img = st.session_state["base_image"]
    st.image(base_img, use_container_width=True)

    st.subheader("2. 16:9 애니메이션 모션 비디오 렌더링")
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        motion_type = st.selectbox(
            "카메라 연출",
            ["천천히 줌인 (Slow Zoom In)", "좌->우 패닝 (Pan Right)", "우->좌 패닝 (Pan Left)"]
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
                scale = 1.0 + 0.18 * ratio
                crop_w, crop_h = int(w / scale), int(h / scale)
                x1, y1 = (w - crop_w) // 2, (h - crop_h) // 2

            elif "Pan Right" in mode:
                scale = 1.12
                crop_w, crop_h = int(w / scale), int(h / scale)
                y1 = (h - crop_h) // 2
                x1 = int((w - crop_w) * ratio)

            elif "Pan Left" in mode:
                scale = 1.12
                crop_w, crop_h = int(w / scale), int(h / scale)
                y1 = (h - crop_h) // 2
                x1 = int((w - crop_w) * (1.0 - ratio))

            x2, y2 = min(w, x1 + crop_w), min(h, y1 + crop_h)
            cropped = img_np[y1:y2, x1:x2]
            frame = cv2.resize(cropped, (w, h), interpolation=cv2.INTER_LINEAR)
            out.write(frame)

        out.release()

    if st.button("🎬 모션 비디오(MP4) 생성"):
        with st.spinner("비디오를 렌더링 중입니다..."):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_file:
                target_video = tmp_file.name

            render_motion(base_img, target_video, motion_type, duration)

            with open(target_video, "rb") as f:
                v_bytes = f.read()

            st.video(v_bytes)
            st.download_button(
                label="📥 애니메이션 비디오(MP4) 다운로드",
                data=v_bytes,
                file_name="animated_scene.mp4",
                mime="video/mp4"
            )

            if os.path.exists(target_video):
                os.remove(target_video)
