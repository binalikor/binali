import io
import os
import tempfile
import urllib.parse
import cv2
import numpy as np
from PIL import Image
import requests
import streamlit as st

st.set_page_config(page_title="애니메이션 삽화 스튜디오", layout="wide")
st.title("📚 애니메이션 삽화 & 모션 씬 스튜디오")
st.write("한국어 묘사를 문맥 그대로 살려내어 요청하신 의도대로 원화를 생성합니다.")

# 1. 한국어 문맥을 전문 프롬프트로 변환하는 LLM 번역 함수
def convert_korean_to_art_prompt(ko_text):
    if not ko_text.strip():
        return ""
    
    system_instruction = (
        "You are an expert AI prompt engineer for animation and storybook illustrations. "
        "Translate the user's Korean description into a vivid, descriptive English prompt. "
        "Keep all cultural and specific details intact (e.g. conical straw hat covering down to chin, "
        "primitive clothes woven from vines, ancient creator god Mireuk, earthy clay skin). "
        "Output ONLY the final English prompt without conversational text or quotes."
    )
    
    url = f"https://text.pollinations.ai/{urllib.parse.quote(ko_text)}?system={urllib.parse.quote(system_instruction)}"
    
    try:
        res = requests.get(url, timeout=12)
        if res.status_code == 200 and res.text.strip():
            return res.text.strip().strip('"')
    except Exception:
        pass
        
    # 예외 시 기본 백업 번역
    backup_url = "https://translate.googleapis.com/translate_a/single"
    params = {"client": "gtx", "sl": "ko", "tl": "en", "dt": "t", "q": ko_text}
    try:
        r = requests.get(backup_url, params=params, timeout=5)
        if r.status_code == 200:
            pieces = [item[0] for item in r.json()[0] if item[0]]
            return "".join(pieces).strip()
    except Exception:
        pass
    return ko_text.strip()

# 2. 장면 입력 UI
st.subheader("1. 장면 묘사 입력")
user_desc = st.text_area(
    "장면 설명 (한국어로 상세히 입력)",
    value="한국 전래동화 이야기책 스타일 삽화. 거대한 신 미륵의 전신 모습. 얼굴 턱까지 덮는 큰 짚 고깔모자를 쓰고, 칡넝쿨로 짠 갈색 원시 옷을 입고 있다. 흙빛 피부에 눈빛은 따뜻하다. 부드러운 먹선과 수채화 채색, 동화책 삽화 스타일, 흰색 배경, 16:9 비율",
    height=120
)

# 3. 이미지 생성
if st.button("🎨 원화 생성 시작 🚀"):
    if not user_desc.strip():
        st.warning("장면 설명을 입력해주세요!")
    else:
        with st.spinner("한국어 문맥을 분석하여 원화를 그리고 있습니다 (약 8~12초)..."):
            try:
                # LLM을 통한 문맥 프롬프트 변환
                final_english = convert_korean_to_art_prompt(user_desc)
                st.session_state["used_en_prompt"] = final_english
                
                # 이미지 생성 요청 (16:9 규격)
                encoded = urllib.parse.quote(final_english)
                seed_val = np.random.randint(1, 999999)
                image_url = f"https://image.pollinations.ai/prompt/{encoded}?width=1280&height=720&nologo=true&seed={seed_val}&model=flux"
                
                res = requests.get(image_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=60)
                if res.status_code == 200:
                    img_data = res.content
                    st.session_state["base_image"] = Image.open(io.BytesIO(img_data))
                    st.session_state["image_bytes"] = img_data
                    st.success("원화 생성 완료!")
                else:
                    st.error("이미지 서버 연결 실패")
            except Exception as e:
                st.error(f"생성 중 오류: {e}")

# 4. 결과 및 모션 비디오 렌더링
if "base_image" in st.session_state:
    st.divider()
    st.caption(f"🔍 **AI가 해석한 묘사:** `{st.session_state.get('used_en_prompt', '')}`")
    base_img = st.session_state["base_image"]
    st.image(base_img, use_container_width=True)

    st.subheader("2. 애니메이션 모션 렌더링 (16:9 규격)")
    col1, col2 = st.columns(2)
    with col1:
        motion_type = st.selectbox(
            "카메라 무빙",
            ["천천히 줌인 (Slow Zoom In)", "좌에서 우로 패닝 (Pan Right)", "우에서 좌로 패닝 (Pan Left)"]
        )
    with col2:
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
                scale = 1.1
                crop_w, crop_h = int(w / scale), int(h / scale)
                y1 = (h - crop_h) // 2
                x1 = int((w - crop_w) * ratio)

            elif "Pan Left" in mode:
                scale = 1.1
                crop_w, crop_h = int(w / scale), int(h / scale)
                y1 = (h - crop_h) // 2
                x1 = int((w - crop_w) * (1.0 - ratio))

            x2, y2 = min(w, x1 + crop_w), min(h, y1 + crop_h)
            cropped = img_np[y1:y2, x1:x2]
            frame = cv2.resize(cropped, (w, h), interpolation=cv2.INTER_LINEAR)
            out.write(frame)

        out.release()

    if st.button("🎬 모션 영상(MP4) 렌더링"):
        with st.spinner("16:9 모션 컷을 생성 중입니다..."):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_file:
                target_video = tmp_file.name

            render_motion(base_img, target_video, motion_type, duration)

            with open(target_video, "rb") as f:
                v_bytes = f.read()

            st.video(v_bytes)
            st.download_button(
                label="📥 애니메이션 MP4 다운로드",
                data=v_bytes,
                file_name="animation_cut.mp4",
                mime="video/mp4"
            )

            if os.path.exists(target_video):
                os.remove(target_video)
