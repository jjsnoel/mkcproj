from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Callable

import torch
import whisper

from srt_utils import normalize_segments


Progress = Callable[[str], None]


DEFAULT_RECOGNITION_PROMPT = (
    "Muenchner Knabenchor, Munich Boys Choir, Toelzer Knabenchor, Ralf Ludewig, "
    "Knabenchor, Chor, Sopran, Alt, Tenor, Bass, Probe, Konzert, Heidenroeslein, "
    "Justus, Muenchen, Bayern, Deutschland, Latin, English."
)
DEFAULT_OPENAI_STT_MODEL = "gpt-4o-transcribe"
DEFAULT_TIMESTAMP_MODEL = "large-v3"
OPENAI_TIMESTAMP_MODELS = {"whisper-1", "gpt-4o-transcribe-diarize"}


def transcribe_video(
    video_path: str | Path,
    whisper_model_name: str = "large-v3",
    language: str | None = None,
    prompt: str = "",
    require_gpu: bool = True,
    stt_provider: str = "auto",
    openai_model_name: str | None = None,
    timestamp_model_name: str | None = None,
    progress: Progress | None = None,
) -> tuple[list[dict], dict]:
    video_path = Path(video_path)

    if not video_path.exists():
        raise FileNotFoundError(f"File not found: {video_path}")

    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg is required for STT but was not found on PATH.")

    source_language = _normalize_language(language)
    provider = (stt_provider or "auto").strip().lower()
    if provider not in {"auto", "openai", "local"}:
        provider = "auto"

    if provider in {"auto", "openai"} and _openai_api_key():
        try:
            return _transcribe_with_openai(
                video_path=video_path,
                openai_model_name=openai_model_name or _env("OPENAI_STT_MODEL", DEFAULT_OPENAI_STT_MODEL),
                timestamp_model_name=timestamp_model_name or whisper_model_name,
                language=source_language,
                prompt=prompt,
                require_gpu=require_gpu,
                progress=progress,
            )
        except Exception as exc:
            if provider == "openai":
                raise
            if progress:
                progress(f"OpenAI STT failed; falling back to local Whisper: {exc}")
    elif provider == "openai":
        raise RuntimeError("OPENAI_API_KEY is not set, so OpenAI STT cannot run.")

    return _transcribe_with_local_whisper(
        video_path=video_path,
        whisper_model_name=whisper_model_name,
        language=source_language,
        prompt=prompt,
        require_gpu=require_gpu,
        progress=progress,
    )


def _transcribe_with_local_whisper(
    video_path: Path,
    whisper_model_name: str,
    language: str | None,
    prompt: str,
    require_gpu: bool,
    progress: Progress | None,
) -> tuple[list[dict], dict]:
    cuda_available = torch.cuda.is_available()
    if require_gpu and not cuda_available:
        raise RuntimeError("CUDA GPU is required for local Whisper in this app.")

    device = "cuda" if cuda_available else "cpu"
    if progress:
        progress(f"Loading local Whisper model: {whisper_model_name} / {device}")

    model = whisper.load_model(whisper_model_name, device=device)
    final_prompt = (prompt or DEFAULT_RECOGNITION_PROMPT).strip()

    kwargs = {
        "task": "transcribe",
        "fp16": (device == "cuda"),
        "temperature": 0,
        "beam_size": 5,
        "condition_on_previous_text": False,
        "initial_prompt": final_prompt,
        "verbose": False,
    }
    if language:
        kwargs["language"] = language

    if progress:
        progress("Running local Whisper for timestamps/source fallback.")

    result = model.transcribe(str(video_path), **kwargs)
    detected_language = result.get("language") or language or "unknown"
    segments = normalize_segments(result.get("segments", []))
    meta = {
        "provider": "local",
        "device": device,
        "cuda_available": torch.cuda.is_available(),
        "gpu_name": torch.cuda.get_device_name(0) if device == "cuda" else "CPU",
        "whisper_model": whisper_model_name,
        "language": detected_language,
        "text": result.get("text", ""),
        "source_text": result.get("text", ""),
        "timestamp_segments": segments,
        "merged_segments": segments,
    }
    return segments, meta


