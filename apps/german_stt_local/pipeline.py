from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Callable

from local_translator import DEFAULT_MODEL, translate_segments_auto
from srt_utils import safe_filename, write_srt
from whisper_stt import transcribe_video


Progress = Callable[[str], None]


def run_full_pipeline(
    video_path: str | Path,
    output_dir: str | Path = "output_gpu",
    output_name: str | None = None,
    whisper_model: str = "large-v3",
    stt_provider: str = "auto",
    openai_stt_model: str = "gpt-4o-transcribe",
    source_language: str = "auto",
    translation_model: str = DEFAULT_MODEL,
    prompt: str = "",
    make_english: bool = True,
    make_korean: bool = True,
    korean_mode: str = "direct",
    require_gpu: bool = True,
    cancel_check: Callable[[], bool] | None = None,
    progress: Progress | None = None,
) -> dict:
    video_path = Path(video_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    base_name = safe_filename(output_name or video_path.stem)
    run_stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = output_dir / f"{base_name}_{run_stamp}"
    run_dir.mkdir(parents=True, exist_ok=True)

    if progress:
        progress("1/4 원문 STT와 타임스탬프 생성 시작")
    _raise_if_cancelled(cancel_check)

    local_model = whisper_model
    source_segments, stt_meta = transcribe_video(
        video_path=video_path,
        whisper_model_name=local_model,
        language=source_language,
        prompt=prompt,
        require_gpu=require_gpu,
        stt_provider=stt_provider,
        openai_model_name=openai_stt_model,
        timestamp_model_name=local_model,
        progress=progress,
    )
    _raise_if_cancelled(cancel_check)

    stt_label = safe_filename(str(stt_meta.get("whisper_model") or whisper_model))
    detected_language = _normalize_source_language(stt_meta.get("language"), fallback=source_language)

    original_txt = run_dir / f"{base_name}.{stt_label}.source_original.txt"
    original_txt.write_text(stt_meta.get("source_text") or stt_meta.get("text") or "", encoding="utf-8")

    timestamp_srt = run_dir / f"{base_name}.{local_model}.timestamp_reference.srt"
    write_srt(stt_meta.get("timestamp_segments") or source_segments, timestamp_srt, width=42)

    source_srt = run_dir / f"{base_name}.{stt_label}.{detected_language}.merged_source.srt"
    write_srt(source_segments, source_srt, width=42)
    _raise_if_cancelled(cancel_check)

    en_srt = None
    ko_srt = None
    en_segments = None
    translation_providers: dict[str, str] = {}
    skipped_translations: list[str] = []
    can_translate_source = detected_language in {"de", "en", "la", "ko"}

    if make_english and detected_language == "en":
        skipped_translations.append("en:same_as_source")
    elif make_english and can_translate_source:
        if progress:
            progress("2/4 영어 번역 SRT 생성 시작")
        _raise_if_cancelled(cancel_check)

        en_segments, provider = translate_segments_auto(
            source_segments,
            source_lang=detected_language,
            target_lang="en",
            model_name=translation_model,
            batch_size=4,
            require_gpu=require_gpu,
            progress=progress,
        )
        translation_providers["en"] = provider

        en_srt = run_dir / f"{base_name}.{stt_label}.en.srt"
        write_srt(en_segments, en_srt, width=42)
        _raise_if_cancelled(cancel_check)
    elif make_english:
        skipped_translations.append(f"en:unsupported_source_{detected_language}")

    if make_korean and detected_language == "ko":
        skipped_translations.append("ko:same_as_source")
    elif make_korean and can_translate_source:
        if progress:
            progress("3/4 한국어 번역 SRT 생성 시작")
        _raise_if_cancelled(cancel_check)

        if korean_mode == "via_english":
            if en_segments is None:
                if detected_language == "en":
                    en_segments = source_segments
                else:
                    en_segments, provider = translate_segments_auto(
                        source_segments,
                        source_lang=detected_language,
                        target_lang="en",
                        model_name=translation_model,
                        batch_size=4,
                        require_gpu=require_gpu,
                        progress=progress,
                    )
                    translation_providers["en"] = provider

            ko_segments, provider = translate_segments_auto(
                en_segments,
                source_lang="en",
                target_lang="ko",
                model_name=translation_model,
                batch_size=4,
                require_gpu=require_gpu,
                progress=progress,
            )
            translation_providers["ko"] = provider
        else:
            ko_segments, provider = translate_segments_auto(
                source_segments,
                source_lang=detected_language,
                target_lang="ko",
                model_name=translation_model,
                batch_size=4,
                require_gpu=require_gpu,
                progress=progress,
            )
            translation_providers["ko"] = provider

        ko_srt = run_dir / f"{base_name}.{stt_label}.ko.srt"
        write_srt(ko_segments, ko_srt, width=32)
        _raise_if_cancelled(cancel_check)
    elif make_korean:
        skipped_translations.append(f"ko:unsupported_source_{detected_language}")

    meta_path = run_dir / f"{base_name}.run_info.json"
    meta = {
        "video_path": str(video_path),
        "output_dir": str(run_dir),
        "stt": _compact_stt_meta(stt_meta),
        "source_language": detected_language,
        "translation_model": translation_model,
        "translation_providers": translation_providers,
        "skipped_translations": skipped_translations,
        "korean_mode": korean_mode,
        "segments_count": len(source_segments),
        "outputs": {
            "original_txt": str(original_txt),
            "timestamp_srt": str(timestamp_srt),
            "source_srt": str(source_srt),
            "de_srt": str(source_srt) if detected_language == "de" else None,
            "en_srt": str(en_srt) if en_srt else None,
            "ko_srt": str(ko_srt) if ko_srt else None,
            "run_info": str(meta_path),
        },
    }

    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    if progress:
        progress("완료! 원문/타임스탬프/합본/번역 파일을 생성했습니다.")

    return meta


def _normalize_source_language(value: object, fallback: str = "auto") -> str:
    language = str(value or "").strip().lower()
    if language in {"de", "en", "la", "ko"}:
        return language
    fallback_value = str(fallback or "").strip().lower()
    if fallback_value in {"de", "en", "la", "ko"}:
        return fallback_value
    return "unknown"


def _compact_stt_meta(stt_meta: dict) -> dict:
    compact = dict(stt_meta)
    compact.pop("timestamp_segments", None)
    compact.pop("merged_segments", None)
    return compact


def _raise_if_cancelled(cancel_check: Callable[[], bool] | None) -> None:
    if cancel_check is not None and cancel_check():
        raise RuntimeError("사용자 요청으로 파이프라인을 중단했습니다.")
