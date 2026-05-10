from __future__ import annotations

import os
import sys
from pathlib import Path

import streamlit as st

st.set_page_config(page_title="독일어 영상 자막/번역", layout="wide")

st.title("독일어 영상 자막/번역")
st.caption("영상/음성 파일에서 독일어 원문 SRT, 영어 SRT, 한국어 SRT를 로컬로 생성합니다.")


def toolkit_root() -> Path:
    env_root = os.environ.get("MUNICH_TOOLKIT_ROOT")
    if env_root:
        return Path(env_root).expanduser().resolve()
    return Path(__file__).resolve().parents[3]


ROOT = toolkit_root()
GERMAN_APP_DIR = ROOT / "apps" / "german_stt_local"
if str(GERMAN_APP_DIR) not in sys.path:
    sys.path.insert(0, str(GERMAN_APP_DIR))

st.info(
    "첫 실행 전에는 루트 폴더의 `SETUP_VIDEO_STT_ONCE.bat`를 한 번 실행하는 게 안전합니다. "
    "Whisper/NLLB 모델은 처음 사용할 때 인터넷으로 다운로드됩니다."
)

try:
    import torch  # type: ignore
    cuda_ok = torch.cuda.is_available()
    gpu_name = torch.cuda.get_device_name(0) if cuda_ok else "CPU"
except Exception as exc:
    torch = None  # type: ignore
    cuda_ok = False
    gpu_name = "torch 미설치"
    st.warning(f"torch를 불러오지 못했습니다: {exc}")

c1, c2, c3 = st.columns(3)
c1.metric("German module", "yes" if GERMAN_APP_DIR.exists() else "no")
c2.metric("CUDA", "yes" if cuda_ok else "no")
c3.metric("Device", gpu_name)

uploaded = st.file_uploader(
    "영상 또는 음성 파일 업로드",
    type=["mp4", "mov", "mkv", "webm", "mp3", "wav", "m4a", "aac"],
)

col1, col2 = st.columns(2)
with col1:
    whisper_model = st.selectbox("Whisper 모델", ["large-v3", "medium", "small"], index=0)
with col2:
    korean_mode = st.selectbox(
        "한국어 번역 방식",
        ["direct", "via_english"],
        index=0,
        format_func=lambda x: "독일어 → 한국어 직접" if x == "direct" else "독일어 → 영어 → 한국어",
    )

try:
    from local_translator import DEFAULT_MODEL  # type: ignore
except Exception:
    DEFAULT_MODEL = "facebook/nllb-200-distilled-600M"

translation_model = st.text_input("로컬 번역 모델", value=DEFAULT_MODEL)
output_name = st.text_input("저장 파일명 선택 사항", value="", placeholder="예: Muenchner_Knabenchor_interview_HIGH")
prompt = st.text_area(
    "Whisper 인식 힌트 선택 사항",
    value=(
        "Münchner Knabenchor, Munich Boys Choir, Tölzer Knabenchor, "
        "Ralf Ludewig, Justus, Knabenchor, Chor, Konzert, Probe, München."
    ),
    height=90,
)
make_english = st.checkbox("영어 SRT 만들기", value=True)
make_korean = st.checkbox("한국어 SRT 만들기", value=True)

start = st.button("자막 생성 시작", type="primary", disabled=(uploaded is None))

if start and uploaded is not None:
    try:
        from pipeline import run_full_pipeline  # type: ignore
    except Exception as exc:
        st.error(f"독일어 STT/번역 모듈을 불러오지 못했습니다: {exc}")
        st.code("SETUP_VIDEO_STT_ONCE.bat", language="text")
        st.stop()

    input_dir = GERMAN_APP_DIR / "input" / "uploaded"
    output_dir = GERMAN_APP_DIR / "output_gpu"
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    save_path = input_dir / uploaded.name
    save_path.write_bytes(uploaded.getbuffer())

    status = st.status("로컬 파이프라인 실행 중...", expanded=True)

    def log(message: str):
        status.write(message)

    try:
        result = run_full_pipeline(
            video_path=save_path,
            output_dir=output_dir,
            output_name=output_name.strip() or None,
            whisper_model=whisper_model,
            translation_model=translation_model.strip() or DEFAULT_MODEL,
            prompt=prompt,
            make_english=make_english,
            make_korean=make_korean,
            korean_mode=korean_mode,
            progress=log,
        )
        status.update(label="완료!", state="complete", expanded=True)
        st.success("자막 파일 생성 완료!")
        st.write("저장 폴더:")
        st.code(result["output_dir"], language="text")

        for label, key in [
            ("독일어 원문 SRT", "de_srt"),
            ("영어 번역 SRT", "en_srt"),
            ("한국어 번역 SRT", "ko_srt"),
        ]:
            file_path = result["outputs"].get(key)
            if file_path:
                path = Path(file_path)
                with path.open("rb") as f:
                    st.download_button(label=f"{label} 다운로드", data=f, file_name=path.name, mime="application/x-subrip")
    except Exception as exc:
        status.update(label="오류 발생", state="error", expanded=True)
        st.error(str(exc))
        st.info("자주 나는 원인: ffmpeg PATH 누락, large-v3 GPU 메모리 부족, 첫 실행 모델 다운로드 실패. GPU 오류면 medium으로 바꿔보세요.")
