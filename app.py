
import io
from PIL import Image
import requests
import streamlit as st

st.set_page_config(page_title="16:9 한국 설화 원화 스튜디오", layout="wide")
st.title("🎬 16:9 한국 설화 애니메이션 원화 스튜디오 — 창세가")
st.caption("Hugging Face 검증 엔드포인트(FLUX.1-schnell)를 통해 16:9 규격 원화를 렌더링합니다.")

# ── 캐릭터 / 공통 스타일 프리셋 ──────────────────────────────
CHARACTER_PROMPTS = {
    "(선택 안 함)": "",
    "미륵": "a towering ancient Korean creator deity, calm and serene expression, long flowing beard, wearing a rough hemp-fiber robe with wide sleeves, tall pointed hemp hood, bare feet, dignified and slow-moving presence, muted earth-tone palette (ochre, brown, faded white)",
    "석가": "a Korean deity figure with a sharper angular face, sly calculating eyes, silk robe with silver thread accents, restless posture, cool color palette (grey, silver, deep blue)",
    "생쥐": "a small clever mouse character, slightly anthropomorphized but still animal-like, alert posture, glinting eyes suggesting cunning, folk-art woodblock print style",
    "풀메뚜기/풀개구리": "a small grasshopper (or frog), rendered in folk-art woodblock style, humble and simple, slightly comedic proportions",
}

SCENE_PROMPTS = {
    "(선택 안 함)": "",
    "S#1 태초, 하늘과 땅": "a towering deity separating heaven and earth with outstretched hands, four massive bronze pillars rising at the corners of the earth, dark and sacred atmosphere, bold lines and negative space",
    "S#2 해와 달, 별의 탄생": "a night sky where a deity splits twin suns and twin moons apart, stars scattering with varying brightness, mystical color palette",
    "S#3 칡으로 옷을 짓다": "a giant deity weaving thread from kudzu vine at a loom set among the clouds, unfolding a finished rough hemp robe, humble and devoted atmosphere",
    "S#4 물과 불의 근본을 찾다": "tiny insects (grasshopper, frog, mouse) restrained before a giant deity, serious yet comically disproportionate scale",
    "S#5 금쟁반과 은쟁반": "glowing insects on a gold tray and a silver tray transforming into human figures, sacred and surreal atmosphere, minimal color, generous negative space",
    "S#6 도전": "two deities in tense confrontation, one radiating warm earthy colors, the other cool silvery tones",
    "S#7 첫 번째 내기 (금병과 은병)": "a gold bottle and a silver bottle suspended over the East Sea, taut cords, one cord snapping at the moment of defeat",
    "S#8 두 번째 내기 (여름에 강 얼리기)": "a river gradually freezing over in the middle of lush summer greenery, one calm figure and one anxious figure contrasted",
    "S#9 세 번째 내기 (모란꽃)": "a dark room, two sleeping deities, a peony blossom blooming between them, one figure secretly stealing the flower stem, tense chiaroscuro lighting, Korean traditional pigment painting feel",
    "S#10 미륵의 마지막 말과 예언": "a solitary deity turning away in quiet sorrow, a short montage feel: a wooden totem pole (sotdae), an empty house, shadow-like human figures, muted and melancholic tone",
    "S#11 건달들의 등장과 미륵의 도피": "a chaotic crowd of rough figures emerging from the earth, contrasted with a lone deity quietly walking away in the distance",
    "S#12 노루고기와 두 중 (엔딩)": "a rock and a pine tree on a mountain, spring blossoms drifting below, villagers preparing a ritual flower-pancake feast, a dissolve composition suggesting the passage of time, warm yet wistful colors",
}

COMMON_STYLE_TAG = "Korean folk mythology art style, woodblock print texture, bold ink outlines, muted natural pigments, generous negative space, painterly and slightly weathered, no modern elements, cinematic and solemn atmosphere"

# ── 사이드바: 인증 및 모델 설정 ──────────────────────────────
with st.sidebar:
    st.header("🔑 Hugging Face 설정")
    hf_token = st.text_input(
        "Access Token",
        value="",
        type="password",
        help="hf_로 시작하는 토큰을 매 세션마다 직접 입력하세요. 코드에는 절대 저장하지 마세요.",
    )
    if not hf_token:
        st.warning("토큰이 입력되지 않았습니다. 아래에서 입력해야 이미지를 생성할 수 있습니다.")
    model_name = "black-forest-labs/FLUX.1-schnell"
    st.text(f"연결 모델: {model_name}")

    st.divider()
    st.header("📐 이미지 규격")
    width = st.selectbox("가로(px)", [1280, 1024, 768], index=0)
    height = st.selectbox("세로(px)", [720, 576, 432], index=0)

