import io
import base64
import streamlit as st
from PIL import Image
from openai import OpenAI

st.set_page_config(page_title="설화 16:9 스튜디오", layout="wide")
st.title("🎬 한국 설화 제작 스튜디오")

# 탭 분리: 삽화 생성 / 모션 변환
tab1, tab2 = st.tabs(["🎨 1. 삽화 생성", "🎞️ 2. 모션 영상 변환"])

# -------------------------------------------------------------
# TAB 1: 삽화 생성 페이지
# -------------------------------------------------------------
with tab1:
    st.subheader("16:9 설화 삽화 제작")
    
    col_k, col_p = st.columns([1, 2])
    with col_k:
        api_key = st.text_input("OpenAI API Key", type="password", placeholder="sk-...", key="api_key_input")
        art_style = st.selectbox(
            "화풍 선택",
            ["한국 전통 수묵 담채화", "고전 설화 일러스트", "신화 다큐풍"]
        )
    
    with col_p:
        user_prompt = st.text_area(
            "장면 묘사 (한글)",
            value="짚으로 엮은 거대한 고깔모자를 쓰고 칡넝쿨 옷을 입은 거인 미륵이 안개 낀 한반도 산골짜기에 온화한 표정으로 우뚝 서 있다.",
            height=110
        )

    if st.button("🎨 삽화 생성 실행", key="btn_gen_img"):
        if not api_key:
            st.error("API Key를 입력해 주세요.")
        else:
            with st.spinner("이미지 생성 중 (약 15~20초 소요)..."):
                try:
                    client = OpenAI(api_key=api_key)
                    full_prompt = (
                        f"16:9 widescreen composition, authentic Korean folklore art style ({art_style}), "
                        f"traditional hanji paper texture, brush strokes: {user_prompt}"
                    )
                    
                    res = client.images.generate(
                        model="gpt-image-1",
                        prompt=full_prompt,
                        size="1536x1024"
                    )
                    
                    img_b64 = res.data[0].b64_json
                    raw_img = Image.open(io.BytesIO(base64.b64decode(img_b64))).convert("RGB")
                    
                    # 16:9 와이드 비율로 중앙 크롭 정렬
                    w, h = raw_img.size
                    target_h = int(w * 9 / 16)
                    if h > target_h:
                        offset_y = (h - target_h) // 2
                        raw_img = raw_img.crop((0, offset_y, w, offset_y + target_h))
                    
                    st.session_state["shared_img"] = raw_img
                    st.success("삽화 생성 완료! '모션 영상 변환' 탭으로 이동하세요.")
                    
                except Exception as e:
                    st.error(f"생성 실패: {e}")

    if "shared_img" in st.session_state:
        st.divider()
        st.image(st.session_state["shared_img"], caption="현재 생성된 16:9 원화", use_container_width=True)

# -------------------------------------------------------------
# TAB 2: 모션 영상 변환 페이지 (단독 작업 가능)
# -------------------------------------------------------------
with tab2:
    st.subheader("16:9 모션 비디오 렌더러")
    st.caption("1번 탭에서 만든 삽화를 쓰거나, 외부에서 준비한 16:9 이미지를 직접 올려서 영상을 굽습니다.")
    
    uploaded_file = st.file_uploader("외부 이미지 직접 올리기 (선택 사항)", type=["png", "jpg", "jpeg", "webp"])
    
    # 작업 대상 이미지 결정 (직접 업로드 우선 -> 1번 탭 생성본)
    target_img = None
    if uploaded_file is not None:
        target_img = Image.open(uploaded_file).convert("RGB")
    elif "shared_img" in st.session_state:
        target_img = st.session_state["shared_img"]
    
    if target_img:
        col_view, col_ctrl = st.columns([1, 1])
        with col_view:
            st.image(target_img, caption="변환할 원본 이미지", use_container_width=True)
            
        with col_ctrl:
            motion = st.selectbox("카메라 워킹 연출", ["천천히 줌인 (Slow Zoom)", "우측으로 훑기 (Pan Right)"])
            sec = st.slider("영상 길이 (초)", min_value=2, max_value=6, value=3)
            
            if st.button("🎬 모션 렌더링 시작", key="btn_render_motion"):
                with st.spinner("카메라 모션 렌더링 중..."):
                    w, h = 1280, 720
                    base = target_img.resize((w, h), Image.Resampling.LANCZOS)
                    fps = 15
                    total = fps * sec
                    frames = []

                    for i in range(total):
                        r = i / (total - 1)
                        if "Zoom" in motion:
                            scale = 1.0 + 0.15 * r
                            cw, ch = int(w / scale), int(h / scale)
                            x, y = (w - cw) // 2, (h - ch) // 2
                        else:
                            scale = 1.1
                            cw, ch = int(w / scale), int(h / scale)
                            y = (h - ch) // 2
                            x = int((w - cw) * r)
                        frames.append(base.crop((x, y, x + cw, y + ch)).resize((w, h), Image.Resampling.BILINEAR))

                    buf = io.BytesIO()
                    frames[0].save(
                        buf, 
                        format="WEBP", 
                        save_all=True, 
                        append_images=frames[1:], 
                        duration=int(1000 / fps), 
                        loop=0,
                        quality=90
                    )
                    anim_bytes = buf.getvalue()

                    st.success("모션 렌더링 완료!")
                    st.image(anim_bytes, caption="완성된 16:9 모션 애니메이션", use_container_width=True)
                    st.download_button("📥 애니메이션 다운로드", anim_bytes, "scene_motion.webp", "image/webp")
    else:
        st.info("작업할 이미지가 없습니다. 1번 탭에서 삽화를 생성하거나 위 업로더에 이미지를 넣어주세요.")
