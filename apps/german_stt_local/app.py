from __future__ import annotations

from pathlib import Path

import streamlit as st
import torch

from local_translator import DEFAULT_MODEL, deepl_auth_key
from pipeline import run_full_pipeline
from whisper_stt import openai_api_key_configured


st.set_page_config(
    page_title="Munich Local Voice Translator",
    page_icon="STT",
    layout="centered",
)

st.title("Munich Local Voice Translator")
st.caption("영상/음성에서 원어 원문, 타임스탬프 기준, 병합 원문 SRT와 필요한 영어/한국어 번역 SRT를 생성합니다.")

with st.expander("현재 실행 상태", expanded=True):
    cuda_ok = torch.cuda.is_available()
    deepl_ok = bool(deepl_auth_key())
    openai_ok = openai_api_key_configured()
    st.write("OpenAI STT key:", "configured" if openai_ok else "missing")
    st.write("CUDA 사용 가능:", cuda_ok)
    st.write("사용 장치:", torch.cuda.get_device_name(0) if cuda_ok else "CPU")
    st.write("DeepL 키:", "설정됨" if deepl_ok else "없음")
    st.write("로컬 후처리 모델: Whisper large-v3")
    if not cuda_ok and not openai_ok:
        st.error("CUDA GPU와 OPENAI_API_KEY가 모두 없어 STT를 실행할 수 없습니다.")
    elif not cuda_ok:
        st.info("CUDA GPU는 없지만 OpenAI STT 키가 있어 API 방식으로 실행할 수 있습니다.")

uploaded = st.file_uploader(
    "영상 또는 음성 파일 업로드",
    type=["mp4", "mov", "mkv", "webm", "mp3", "wav", "m4a", "aac"],
)

col1, col2 = st.columns(2)

with col1:
    stt_provider = st.selectbox(
        "STT provider",
        ["auto", "openai", "local"],
        index=0,
        help="auto uses OpenAI first, then falls back to local Whisper if API quota/token/network fails.",
    )
    openai_stt_model = st.selectbox(
        "OpenAI STT model",
        ["gpt-4o-transcribe", "gpt-4o-mini-transcribe", "whisper-1", "gpt-4o-transcribe-diarize"],
        index=0,
        help="gpt-4o-transcribe is used for the most accurate source transcript. Timestamps come from local Whisper.",
    )
    whisper_model = st.selectbox(
        "Local Whisper model",
        ["large-v3"],
        index=0,
        help="Used for both local timestamp generation and local fallback if OpenAI STT fails.",
    )

with col2:
    source_language = st.selectbox(
        "Source language",
        ["auto", "de", "en", "la"],
        index=0,
        format_func=lambda x: {"auto": "자동 감지", "de": "독일어", "en": "영어", "la": "라틴어"}[x],
    )
    korean_mode = st.selectbox(
        "한국어 번역 방식",
        ["direct", "via_english"],
        index=0,
        format_func=lambda x: "원문 -> 한국어 직접" if x == "direct" else "원문 -> 영어 -> 한국어",
        help="기본값은 직접 번역입니다. 결과가 어색하면 via_english를 테스트하세요.",
    )

translation_model = st.text_input(
    "DeepL 실패 시 fallback Facebook/NLLB 모델",
    value=DEFAULT_MODEL,
    help="기본 번역은 DeepL입니다. DeepL 한도 소진/실패 시에만 이 로컬 모델을 GPU에서 실행합니다.",
)

output_name = st.text_input(
    "저장 파일명 선택 사항",
    value="",
    placeholder="예: Muenchner_Knabenchor_interview_HIGH",
)

prompt = st.text_area(
    "Whisper 인식 힌트 선택 사항",
    value=(
        "Muenchner Knabenchor, Munich Boys Choir, Toelzer Knabenchor, "
        "Ralf Ludewig, Justus, Knabenchor, Chor, Konzert, Probe, Muenchen."
    ),
    height=90,
)

make_english = st.checkbox("영어 SRT 만들기", value=True)
make_korean = st.checkbox("한국어 SRT 만들기", value=True)

openai_ok = openai_api_key_configured()
can_run_stt = cuda_ok or (openai_ok and stt_provider in {"auto", "openai"})
stop_flag = Path("RUN_STOP.flag")
start_col, stop_col = st.columns([1, 1])
with start_col:
    start = st.button("자막 생성 시작", type="primary", disabled=(uploaded is None or not can_run_stt))
with stop_col:
    if st.button("실행 중단 요청"):
        stop_flag.write_text("stop", encoding="utf-8")
        st.warning("중단 요청을 보냈습니다. 현재 처리 중인 API 요청/모델 단계가 끝나는 즉시 멈춥니다.")

if start and uploaded is not None:
    if stop_flag.exists():
        stop_flag.unlink()

    input_dir = Path("input") / "uploaded"
    input_dir.mkdir(parents=True, exist_ok=True)

    save_path = input_dir / uploaded.name
    save_path.write_bytes(uploaded.getbuffer())

    status = st.status("로컬 파이프라인 실행 중...", expanded=True)

    def log(message: str):
        if stop_flag.exists():
            raise RuntimeError("사용자 요청으로 파이프라인을 중단했습니다.")
        status.write(message)

    def cancel_check() -> bool:
        return stop_flag.exists()

    try:
        result = run_full_pipeline(
            video_path=save_path,
            output_dir="output_gpu",
            output_name=output_name.strip() or None,
            whisper_model=whisper_model,
            stt_provider=stt_provider,
            openai_stt_model=openai_stt_model,
            source_language=source_language,
            translation_model=translation_model.strip() or DEFAULT_MODEL,
            prompt=prompt,
            make_english=make_english,
            make_korean=make_korean,
            korean_mode=korean_mode,
            require_gpu=True,
            cancel_check=cancel_check,
            progress=log,
        )

        status.update(label="완료!", state="complete", expanded=True)

        st.success("자막 파일 생성 완료!")

        outputs = result["outputs"]
        st.write("저장 폴더:")
        st.code(result["output_dir"])
        st.write("번역 엔진:")
        st.json(result.get("translation_providers", {}))
        if result.get("skipped_translations"):
            st.write("건너뛴 번역:")
            st.json(result.get("skipped_translations", []))

        for label, key in [
            ("OpenAI 원문 텍스트", "original_txt"),
            ("로컬 타임스탬프 기준 SRT", "timestamp_srt"),
            ("병합 원문 SRT", "source_srt"),
            ("영어 번역 SRT", "en_srt"),
            ("한국어 번역 SRT", "ko_srt"),
        ]:
            file_path = outputs.get(key)
            if file_path:
                path = Path(file_path)
                with path.open("rb") as f:
                    st.download_button(
                        label=f"{label} 다운로드",
                        data=f,
                        file_name=path.name,
                        mime="application/x-subrip",
                    )

    except Exception as exc:
        status.update(label="오류 발생", state="error", expanded=True)
        st.error(str(exc))
        st.info(
            "자주 나는 원인: CUDA GPU 미감지, ffmpeg PATH 누락, large-v3 GPU 메모리 부족, 첫 실행 모델 다운로드 실패. "
            "자주 나는 원인: CUDA GPU 미감지, ffmpeg PATH 누락, large-v3 GPU 메모리 부족, 첫 실행 모델 다운로드 실패."
        )