def _transcribe_with_openai(
    video_path: Path,
    openai_model_name: str,
    timestamp_model_name: str,
    language: str | None,
    prompt: str,
    require_gpu: bool,
    progress: Progress | None,
) -> tuple[list[dict], dict]:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("The openai package is not installed. Reinstall requirements_video_stt.txt.") from exc

    model_name = (openai_model_name or DEFAULT_OPENAI_STT_MODEL).strip()
    final_prompt = (prompt or DEFAULT_RECOGNITION_PROMPT).strip()
    client = OpenAI(api_key=_openai_api_key())
    chunk_seconds = _env_int("OPENAI_STT_CHUNK_SECONDS", 600)

    if progress:
        progress(f"Running OpenAI source transcription: {model_name}")

    openai_segments, source_text = _transcribe_openai_chunks(
        client=client,
        video_path=video_path,
        model_name=model_name,
        language=language,
        prompt=final_prompt,
        chunk_seconds=chunk_seconds,
        progress=progress,
    )

    timestamp_segments: list[dict]
    timestamp_meta: dict
    if model_name in OPENAI_TIMESTAMP_MODELS and openai_segments:
        timestamp_segments = normalize_segments(openai_segments)
        timestamp_meta = {"provider": "openai", "whisper_model": model_name, "language": language or "unknown"}
        merged_segments = timestamp_segments
    else:
        if progress:
            progress(f"Running free local Whisper for subtitle timing: {timestamp_model_name}")
        timestamp_segments, timestamp_meta = _transcribe_with_local_whisper(
            video_path=video_path,
            whisper_model_name=timestamp_model_name,
            language=language,
            prompt=prompt,
            require_gpu=require_gpu,
            progress=progress,
        )
        merged_segments = _apply_text_to_timestamps(source_text, timestamp_segments)

    detected_language = language or timestamp_meta.get("language") or "unknown"
    meta = {
        "provider": "openai",
        "device": "openai-api",
        "cuda_available": torch.cuda.is_available(),
        "gpu_name": "OpenAI API",
        "whisper_model": model_name,
        "openai_model": model_name,
        "timestamp_source": timestamp_meta.get("whisper_model", timestamp_model_name),
        "language": detected_language,
        "text": source_text,
        "source_text": source_text,
        "timestamp_segments": timestamp_segments,
        "merged_segments": merged_segments,
    }
    return normalize_segments(merged_segments), meta


def _transcribe_openai_chunks(
    client,
    video_path: Path,
    model_name: str,
    language: str | None,
    prompt: str,
    chunk_seconds: int,
    progress: Progress | None,
) -> tuple[list[dict], str]:
    with tempfile.TemporaryDirectory(prefix="munich_openai_stt_") as tmp:
        tmp_dir = Path(tmp)
        chunks = _make_audio_chunks(video_path, tmp_dir, chunk_seconds)
        all_segments: list[dict] = []
        transcript_text: list[str] = []
        offset = 0.0

        for index, chunk_path in enumerate(chunks, start=1):
            if progress:
                progress(f"Uploading OpenAI STT chunk {index}/{len(chunks)}")

            chunk_duration = _probe_duration_seconds(chunk_path)
            data = _openai_transcribe_chunk(
                client=client,
                chunk_path=chunk_path,
                model_name=model_name,
                language=language,
                prompt=prompt,
            )
            chunk_segments, text = _segments_from_openai_response(data, offset)
            all_segments.extend(chunk_segments)
            if text:
                transcript_text.append(text)
            offset += chunk_duration

    return all_segments, "\n".join(transcript_text).strip()


def _openai_transcribe_chunk(client, chunk_path: Path, model_name: str, language: str | None, prompt: str):
    kwargs = {"model": model_name, "file": None}
    if language:
        kwargs["language"] = language
    if prompt:
        kwargs["prompt"] = prompt
    if model_name == "whisper-1":
        kwargs["response_format"] = "verbose_json"
        kwargs["timestamp_granularities"] = ["segment"]
    elif model_name == "gpt-4o-transcribe-diarize":
        kwargs["response_format"] = "diarized_json"
    else:
        kwargs["response_format"] = "json"

    with chunk_path.open("rb") as audio_file:
        kwargs["file"] = audio_file
        return client.audio.transcriptions.create(**kwargs)


def _apply_text_to_timestamps(text: str, timestamp_segments: list[dict]) -> list[dict]:
    clean_text = " ".join((text or "").split())
    if not clean_text or not timestamp_segments:
        return timestamp_segments

    pieces = _split_text_by_segment_durations(clean_text, timestamp_segments)
    aligned = []
    for segment, piece in zip(timestamp_segments, pieces, strict=False):
        aligned.append(
            {
                "start": float(segment["start"]),
                "end": float(segment["end"]),
                "text": piece or segment.get("text", ""),
            }
        )
    return aligned


