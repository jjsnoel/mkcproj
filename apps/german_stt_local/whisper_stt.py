from __future__ import annotations

import shutil
from pathlib import Path
from typing import Callable

import torch
import whisper

from srt_utils import normalize_segments


Progress = Callable[[str], None]


DEFAULT_GERMAN_PROMPT = (
    "Münchner Knabenchor, Munich Boys Choir, Tölzer Knabenchor, Ralf Ludewig, "
    "Knabenchor, Chor, Sopran, Alt, Tenor, Bass, Probe, Konzert, Heidenröslein, "
    "Justus, München, Bayern, Deutschland."
)


def transcribe_video(
    video_path: str | Path,
    whisper_model_name: str = "large-v3",
    language: str = "de",
    prompt: str = "",
    progress: Progress | None = None,
) -> tuple[list[dict], dict]:
    video_path = Path(video_path)

    if not video_path.exists():
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {video_path}")

    if shutil.which("ffmpeg") is None:
        raise RuntimeError(
            "ffmpeg가 설치되어 있지 않거나 PATH에 없습니다. Whisper가 영상에서 음성을 읽으려면 ffmpeg가 필요합니다."
        )

    device = "cuda" if torch.cuda.is_available() else "cpu"
    if progress:
        progress(f"Whisper 모델 로딩 중: {whisper_model_name} / 장치: {device}")

    model = whisper.load_model(whisper_model_name, device=device)

    final_prompt = (prompt or DEFAULT_GERMAN_PROMPT).strip()

    if progress:
        progress("독일어 원문 STT 진행 중... 영상 길이에 따라 시간이 걸릴 수 있어요.")

    result = model.transcribe(
        str(video_path),
        language=language,
        task="transcribe",
        fp16=(device == "cuda"),
        temperature=0,
        beam_size=5,
        condition_on_previous_text=False,
        initial_prompt=final_prompt,
        verbose=False,
    )

    segments = normalize_segments(result.get("segments", []))
    meta = {
        "device": device,
        "cuda_available": torch.cuda.is_available(),
        "gpu_name": torch.cuda.get_device_name(0) if device == "cuda" else "CPU",
        "whisper_model": whisper_model_name,
        "language": language,
        "text": result.get("text", ""),
    }
    return segments, meta
