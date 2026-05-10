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
    translation_model: str = DEFAULT_MODEL,
    prompt: str = "",
    make_english: bool = True,
    make_korean: bool = True,
    korean_mode: str = "direct",
    require_gpu: bool = True,
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
        progress("1/3 독일어 원문 자막 생성 시작")

    de_segments, stt_meta = transcribe_video(
        video_path=video_path,
        whisper_model_name=whisper_model,
        language="de",
        prompt=prompt,
        require_gpu=require_gpu,
        progress=progress,
    )

    de_srt = run_dir / f"{base_name}.{whisper_model}.de.srt"
    write_srt(de_segments, de_srt, width=42)

    en_srt = None
    ko_srt = None
    en_segments = None
    translation_providers: dict[str, str] = {}

    if make_english:
        if progress:
            progress("2/3 영어 번역 자막 생성 시작")

        en_segments, provider = translate_segments_auto(
            de_segments,
            source_lang="de",
            target_lang="en",
            model_name=translation_model,
            batch_size=4,
            require_gpu=require_gpu,
            progress=progress,
        )
        translation_providers["en"] = provider

        en_srt = run_dir / f"{base_name}.{whisper_model}.en.srt"
        write_srt(en_segments, en_srt, width=42)

    if make_korean:
        if progress:
            progress("3/3 한국어 번역 자막 생성 시작")

        if korean_mode == "via_english":
            if en_segments is None:
                en_segments, provider = translate_segments_auto(
                    de_segments,
                    source_lang="de",
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
                de_segments,
                source_lang="de",
                target_lang="ko",
                model_name=translation_model,
                batch_size=4,
                require_gpu=require_gpu,
                progress=progress,
            )
            translation_providers["ko"] = provider

        ko_srt = run_dir / f"{base_name}.{whisper_model}.ko.srt"
        write_srt(ko_segments, ko_srt, width=32)

    meta_path = run_dir / f"{base_name}.run_info.json"
    meta = {
        "video_path": str(video_path),
        "output_dir": str(run_dir),
        "whisper": stt_meta,
        "translation_model": translation_model,
        "translation_providers": translation_providers,
        "korean_mode": korean_mode,
        "segments_count": len(de_segments),
        "outputs": {
            "de_srt": str(de_srt),
            "en_srt": str(en_srt) if en_srt else None,
            "ko_srt": str(ko_srt) if ko_srt else None,
            "run_info": str(meta_path),
        },
    }

    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    if progress:
        progress("완료! SRT 파일 생성이 끝났어요.")

    return meta
