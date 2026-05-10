from __future__ import annotations

from pathlib import Path

import streamlit as st
import torch

from local_translator import DEFAULT_MODEL, deepl_auth_key
from pipeline import run_full_pipeline


st.set_page_config(
    page_title="Munich Local Voice Translator",
    page_icon="STT",
    layout="centered",
)

st.title("Munich Local Voice Translator")
st.caption("독일어 음성/영상에서 독일어 SRT를 만들고, DeepL 우선으로 영어/한국어 SRT를 생성합니다.")

with st.expander("현재 실행 상태", expanded=True):
    cuda_ok = torch.cuda.is_available()
    deepl_ok = bool(deepl_auth_key())
    st.write("CUDA 사용 가능:", cuda_ok)
    st.write("사용 장치:", torch.cuda.get_device_name(0) if cuda_ok else "CPU")
    st.write("DeepL 키:", "설정됨" if deepl_ok else "없음")
    st.write("권장: 정확도 우선 Whisper large-v3 / 안정성 우선 medium")
    if not cuda_ok:
        st.error("CUDA GPU가 잡히지 않아 실행을 막았습니다. CPU fallback은 비활성화되어 있습니다.")

uploaded = st.file_uploader(
    "영상 또는 음성 파일 업로드",
    type=["mp4", "mov", "mkv", "webm", "mp3", "wav", "m4a", "aac"],
)

col1, col2 = st.columns(2)

with col1:
    whisper_model = st.selectbox(
        "Whisper 모델",
        ["large-v3", "medium"],
        index=0,
        help="large-v3가 기본 권장입니다. GPU 메모리 오류가 나면 medium으로 바꾸세요.",
    )

with col2:
    korean_mode = st.selectbox(
        "한국어 번역 방식",
        ["direct", "via_english"],
        index=0,
        format_func=lambda x: "독일어 -> 한국어 직접" if x == "direct" else "독일어 -> 영어 -> 한국어",
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

start = st.button("자막 생성 시작", type="primary", disabled=(uploaded is None or not cuda_ok))

if start and uploaded is not None:
    input_dir = Path("input") / "uploaded"
    input_dir.mkdir(parents=True, exist_ok=True)

    save_path = input_dir / uploaded.name
    save_path.write_bytes(uploaded.getbuffer())

    status = st.status("로컬 파이프라인 실행 중...", expanded=True)

    def log(message: str):
        status.write(message)

    try:
        result = run_full_pipeline(
            video_path=save_path,
            output_dir="output_gpu",
            output_name=output_name.strip() or None,
            whisper_model=whisper_model,
            translation_model=translation_model.strip() or DEFAULT_MODEL,
            prompt=prompt,
            make_english=make_english,
            make_korean=make_korean,
            korean_mode=korean_mode,
            require_gpu=True,
            progress=log,
        )

        status.update(label="완료!", state="complete", expanded=True)

        st.success("자막 파일 생성 완료!")

        outputs = result["outputs"]
        st.write("저장 폴더:")
        st.code(result["output_dir"])
        st.write("번역 엔진:")
        st.json(result.get("translation_providers", {}))

        for label, key in [
            ("독일어 원문 SRT", "de_srt"),
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
            "GPU 메모리 오류면 Whisper 모델을 medium으로 바꿔 다시 해보세요."
        )
