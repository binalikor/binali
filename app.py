import io
import requests
import streamlit as st
from PIL import Image
from openai import OpenAI

st.set_page_config(page_title="설화 16:9 영상 스튜디오", layout="wide")
st.title("🎬 한국 설화 16:9 삽화 & 모션 스튜디오")

with st.sidebar:
    st.header("🔑 설정")
    api_key = st.text_input("OpenAI API Key 입력", type="password", placeholder="sk-...")

user_prompt = st.text_area(
    "장면 묘사 (한글)",
    value="짚으로 엮은 거대한 고깔모자를 쓰고 칡넝쿨 옷을 입은 거인 미륵이 안개 낀 한반도 산골짜기에 온화한 표정으로 우뚝 서 있다."
)

if st.button("🎨 16:9 삽화 생성"):
    if not api_key:
        st.error("OpenAI API Key를 사이드바에 입력해 주세요.")
    else:
        with st.spinner("삽화 생성 중..."):
            try:
                client = OpenAI(api_key=api_key)
                full_prompt = (
                    f"Korean traditional ink wash and watercolor painting, hanji paper texture: {user_prompt}"
                )
                res = client.images.generate(
                    model="dall-e-2",
                    prompt=full_prompt,
                    size="1024x1024",
                    n=1
                )
                img_data = requests.get(res.data[0].url).content
                raw_img = Image.open(io.BytesIO(img_data)).convert("RGB")
                
                # 1024x1024 정방형을 16:9 와이드(1024x576)로 중앙 크롭 정렬
                w, h = raw_img.size
                target_h = int(w * 9 / 16)
                offset_y = (h - target_h) // 2
                st.session_state["img"] = raw_img.crop((0, offset_y, w, offset_y + target_h))
                
                st.success("삽화 생성 완료")
            except Exception as e:
                st.error(f"오류: {e}")

if "img" in st.session_state:
    st.divider()
    img = st.session_state["img"]
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("생성된 삽화 (16:9 규격)")
        st.image(img, use_container_width=True)

    with c2:
        st.subheader("모션 영상 변환")
        motion = st.selectbox("카메라 연출", ["천천히 줌인", "우측으로 패닝"])
        sec = st.slider("재생 시간(초)", 2, 5, 3)

        if st.button("🎬 모션 렌더링"):
            with st.spinner("영상 렌더링 중..."):
                w, h = 1280, 720
                base = img.resize((w, h), Image.Resampling.LANCZOS)
                fps = 15
                total = fps * sec
                frames = []

                for i in range(total):
                    r = i / (total - 1)
                    if motion == "천천히 줌인":
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
                frames[0].save(buf, format="WEBP", save_all=True, append_images=frames[1:], duration=int(1000/fps), loop=0)
                
                st.image(buf.getvalue(), caption="완성 영상", use_container_width=True)
                st.download_button("📥 영상 다운로드", buf.getvalue(), "scene_16_9.webp", "image/webp")
