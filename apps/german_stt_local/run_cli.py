from __future__ import annotations

import argparse

from local_translator import DEFAULT_MODEL
from pipeline import run_full_pipeline


def main():
    parser = argparse.ArgumentParser(description="Local German STT + English/Korean SRT translator")
    parser.add_argument("video", help="영상 또는 음성 파일 경로")
    parser.add_argument("--model", default="large-v3", choices=["large-v3"])
    parser.add_argument("--stt-provider", default="auto", choices=["auto", "openai", "local"])
    parser.add_argument(
        "--openai-stt-model",
        default="gpt-4o-transcribe",
        choices=["gpt-4o-transcribe", "gpt-4o-mini-transcribe", "whisper-1", "gpt-4o-transcribe-diarize"],
    )
    parser.add_argument("--source-language", default="auto", choices=["auto", "de", "en", "la", "ko"])
    parser.add_argument("--translation-model", default=DEFAULT_MODEL)
    parser.add_argument("--korean-mode", default="direct", choices=["direct", "via_english"])
    parser.add_argument("--output-name", default=None)
    parser.add_argument("--output-dir", default="output_gpu")
    parser.add_argument("--prompt", default="")
    parser.add_argument("--no-en", action="store_true")
    parser.add_argument("--no-ko", action="store_true")
    args = parser.parse_args()

    def log(msg: str):
        print(msg, flush=True)

    result = run_full_pipeline(
        video_path=args.video,
        output_dir=args.output_dir,
        output_name=args.output_name,
        whisper_model=args.model,
        stt_provider=args.stt_provider,
        openai_stt_model=args.openai_stt_model,
        source_language=args.source_language,
        translation_model=args.translation_model,
        prompt=args.prompt,
        make_english=not args.no_en,
        make_korean=not args.no_ko,
        korean_mode=args.korean_mode,
        progress=log,
    )

    print("\n완료:")
    for key, value in result["outputs"].items():
        if value:
            print(f"- {key}: {value}")


if __name__ == "__main__":
    main()