def _split_text_by_segment_durations(text: str, timestamp_segments: list[dict]) -> list[str]:
    words = text.split()
    count = len(timestamp_segments)
    if count <= 1:
        return [" ".join(words)]
    if len(words) <= count:
        return words + [""] * (count - len(words))

    durations = [max(0.1, float(seg["end"]) - float(seg["start"])) for seg in timestamp_segments]
    total_duration = sum(durations)
    pieces = []
    cursor = 0
    for index, duration in enumerate(durations):
        remaining_segments = count - index
        remaining_words = len(words) - cursor
        if remaining_segments == 1:
            take = remaining_words
        else:
            take = max(1, round(len(words) * (duration / total_duration)))
            take = min(take, remaining_words - (remaining_segments - 1))
        pieces.append(" ".join(words[cursor : cursor + take]))
        cursor += take
    return pieces


def _make_audio_chunks(video_path: Path, tmp_dir: Path, chunk_seconds: int) -> list[Path]:
    chunk_pattern = tmp_dir / "chunk_%03d.mp3"
    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-b:a",
        "64k",
        "-f",
        "segment",
        "-segment_time",
        str(chunk_seconds),
        "-reset_timestamps",
        "1",
        str(chunk_pattern),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"ffmpeg audio chunk creation failed: {completed.stderr[-1000:]}")

    chunks = sorted(tmp_dir.glob("chunk_*.mp3"))
    if not chunks:
        raise RuntimeError("No audio chunks were created for OpenAI STT.")

    for chunk in chunks:
        if chunk.stat().st_size >= 25 * 1024 * 1024:
            raise RuntimeError(
                f"OpenAI upload limit exceeded by chunk {chunk.name}. "
                "Set OPENAI_STT_CHUNK_SECONDS to a smaller value."
            )
    return chunks


def _probe_duration_seconds(path: Path) -> float:
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
    if completed.returncode != 0:
        return 0.0
    try:
        return float(completed.stdout.strip())
    except ValueError:
        return 0.0


def _segments_from_openai_response(response, offset: float) -> tuple[list[dict], str]:
    data = _response_to_dict(response)
    raw_segments = data.get("segments") or data.get("speaker_segments") or []
    segments: list[dict] = []

    for item in raw_segments:
        start = _float_value(item.get("start") or item.get("start_time"), 0.0)
        end = _float_value(item.get("end") or item.get("end_time"), start)
        text = (item.get("text") or item.get("transcript") or "").strip()
        speaker = (item.get("speaker") or "").strip()
        if speaker and text:
            text = f"{speaker}: {text}"
        if text:
            segments.append({"start": start + offset, "end": end + offset, "text": text})

    return segments, (data.get("text") or "").strip()


def _response_to_dict(response) -> dict:
    if isinstance(response, dict):
        return response
    if hasattr(response, "model_dump"):
        return response.model_dump()
    if hasattr(response, "dict"):
        return response.dict()
    return {"text": getattr(response, "text", "")}


def _float_value(value, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def openai_api_key_configured() -> bool:
    return bool(_openai_api_key())


def _openai_api_key() -> str:
    return _clean_openai_api_key(_env("OPENAI_API_KEY", ""))


def _env(name: str, default: str = "") -> str:
    _load_env_files()
    return os.environ.get(name, default).strip()


def _env_int(name: str, default: int) -> int:
    try:
        return int(_env(name, str(default)))
    except ValueError:
        return default


def _normalize_language(language: str | None) -> str | None:
    if not language:
        return None
    value = language.strip().lower()
    if value in {"auto", "detect", "unknown"}:
        return None
    return value


def _load_env_files() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        load_dotenv = None

    root = Path(__file__).resolve().parents[2]
    for env_path in (root / ".env", Path(__file__).resolve().parent / ".env"):
        if load_dotenv is not None:
            load_dotenv(env_path)
        _load_env_file_utf8_sig(env_path)


def _load_env_file_utf8_sig(env_path: Path) -> None:
    if not env_path.exists():
        return
    try:
        lines = env_path.read_text(encoding="utf-8-sig").splitlines()
    except OSError:
        return

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        name, value = stripped.split("=", 1)
        name = name.strip().lstrip("\ufeff")
        value = value.strip().strip('"').strip("'")
        if name.startswith("OPENAI_") or name == "LOCAL_WHISPER_MODEL":
            os.environ[name] = value
        elif name and name not in os.environ:
            os.environ[name] = value


def _clean_openai_api_key(value: str) -> str:
    key = (value or "").strip().strip('"').strip("'")
    for marker in ("OPENAI_STT_MODEL=", "OPENAI_STT_CHUNK_SECONDS=", "LOCAL_WHISPER_MODEL=", "LOCAL_TIMESTAMP_MODEL="):
        if marker in key:
            key = key.split(marker, 1)[0]
    return key.strip()
