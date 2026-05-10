from __future__ import annotations

import re
import textwrap
from pathlib import Path
from typing import Iterable


def srt_time(seconds: float) -> str:
    millis = int(round(seconds * 1000))
    hours = millis // 3_600_000
    millis %= 3_600_000
    minutes = millis // 60_000
    millis %= 60_000
    secs = millis // 1000
    millis %= 1000
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"


def safe_filename(name: str) -> str:
    bad_chars = '<>:"/\\|?*'
    for ch in bad_chars:
        name = name.replace(ch, "_")
    name = re.sub(r"\s+", "_", name.strip())
    return name or "subtitle_output"


def wrap_subtitle(text: str, width: int = 42) -> str:
    text = " ".join((text or "").strip().split())
    if not text:
        return ""

    if re.search(r"[가-힣]", text):
        width = min(width, 32)

    return "\n".join(
        textwrap.wrap(
            text,
            width=width,
            break_long_words=False,
            break_on_hyphens=False,
        )
    )


def write_srt(segments: Iterable[dict], output_path: Path, text_key: str = "text", width: int = 42) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # utf-8-sig: Korean subtitles open better in Windows/Premiere.
    with output_path.open("w", encoding="utf-8-sig", newline="\n") as f:
        for i, seg in enumerate(segments, start=1):
            text = wrap_subtitle(str(seg.get(text_key, "")).strip(), width=width)
            if not text:
                text = "..."

            f.write(f"{i}\n")
            f.write(f"{srt_time(float(seg['start']))} --> {srt_time(float(seg['end']))}\n")
            f.write(f"{text}\n\n")


def normalize_segments(raw_segments: Iterable[dict]) -> list[dict]:
    normalized = []
    for i, seg in enumerate(raw_segments, start=1):
        normalized.append(
            {
                "id": i,
                "start": float(seg["start"]),
                "end": float(seg["end"]),
                "text": str(seg.get("text", "")).strip(),
            }
        )
    return normalized