st.subheader("1. 캐릭터 / 씬 프리셋 선택 (선택 사항)")
col1, col2 = st.columns(2)
with col1:
    picked_character = st.selectbox("캐릭터 프리셋", list(CHARACTER_PROMPTS.keys()))
with col2:
    picked_scene = st.selectbox("씬 프리셋", list(SCENE_PROMPTS.keys()))

st.subheader("2. 장면 묘사 입력 (한국어, 자유롭게 수정 가능)")
default_desc = "한국 전래동화 이야기책 스타일 삽화."
user_desc = st.text_area("장면 설명 (한국어)", value=default_desc, height=100)

use_presets = st.checkbox("위에서 선택한 캐릭터/씬 프리셋을 프롬프트에 자동으로 포함", value=True)


def build_art_prompt(ko_text: str) -> str:
    if not ko_text.strip():
        return ""
    url = "https://translate.googleapis.com/translate_a/single"
    params = {"client": "gtx", "sl": "ko", "tl": "en", "dt": "t", "q": ko_text}
    try:
        res = requests.get(url, params=params, timeout=5)
        if res.status_code == 200:
            en_base = "".join(piece[0] for piece in res.json()[0] if piece[0]).strip()
        else:
            en_base = ko_text
    except Exception:
        en_base = ko_text

    parts = [en_base]
    if use_presets:
        if CHARACTER_PROMPTS.get(picked_character):
            parts.append(CHARACTER_PROMPTS[picked_character])
        if SCENE_PROMPTS.get(picked_scene):
            parts.append(SCENE_PROMPTS[picked_scene])
    parts.append(COMMON_STYLE_TAG)
    parts.append("16:9 wide aspect ratio, clean composition, sharp details")
    return ", ".join(p for p in parts if p)


def request_hf_image(prompt: str, token: str, model: str, w: int, h: int):
    clean_token = token.strip()
    if not clean_token.startswith("hf_"):
        clean_token = "hf_" + clean_token

    api_url = f"https://router.huggingface.co/hf-inference/models/{model}"
    headers = {"Authorization": f"Bearer {clean_token}", "Content-Type": "application/json"}
    payload = {"inputs": prompt, "parameters": {"width": w, "height": h}}

    res = requests.post(api_url, headers=headers, json=payload, timeout=40)

    if res.status_code == 200:
        return res.content, None
    elif res.status_code == 503:
        return None, "서버가 모델을 준비 중입니다(Cold Start). 약 15초 후 다시 눌러주세요."
    elif res.status_code == 401:
        return None, "인증 실패: Hugging Face 토큰을 확인해주세요."
    else:
        return None, f"서버 응답 오류 ({res.status_code}): {res.text}"


if st.button("🎨 16:9 원화 생성 시작 🚀"):
    if not hf_token.strip():
        st.error("사이드바에 토큰을 입력해주세요.")
    elif not user_desc.strip():
        st.warning("장면 설명을 입력해주세요.")
    else:
        status_box = st.empty()
        status_box.info("Hugging Face 엔드포인트로 원화를 생성 중입니다...")
        try:
            prompt_en = build_art_prompt(user_desc)
            st.session_state["used_prompt"] = prompt_en

            img_bytes, err = request_hf_image(prompt_en, hf_token, model_name, width, height)

            if img_bytes:
                img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
                st.session_state["base_image"] = img
                st.session_state["img_bytes"] = img_bytes
                st.session_state["scene_label"] = picked_scene
                status_box.success(f"원화 생성 완료! ({img.size[0]}x{img.size[1]})")
            else:
                status_box.error(err)
        except requests.exceptions.Timeout:
            status_box.error("서버 응답 시간 초과. 잠시 후 다시 시도해주세요.")
        except Exception as e:
            status_box.error(f"통신 오류: {e}")

if "base_image" in st.session_state:
    st.divider()
    st.caption(f"🔍 **적용된 영문 프롬프트:** `{st.session_state.get('used_prompt', '')}`")
    base_img = st.session_state["base_image"]
    st.image(base_img, caption="생성된 원화", use_container_width=True)

    scene_label = st.session_state.get("scene_label", "scene")
    safe_name = scene_label.split(" ")[0] if scene_label != "(선택 안 함)" else "scene"
    st.download_button(
        label="📥 고화질 원화 다운로드 (PNG)",
        data=st.session_state["img_bytes"],
        file_name=f"changsega_{safe_name}.png",
        mime="image/png",
    )
