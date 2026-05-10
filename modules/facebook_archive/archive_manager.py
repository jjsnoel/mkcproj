from __future__ import annotations

import argparse
import csv
import hashlib
import os
import re
import shutil
import sys
import unicodedata
from datetime import datetime
from pathlib import Path


ARCHIVE_ROOT_NAME = "Muenchner_Knabenchor_Archive"
SOURCE_NAME = "Facebook - Münchner Knabenchor"

YEARS = range(2014, 2027)

SUPPORTED_THEMES = [
    "01_Profile_Best",
    "02_Concert",
    "03_Rehearsal",
    "04_Tour_Travel",
    "05_Church_Cathedral",
    "06_Backstage_Daily",
    "07_Posters_Programs",
    "08_Press_Article",
    "09_Collaboration",
    "10_Unknown",
    "11_Reels_Sets/01_angels_on_stage",
    "11_Reels_Sets/02_before_the_concert",
    "11_Reels_Sets/03_church_music_mood",
    "11_Reels_Sets/04_tour_memories",
    "11_Reels_Sets/05_then_and_now",
    "11_Reels_Sets/06_christmas_concert",
]

IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
    ".bmp",
    ".tif",
    ".tiff",
    ".heic",
    ".heif",
}

MONTH_ALIASES = {
    "jan": 1,
    "january": 1,
    "januar": 1,
    "janvier": 1,
    "enero": 1,
    "gennaio": 1,
    "janeiro": 1,
    "feb": 2,
    "february": 2,
    "februar": 2,
    "fevrier": 2,
    "février": 2,
    "febrero": 2,
    "febbraio": 2,
    "fevereiro": 2,
    "mar": 3,
    "march": 3,
    "maerz": 3,
    "märz": 3,
    "mars": 3,
    "marzo": 3,
    "marco": 3,
    "março": 3,
    "apr": 4,
    "april": 4,
    "avril": 4,
    "abril": 4,
    "aprile": 4,
    "may": 5,
    "mai": 5,
    "mayo": 5,
    "maggio": 5,
    "maio": 5,
    "jun": 6,
    "june": 6,
    "juni": 6,
    "juin": 6,
    "junio": 6,
    "giugno": 6,
    "junho": 6,
    "jul": 7,
    "july": 7,
    "juli": 7,
    "juillet": 7,
    "julio": 7,
    "luglio": 7,
    "julho": 7,
    "aug": 8,
    "august": 8,
    "aout": 8,
    "août": 8,
    "agosto": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "septembre": 9,
    "septiembre": 9,
    "settembre": 9,
    "setembro": 9,
    "oct": 10,
    "october": 10,
    "okt": 10,
    "oktober": 10,
    "octobre": 10,
    "octubre": 10,
    "ottobre": 10,
    "outubro": 10,
    "nov": 11,
    "november": 11,
    "novembre": 11,
    "noviembre": 11,
    "novembro": 11,
    "dec": 12,
    "december": 12,
    "dez": 12,
    "dezember": 12,
    "decembre": 12,
    "décembre": 12,
    "diciembre": 12,
    "dicembre": 12,
    "dezembro": 12,
}

MASTER_HEADERS = [
    "date",
    "year",
    "post_folder",
    "post_title",
    "source",
    "source_url",
    "image_count",
    "category",
    "event",
    "location",
    "mood",
    "reels_usable",
    "caption_summary",
    "original_caption_path",
    "korean_translation_path",
    "notes",
]

CURATED_HEADERS = [
    "theme",
    "curated_file",
    "original_file",
    "post_folder",
    "date",
    "category",
    "mood",
    "reels_use_case",
    "notes",
]

DUPLICATE_HEADERS = [
    "duplicate_group",
    "sha256",
    "file_size_bytes",
    "file_path",
    "duplicate_count",
    "likely_original",
]

REEL_IDEA_HEADERS = [
    "idea_title",
    "theme",
    "source_post_folder",
    "original_file",
    "caption_note",
    "mood",
    "status",
    "notes",
]

README_TEXT = """# Muenchner Knabenchor Facebook Archive Manager

This is a local Windows-friendly archive helper for photos and captions you saved manually.

It does not scrape Facebook, does not use Meta or Facebook APIs, and does not bypass permissions. It only organizes files that already exist on your computer.

## Requirements

- Windows 11
- PowerShell
- Python 3.11 or newer recommended
- No external Python packages are required

Check Python:

```powershell
python --version
```

If Windows says `python` is not recognized, try:

```powershell
py --version
```

If neither command works, install Python from python.org and check the box that adds Python to PATH.

## First Setup

From the folder that contains these scripts, run:

```powershell
python setup_archive.py
```

This creates:

```text
Muenchner_Knabenchor_Archive/
  00_INBOX/
  01_ORIGINAL_BY_YEAR/
  02_CURATED_BY_THEME/
  03_INDEX/
```

It is safe to run setup more than once. Existing files are not deleted.

## Safe Manual Workflow

1. Manually save Facebook photos yourself.
2. Manually copy the post caption into a `.txt` file.
3. Put unsorted images in:

```text
Muenchner_Knabenchor_Archive\\00_INBOX\\images
```

4. Put caption text files in:

```text
Muenchner_Knabenchor_Archive\\00_INBOX\\captions
```

5. Use `new-post` to copy them into the source-of-truth archive.

The `01_ORIGINAL_BY_YEAR` folder is the source-of-truth archive. Curated theme folders contain copies or hardlinks only. The tool never moves or deletes original images.

## PowerShell Examples

Create the archive structure:

```powershell
python setup_archive.py
```

Create a new archived post:

```powershell
python archive_manager.py new-post --date 2024-12-15 --title "Christmas Concert" --url "https://www.facebook.com/example" --images ".\\00_INBOX\\images" --caption ".\\00_INBOX\\captions\\caption.txt"
```

Curate one original image into a theme folder:

```powershell
python archive_manager.py curate --original ".\\01_ORIGINAL_BY_YEAR\\2024\\2024-12-15_post_001_christmas_concert\\images\\001.jpg" --theme "02_Concert" --use-case "christmas_reel" --mode copy
```

Find exact duplicate image files:

```powershell
python archive_manager.py dedupe
```

Preview inbox files that can be deleted after archiving:

```powershell
python archive_manager.py clear-inbox --dry-run
```

Delete inbox files after archiving:

```powershell
python archive_manager.py clear-inbox --yes
```

Rebuild the master CSV index from existing post folders:

```powershell
python archive_manager.py rebuild-index
```

List archived posts:

```powershell
python archive_manager.py list-posts
```

The examples above use short paths like `.\\00_INBOX\\images`. The tool checks inside `Muenchner_Knabenchor_Archive` automatically, so you can run these commands from the folder that contains `archive_manager.py`.

## Interactive Mode

If you forget an argument, the tool asks for it:

```powershell
python archive_manager.py new-post
```

You can press Enter for optional fields like URL, event, location, mood, and notes.

## Supported Themes

Use one of these values with `--theme`:

```text
01_Profile_Best
02_Concert
03_Rehearsal
04_Tour_Travel
05_Church_Cathedral
06_Backstage_Daily
07_Posters_Programs
08_Press_Article
09_Collaboration
10_Unknown
11_Reels_Sets/01_angels_on_stage
11_Reels_Sets/02_before_the_concert
11_Reels_Sets/03_church_music_mood
11_Reels_Sets/04_tour_memories
11_Reels_Sets/05_then_and_now
11_Reels_Sets/06_christmas_concert
```

## Notes

- `new-post` copies images into `01_ORIGINAL_BY_YEAR`.
- `curate` copies or hardlinks images into `02_CURATED_BY_THEME`.
- `clear-inbox` deletes files from `00_INBOX` only. Use `--dry-run` to preview first.
- `dedupe` reports exact duplicates only. It does not delete anything.
- `rebuild-index` rewrites `03_INDEX\\master_index.csv` from the folders on disk. It does not delete files.
- Use quotes around Windows paths that contain spaces.
"""


class ArchiveError(Exception):
    """Raised for clear user-facing archive errors."""


CAPTION_TRANSLATION_PENDING_MARKER = "[자동 번역 미실행]"


def script_dir() -> Path:
    return Path(__file__).resolve().parent


def default_archive_root() -> Path:
    cwd = Path.cwd()
    if (cwd / "00_INBOX").exists() and (cwd / "01_ORIGINAL_BY_YEAR").exists():
        return cwd
    if cwd.name == ARCHIVE_ROOT_NAME:
        return cwd
    return cwd / ARCHIVE_ROOT_NAME


def resolve_archive_root(value: str | None = None) -> Path:
    if value:
        return Path(value).expanduser().resolve()
    return default_archive_root().resolve()


def is_relative_to(path: Path, base: Path) -> bool:
    try:
        path.resolve().relative_to(base.resolve())
        return True
    except ValueError:
        return False


def relative_to_archive(path: Path, archive_root: Path) -> str:
    try:
        return str(path.resolve().relative_to(archive_root.resolve()))
    except ValueError:
        return str(path.resolve())


def clean_user_path(raw: str) -> str:
    return raw.strip().strip('"').strip("'")


def resolve_user_path(raw: str, archive_root: Path, must_exist: bool = True) -> Path:
    cleaned = clean_user_path(raw)
    if not cleaned:
        raise ArchiveError("A path was required, but the value was empty.")

    supplied = Path(cleaned).expanduser()
    candidates: list[Path]
    if supplied.is_absolute():
        candidates = [supplied]
    else:
        candidates = [Path.cwd() / supplied, archive_root / supplied]

    for candidate in candidates:
        if candidate.exists() or not must_exist:
            return candidate.resolve()

    checked = "\n".join(f"  - {candidate}" for candidate in candidates)
    raise ArchiveError(f"Path not found: {raw}\nChecked:\n{checked}")


def safe_filename_part(value: str, fallback: str = "untitled", max_length: int = 60) -> str:
    # Convert accents such as Muenchen/Munchen-like source text into ASCII-safe slugs.
    normalized = unicodedata.normalize("NFKD", value or "")
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    ascii_text = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', " ", ascii_text)
    ascii_text = re.sub(r"[^A-Za-z0-9]+", "_", ascii_text.lower())
    ascii_text = re.sub(r"_+", "_", ascii_text).strip("._ ")

    if not ascii_text:
        ascii_text = fallback

    ascii_text = ascii_text[:max_length].strip("_")
    if not ascii_text:
        ascii_text = fallback

    reserved = {
        "con",
        "prn",
        "aux",
        "nul",
        *(f"com{i}" for i in range(1, 10)),
        *(f"lpt{i}" for i in range(1, 10)),
    }
    if ascii_text.casefold() in reserved:
        ascii_text = f"{ascii_text}_file"
    return ascii_text


def natural_key(path: Path) -> list[object]:
    parts = re.split(r"(\d+)", path.name.casefold())
    return [int(part) if part.isdigit() else part for part in parts]


def _valid_date(year: int, month: int, day: int):
    if year < min(YEARS) or year > max(YEARS):
        return None
    try:
        return datetime(year, month, day).date()
    except ValueError:
        return None


def _normalize_date_text(date_text: str) -> str:
    normalized = unicodedata.normalize("NFKC", date_text).strip().lower()
    normalized = normalized.replace(",", " ")
    normalized = re.sub(r"(\d+)(st|nd|rd|th)\b", r"\1", normalized)
    normalized = re.sub(r"\b(\d{1,2})\s*(일|월|년)\b", r"\1 \2", normalized)
    normalized = re.sub(r"([가-힣])", r" \1 ", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def _ascii_fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def _month_number(token: str) -> int | None:
    compact = token.rstrip(".")
    return MONTH_ALIASES.get(compact) or MONTH_ALIASES.get(_ascii_fold(compact))


def _parse_numeric_date(normalized: str):
    numbers = [int(value) for value in re.findall(r"\d+", normalized)]
    if len(numbers) < 3:
        return None

    first, second, third = numbers[:3]

    if first >= 1000:
        return _valid_date(first, second, third)

    if third >= 1000:
        year = third
        if first > 12 and second <= 12:
            return _valid_date(year, second, first)
        if second > 12 and first <= 12:
            return _valid_date(year, first, second)

        month_first = _valid_date(year, first, second)
        day_first = _valid_date(year, second, first)
        if month_first:
            return month_first
        return day_first

    return None


def _parse_named_month_date(normalized: str):
    tokens = re.findall(r"[^\W\d_]+|\d+", normalized, flags=re.UNICODE)
    month_index = None
    month = None

    for index, token in enumerate(tokens):
        month_candidate = _month_number(token)
        if month_candidate:
            month_index = index
            month = month_candidate
            break

    if month_index is None or month is None:
        return None

    numeric_tokens = [(index, int(token)) for index, token in enumerate(tokens) if token.isdigit()]
    years = [(index, value) for index, value in numeric_tokens if value >= 1000]
    if not years:
        return None

    year_index, year = years[0]
    day_candidates = [
        value
        for index, value in numeric_tokens
        if index != year_index and 1 <= value <= 31
    ]
    if not day_candidates:
        return None

    before_month = [
        value
        for index, value in numeric_tokens
        if index < month_index and index != year_index and 1 <= value <= 31
    ]
    after_month = [
        value
        for index, value in numeric_tokens
        if index > month_index and index != year_index and 1 <= value <= 31
    ]
    day = before_month[-1] if before_month else after_month[0] if after_month else day_candidates[0]
    return _valid_date(year, month, day)


def parse_date(date_text: str):
    normalized = _normalize_date_text(date_text)
    if not normalized:
        raise ArchiveError("게시일을 입력하세요.")

    parsed = _parse_named_month_date(normalized) or _parse_numeric_date(normalized)
    if parsed:
        return parsed

    raise ArchiveError(
        "게시일을 이해하지 못했습니다. 예: 2024-12-15, 2024년 12월 15일, "
        "Dec 15 2024, 15 December 2024, 15.12.2024"
    )


def ensure_csv(path: Path, headers: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.stat().st_size > 0:
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)


def write_csv(path: Path, headers: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow({header: row.get(header, "") for header in headers})


def append_csv_row(path: Path, headers: list[str], row: dict[str, object]) -> None:
    ensure_csv(path, headers)
    with path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writerow({header: row.get(header, "") for header in headers})


def init_archive(archive_root: str | Path | None = None, create_readme: bool = True) -> Path:
    root = Path(archive_root).expanduser().resolve() if archive_root else default_archive_root()
    root.mkdir(parents=True, exist_ok=True)

    (root / "00_INBOX" / "images").mkdir(parents=True, exist_ok=True)
    (root / "00_INBOX" / "captions").mkdir(parents=True, exist_ok=True)

    for year in YEARS:
        (root / "01_ORIGINAL_BY_YEAR" / str(year)).mkdir(parents=True, exist_ok=True)

    for theme in SUPPORTED_THEMES:
        (root / "02_CURATED_BY_THEME" / Path(*theme.split("/"))).mkdir(parents=True, exist_ok=True)

    index_dir = root / "03_INDEX"
    index_dir.mkdir(parents=True, exist_ok=True)
    ensure_csv(index_dir / "master_index.csv", MASTER_HEADERS)
    ensure_csv(index_dir / "curated_index.csv", CURATED_HEADERS)
    ensure_csv(index_dir / "duplicate_report.csv", DUPLICATE_HEADERS)
    ensure_csv(index_dir / "reel_ideas.csv", REEL_IDEA_HEADERS)

    if create_readme:
        readme_path = script_dir() / "README.md"
        if not readme_path.exists():
            readme_path.write_text(README_TEXT, encoding="utf-8")

    return root.resolve()


def read_text_safely(path: Path) -> str:
    if not path.exists():
        return ""
    for encoding in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def caption_summary(text: str, max_chars: int = 160) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    if len(compact) <= max_chars:
        return compact
    return compact[: max_chars - 3].rstrip() + "..."


def translate_caption_to_korean(text: str, source_lang: str = "de") -> str:
    compact = text.strip()
    if not compact:
        return ""

    if re.search(r"[가-힣]", compact) and source_lang == "ko":
        return compact

    source_lang = (source_lang or "de").strip().lower()
    if source_lang == "ko":
        return compact
    if source_lang not in {"de", "en"}:
        raise ArchiveError(f"Unsupported caption source language for Korean translation: {source_lang}")

    toolkit_root = script_dir().parents[1]
    translator_dir = toolkit_root / "apps" / "german_stt_local"
    if str(translator_dir) not in sys.path:
        sys.path.insert(0, str(translator_dir))

    try:
        from local_translator import DEFAULT_MODEL, LocalNLLBTranslator  # type: ignore
    except Exception as exc:
        return (
            f"{CAPTION_TRANSLATION_PENDING_MARKER}\n"
            "캡션 한국어 번역 모듈을 불러오지 못했습니다. "
            "먼저 SETUP_VIDEO_STT_ONCE.bat를 실행한 뒤 대시보드에서 '빈 한국어 캡션 다시 번역'을 눌러주세요.\n\n"
            f"원문:\n{compact}"
        )

    try:
        translator = LocalNLLBTranslator(model_name=DEFAULT_MODEL)
        translated = translator.translate_texts(
            [compact],
            source_lang=source_lang,
            target_lang="ko",
            batch_size=1,
        )[0]
    except Exception as exc:
        return (
            f"{CAPTION_TRANSLATION_PENDING_MARKER}\n"
            f"캡션 한국어 번역에 실패했습니다: {exc}\n\n"
            f"원문:\n{compact}"
        )

    return translated.strip()


def fill_missing_korean_captions(archive_root: str | Path, source_lang: str = "de") -> list[str]:
    root = Path(archive_root).expanduser().resolve()
    original_root = root / "01_ORIGINAL_BY_YEAR"
    if not original_root.exists():
        return []

    updated: list[str] = []
    for caption_path in sorted(original_root.glob("*/*/caption_original.txt"), key=natural_key):
        caption_text = read_text_safely(caption_path)
        if not caption_text.strip():
            continue

        korean_path = caption_path.with_name("caption_ko.txt")
        current_korean_text = read_text_safely(korean_path) if korean_path.exists() else ""
        if current_korean_text.strip() and CAPTION_TRANSLATION_PENDING_MARKER not in current_korean_text:
            continue

        korean_text = translate_caption_to_korean(caption_text, source_lang)
        korean_path.write_text(korean_text, encoding="utf-8")
        updated.append(relative_to_archive(korean_path, root))

    return updated


def prompt_text(label: str, default: str = "", required: bool = False) -> str:
    while True:
        suffix = f" [{default}]" if default else ""
        value = input(f"{label}{suffix}: ").strip()
        if not value and default:
            value = default
        if value or not required:
            return value
        print("This value is required.")


def prompt_path(label: str, archive_root: Path, default: str = "", required: bool = True) -> Path | None:
    while True:
        value = prompt_text(label, default=default, required=required)
        if not value and not required:
            return None
        try:
            return resolve_user_path(value, archive_root, must_exist=True)
        except ArchiveError as exc:
            print(f"Error: {exc}")


def gather_image_files(images_path: Path) -> list[Path]:
    if images_path.is_file():
        if images_path.suffix.lower() not in IMAGE_EXTENSIONS:
            raise ArchiveError(f"Not a supported image file: {images_path}")
        return [images_path]

    if not images_path.is_dir():
        raise ArchiveError(f"Images path is not a file or folder: {images_path}")

    images = [
        item
        for item in images_path.iterdir()
        if item.is_file() and item.suffix.lower() in IMAGE_EXTENSIONS
    ]
    images.sort(key=natural_key)
    if not images:
        supported = ", ".join(sorted(IMAGE_EXTENSIONS))
        raise ArchiveError(f"No supported image files found in {images_path}. Supported: {supported}")
    return images


def archive_inbox_post(
    *,
    archive_root: str | Path,
    date_text: str,
    title: str,
    source_url: str = "",
    caption_text: str | None = None,
    caption_file: str | Path | None = None,
    category: str = "",
    event: str = "",
    location: str = "",
    mood: str = "",
    reels_usable: str = "maybe",
    caption_source_lang: str = "de",
    clear_inbox: bool = False,
) -> dict[str, object]:
    """Archive the current 00_INBOX/images as one post and return UI-friendly results."""
    root = init_archive(archive_root)
    date_obj = parse_date(date_text)

    inbox_images = root / "00_INBOX" / "images"
    image_sources = gather_image_files(inbox_images)

    safe_title = title.strip()
    if not safe_title:
        safe_title = "No Caption Photo" if len(image_sources) == 1 else "No Caption Photos"

    resolved_caption_file: Path | None = Path(caption_file).expanduser().resolve() if caption_file else None
    if resolved_caption_file and not resolved_caption_file.is_file():
        raise ArchiveError(f"Caption path must be a text file: {resolved_caption_file}")

    if resolved_caption_file:
        final_caption_text = read_text_safely(resolved_caption_file)
    else:
        final_caption_text = caption_text or ""

    has_caption = bool(final_caption_text.strip())
    korean_caption_text = translate_caption_to_korean(final_caption_text, caption_source_lang) if has_caption else ""
    errors: list[str] = []
    if CAPTION_TRANSLATION_PENDING_MARKER in korean_caption_text:
        errors.append("캡션 한국어 번역은 아직 완료되지 않았습니다. SETUP_VIDEO_STT_ONCE.bat 실행 후 재번역 버튼을 사용하세요.")

    year_dir = root / "01_ORIGINAL_BY_YEAR" / str(date_obj.year)
    year_dir.mkdir(parents=True, exist_ok=True)

    slug = safe_filename_part(safe_title, fallback="post", max_length=48)
    post_folder = next_post_folder(year_dir, date_obj.isoformat(), slug)
    images_dest = post_folder / "images"
    images_dest.mkdir(parents=True, exist_ok=True)

    copied_images: list[Path] = []
    for index, source in enumerate(image_sources, start=1):
        destination = images_dest / f"{index:03d}{source.suffix.lower()}"
        if destination.exists():
            raise ArchiveError(f"Destination image already exists, not overwriting: {destination}")
        shutil.copy2(source, destination)
        copied_images.append(destination)

    if has_caption:
        (post_folder / "caption_original.txt").write_text(final_caption_text, encoding="utf-8")
        (post_folder / "caption_ko.txt").write_text(korean_caption_text, encoding="utf-8")

    (post_folder / "source_url.txt").write_text((source_url or "").strip() + "\n", encoding="utf-8")
    (post_folder / "post_info.md").write_text(
        make_post_info(
            date_text=date_obj.isoformat(),
            year=date_obj.year,
            title=safe_title,
            source_url=(source_url or "").strip(),
            post_folder=post_folder,
            archive_root=root,
            image_count=len(copied_images),
            category=category,
            event=event,
            location=location,
            mood=mood,
            reels_usable=reels_usable or "maybe",
            has_caption=has_caption,
        ),
        encoding="utf-8",
    )

    append_csv_row(
        root / "03_INDEX" / "master_index.csv",
        MASTER_HEADERS,
        {
            "date": date_obj.isoformat(),
            "year": date_obj.year,
            "post_folder": relative_to_archive(post_folder, root),
            "post_title": safe_title,
            "source": SOURCE_NAME,
            "source_url": (source_url or "").strip(),
            "image_count": len(copied_images),
            "category": category,
            "event": event,
            "location": location,
            "mood": mood,
            "reels_usable": reels_usable or "maybe",
            "caption_summary": caption_summary(final_caption_text),
            "original_caption_path": relative_to_archive(post_folder / "caption_original.txt", root) if has_caption else "",
            "korean_translation_path": relative_to_archive(post_folder / "caption_ko.txt", root) if has_caption else "",
            "notes": "",
        },
    )

    deleted_inbox_count = delete_inbox_files(root) if clear_inbox else 0
    master_index_path = root / "03_INDEX" / "master_index.csv"
    return {
        "archive_root": str(root),
        "post_folder": str(post_folder),
        "created_post_folder": str(post_folder),
        "post_folder_relative": relative_to_archive(post_folder, root),
        "image_count": len(copied_images),
        "processed_images": len(copied_images),
        "created_post_folder_count": 1,
        "deleted_inbox_count": deleted_inbox_count,
        "deleted_inbox_files": deleted_inbox_count,
        "master_index": str(master_index_path),
        "index_path": str(master_index_path),
        "copied_images": [relative_to_archive(path, root) for path in copied_images],
        "errors": errors,
    }


def next_post_folder(year_dir: Path, date_text: str, slug: str) -> Path:
    pattern = re.compile(rf"^{re.escape(date_text)}_post_(\d{{3}})_.+$")
    numbers: list[int] = []
    if year_dir.exists():
        for child in year_dir.iterdir():
            if child.is_dir():
                match = pattern.match(child.name)
                if match:
                    numbers.append(int(match.group(1)))

    next_number = max(numbers, default=0) + 1
    while True:
        folder = year_dir / f"{date_text}_post_{next_number:03d}_{slug}"
        if not folder.exists():
            return folder
        next_number += 1


def make_post_info(
    *,
    date_text: str,
    year: int,
    title: str,
    source_url: str,
    post_folder: Path,
    archive_root: Path,
    image_count: int,
    category: str,
    event: str,
    location: str,
    mood: str,
    reels_usable: str,
    has_caption: bool,
) -> str:
    relative_folder = relative_to_archive(post_folder, archive_root)
    original_caption_note = "See: caption_original.txt" if has_caption else "No caption file."
    korean_translation_note = "See: caption_ko.txt" if has_caption else "No Korean translation file."
    return f"""# Facebook Post Archive

## Basic Info
- Date: {date_text}
- Year: {year}
- Source: {SOURCE_NAME}
- URL: {source_url}
- Post Folder: {relative_folder}
- Title: {title}
- Image Count: {image_count}

## Original Caption
{original_caption_note}

## Korean Translation
{korean_translation_note}

## Context
- Event: {event}
- Location: {location}
- Category: {category}
- Mood: {mood}
- Reels Usable: {reels_usable}

## Notes
- 
- 

## Reels Ideas
- 
- 
"""


def normalize_theme(theme: str) -> str:
    cleaned = theme.strip().replace("\\", "/").strip("/")
    for allowed in SUPPORTED_THEMES:
        if cleaned.casefold() == allowed.casefold():
            return allowed
    allowed_text = "\n".join(f"  - {item}" for item in SUPPORTED_THEMES)
    raise ArchiveError(f"Unsupported theme: {theme}\nSupported themes:\n{allowed_text}")


def theme_destination(root: Path, theme: str) -> Path:
    return root / "02_CURATED_BY_THEME" / Path(*theme.split("/"))


def extract_date_from_post_folder(folder_name: str) -> str:
    match = re.match(r"^(\d{4}-\d{2}-\d{2})_post_\d{3}_.+$", folder_name)
    return match.group(1) if match else ""


def title_from_post_folder(folder_name: str) -> str:
    match = re.match(r"^\d{4}-\d{2}-\d{2}_post_\d{3}_(.+)$", folder_name)
    slug = match.group(1) if match else folder_name
    return slug.replace("_", " ").strip().title()


def parse_post_info(path: Path) -> dict[str, str]:
    text = read_text_safely(path)
    data: dict[str, str] = {}
    for line in text.splitlines():
        match = re.match(r"^\s*-\s*([^:]+):\s*(.*)$", line)
        if match:
            key = re.sub(r"[^a-z0-9]+", "_", match.group(1).strip().lower()).strip("_")
            data[key] = match.group(2).strip()
    return data


def extract_section_notes(path: Path, heading: str = "Notes") -> str:
    text = read_text_safely(path)
    if not text:
        return ""

    lines = text.splitlines()
    capture = False
    collected: list[str] = []
    target = f"## {heading}".casefold()
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## "):
            if stripped.casefold() == target:
                capture = True
                continue
            if capture:
                break
        elif capture:
            cleaned = re.sub(r"^\s*-\s*", "", line).strip()
            if cleaned:
                collected.append(cleaned)
    return " | ".join(collected)


def list_image_files_recursive(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(
        [item for item in root.rglob("*") if item.is_file() and item.suffix.lower() in IMAGE_EXTENSIONS],
        key=lambda item: str(item).casefold(),
    )


def scan_post_folder(post_folder: Path, archive_root: Path) -> dict[str, object]:
    info_path = post_folder / "post_info.md"
    info = parse_post_info(info_path)

    date_text = info.get("date") or extract_date_from_post_folder(post_folder.name)
    year = info.get("year") or post_folder.parent.name
    title = info.get("title") or title_from_post_folder(post_folder.name)

    source_url_path = post_folder / "source_url.txt"
    source_url = read_text_safely(source_url_path).strip() or info.get("url", "")

    caption_path = post_folder / "caption_original.txt"
    caption_ko_path = post_folder / "caption_ko.txt"
    caption_text = read_text_safely(caption_path)

    images_dir = post_folder / "images"
    image_count = (
        len([item for item in images_dir.iterdir() if item.is_file() and item.suffix.lower() in IMAGE_EXTENSIONS])
        if images_dir.exists()
        else 0
    )

    return {
        "date": date_text,
        "year": year,
        "post_folder": relative_to_archive(post_folder, archive_root),
        "post_title": title,
        "source": info.get("source") or SOURCE_NAME,
        "source_url": source_url,
        "image_count": image_count,
        "category": info.get("category", ""),
        "event": info.get("event", ""),
        "location": info.get("location", ""),
        "mood": info.get("mood", ""),
        "reels_usable": info.get("reels_usable", ""),
        "caption_summary": caption_summary(caption_text),
        "original_caption_path": relative_to_archive(caption_path, archive_root) if caption_path.exists() else "",
        "korean_translation_path": relative_to_archive(caption_ko_path, archive_root) if caption_ko_path.exists() else "",
        "notes": extract_section_notes(info_path),
    }


def scan_posts(archive_root: Path) -> list[dict[str, object]]:
    original_root = archive_root / "01_ORIGINAL_BY_YEAR"
    rows: list[dict[str, object]] = []
    if not original_root.exists():
        return rows

    for year_dir in sorted([item for item in original_root.iterdir() if item.is_dir()], key=natural_key):
        for post_folder in sorted([item for item in year_dir.iterdir() if item.is_dir()], key=natural_key):
            if (post_folder / "images").exists() or (post_folder / "post_info.md").exists():
                rows.append(scan_post_folder(post_folder, archive_root))

    rows.sort(key=lambda row: (str(row.get("date", "")), str(row.get("post_folder", ""))))
    return rows


def command_init(args: argparse.Namespace) -> int:
    archive_root = init_archive(args.archive_root)
    print(f"Archive is ready: {archive_root}")
    print(f"README: {script_dir() / 'README.md'}")
    return 0


def command_new_post(args: argparse.Namespace) -> int:
    archive_root = init_archive(args.archive_root)

    date_text = args.date or prompt_text("Post date", required=True)
    date_obj = parse_date(date_text)
    title = args.title or prompt_text("Post title in English", required=True)
    source_url = args.url if args.url is not None else prompt_text("Source URL", required=False)

    if args.images:
        images_path = resolve_user_path(args.images, archive_root, must_exist=True)
    else:
        images_path = prompt_path("Images file or folder", archive_root, required=True)
        if images_path is None:
            raise ArchiveError("Images path is required.")

    caption_file: Path | None
    if args.caption:
        caption_file = resolve_user_path(args.caption, archive_root, must_exist=True)
        if not caption_file.is_file():
            raise ArchiveError(f"Caption path must be a text file: {caption_file}")
    else:
        caption_file = prompt_path("Caption text file (press Enter to create a blank caption)", archive_root, required=False)
        if caption_file and not caption_file.is_file():
            raise ArchiveError(f"Caption path must be a text file: {caption_file}")

    category = args.category or ""
    event = args.event or ""
    location = args.location or ""
    mood = args.mood or ""
    reels_usable = args.reels_usable or "maybe"
    caption_source_lang = args.caption_lang or "de"

    image_sources = gather_image_files(images_path)
    has_caption = caption_file is not None
    caption_text = read_text_safely(caption_file) if has_caption else ""
    korean_caption_text = translate_caption_to_korean(caption_text, caption_source_lang) if has_caption else ""
    errors: list[str] = []
    if CAPTION_TRANSLATION_PENDING_MARKER in korean_caption_text:
        errors.append("Caption Korean translation is pending. Run SETUP_VIDEO_STT_ONCE.bat, then rerun translation.")

    year_dir = archive_root / "01_ORIGINAL_BY_YEAR" / str(date_obj.year)
    year_dir.mkdir(parents=True, exist_ok=True)

    slug = safe_filename_part(title, fallback="post", max_length=48)
    post_folder = next_post_folder(year_dir, date_obj.isoformat(), slug)
    images_dest = post_folder / "images"
    images_dest.mkdir(parents=True, exist_ok=True)

    copied_images: list[Path] = []
    for index, source in enumerate(image_sources, start=1):
        extension = source.suffix.lower()
        destination = images_dest / f"{index:03d}{extension}"
        shutil.copy2(source, destination)
        copied_images.append(destination)

    if has_caption:
        (post_folder / "caption_original.txt").write_text(caption_text, encoding="utf-8")
        (post_folder / "caption_ko.txt").write_text(korean_caption_text, encoding="utf-8")
    (post_folder / "source_url.txt").write_text((source_url or "").strip() + "\n", encoding="utf-8")
    (post_folder / "post_info.md").write_text(
        make_post_info(
            date_text=date_obj.isoformat(),
            year=date_obj.year,
            title=title,
            source_url=(source_url or "").strip(),
            post_folder=post_folder,
            archive_root=archive_root,
            image_count=len(copied_images),
            category=category,
            event=event,
            location=location,
            mood=mood,
            reels_usable=reels_usable,
            has_caption=has_caption,
        ),
        encoding="utf-8",
    )

    append_csv_row(
        archive_root / "03_INDEX" / "master_index.csv",
        MASTER_HEADERS,
        {
            "date": date_obj.isoformat(),
            "year": date_obj.year,
            "post_folder": relative_to_archive(post_folder, archive_root),
            "post_title": title,
            "source": SOURCE_NAME,
            "source_url": (source_url or "").strip(),
            "image_count": len(copied_images),
            "category": category,
            "event": event,
            "location": location,
            "mood": mood,
            "reels_usable": reels_usable,
            "caption_summary": caption_summary(caption_text),
            "original_caption_path": relative_to_archive(post_folder / "caption_original.txt", archive_root) if has_caption else "",
            "korean_translation_path": relative_to_archive(post_folder / "caption_ko.txt", archive_root) if has_caption else "",
            "notes": "",
        },
    )

    print(f"Created post folder: {post_folder}")
    print(f"Copied {len(copied_images)} image(s).")
    for error in errors:
        print(f"Warning: {error}")
    print("Original source files were not moved or deleted.")
    return 0


def next_curated_file(destination_dir: Path, date_text: str, theme_slug: str, extension: str) -> Path:
    prefix = f"{date_text}_{theme_slug}_" if date_text else f"{theme_slug}_"
    pattern = re.compile(rf"^{re.escape(prefix)}(\d{{3}}){re.escape(extension)}$", re.IGNORECASE)
    numbers: list[int] = []
    if destination_dir.exists():
        for child in destination_dir.iterdir():
            if child.is_file():
                match = pattern.match(child.name)
                if match:
                    numbers.append(int(match.group(1)))

    next_number = max(numbers, default=0) + 1
    while True:
        candidate = destination_dir / f"{prefix}{next_number:03d}{extension}"
        if not candidate.exists():
            return candidate
        next_number += 1


def command_curate(args: argparse.Namespace) -> int:
    archive_root = init_archive(args.archive_root)

    original_arg = args.original or prompt_text("Original image path", required=True)
    original = resolve_user_path(original_arg, archive_root, must_exist=True)
    if not original.is_file() or original.suffix.lower() not in IMAGE_EXTENSIONS:
        raise ArchiveError(f"Original must be a supported image file: {original}")

    original_root = archive_root / "01_ORIGINAL_BY_YEAR"
    if not is_relative_to(original, original_root):
        raise ArchiveError("The original image must be inside 01_ORIGINAL_BY_YEAR. Curated files are never the only copy.")

    if original.parent.name.lower() != "images":
        raise ArchiveError("The original image should be inside a post folder's images directory.")

    theme_value = args.theme or prompt_text("Theme", required=True)
    theme = normalize_theme(theme_value)
    use_case = args.use_case or ""
    notes = args.notes or ""
    mode = args.mode or "copy"

    post_folder = original.parent.parent
    post_date = extract_date_from_post_folder(post_folder.name)
    theme_slug = safe_filename_part(Path(theme).name, fallback="theme", max_length=40)
    extension = original.suffix.lower()

    destination_dir = theme_destination(archive_root, theme)
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = next_curated_file(destination_dir, post_date, theme_slug, extension)

    if mode == "hardlink":
        try:
            os.link(original, destination)
            action = "Hardlinked"
        except OSError as exc:
            shutil.copy2(original, destination)
            action = f"Hardlink failed ({exc}); copied"
    else:
        shutil.copy2(original, destination)
        action = "Copied"

    info = parse_post_info(post_folder / "post_info.md")
    append_csv_row(
        archive_root / "03_INDEX" / "curated_index.csv",
        CURATED_HEADERS,
        {
            "theme": theme,
            "curated_file": relative_to_archive(destination, archive_root),
            "original_file": relative_to_archive(original, archive_root),
            "post_folder": relative_to_archive(post_folder, archive_root),
            "date": post_date or info.get("date", ""),
            "category": info.get("category", ""),
            "mood": info.get("mood", ""),
            "reels_use_case": use_case,
            "notes": notes,
        },
    )

    print(f"{action}: {destination}")
    print("The original image was not moved or deleted.")
    return 0


def command_rebuild_index(args: argparse.Namespace) -> int:
    archive_root = init_archive(args.archive_root)
    rows = scan_posts(archive_root)
    write_csv(archive_root / "03_INDEX" / "master_index.csv", MASTER_HEADERS, rows)
    print(f"Rebuilt master_index.csv with {len(rows)} post(s).")
    print("No image or caption files were deleted.")
    return 0


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def command_dedupe(args: argparse.Namespace) -> int:
    archive_root = init_archive(args.archive_root)
    image_files = list_image_files_recursive(archive_root)

    by_hash: dict[str, list[Path]] = {}
    for image_file in image_files:
        digest = sha256_file(image_file)
        by_hash.setdefault(digest, []).append(image_file)

    duplicate_rows: list[dict[str, object]] = []
    duplicate_group = 1
    original_root = archive_root / "01_ORIGINAL_BY_YEAR"

    for digest, files in sorted(by_hash.items(), key=lambda item: item[0]):
        if len(files) < 2:
            continue

        files.sort(key=lambda item: str(item).casefold())
        for file_path in files:
            duplicate_rows.append(
                {
                    "duplicate_group": duplicate_group,
                    "sha256": digest,
                    "file_size_bytes": file_path.stat().st_size,
                    "file_path": relative_to_archive(file_path, archive_root),
                    "duplicate_count": len(files),
                    "likely_original": "yes" if is_relative_to(file_path, original_root) else "no",
                }
            )
        duplicate_group += 1

    write_csv(archive_root / "03_INDEX" / "duplicate_report.csv", DUPLICATE_HEADERS, duplicate_rows)

    group_count = duplicate_group - 1
    print(f"Scanned {len(image_files)} image file(s).")
    print(f"Found {group_count} duplicate group(s), covering {len(duplicate_rows)} file entries.")
    print(f"Report: {archive_root / '03_INDEX' / 'duplicate_report.csv'}")
    print("No files were deleted.")
    return 0


def command_list_posts(args: argparse.Namespace) -> int:
    archive_root = init_archive(args.archive_root)
    rows = scan_posts(archive_root)

    if not rows:
        print("No archived posts found yet.")
        return 0

    for row in rows:
        date_text = row.get("date", "")
        image_count = row.get("image_count", 0)
        title = row.get("post_title", "")
        folder = row.get("post_folder", "")
        url = row.get("source_url", "")
        print(f"{date_text} | {image_count} image(s) | {title}")
        print(f"  Folder: {folder}")
        if url:
            print(f"  URL: {url}")
    return 0


def inbox_files(archive_root: Path, target: str) -> list[Path]:
    inbox_root = archive_root / "00_INBOX"
    folders: list[Path] = []
    if target in {"all", "images"}:
        folders.append(inbox_root / "images")
    if target in {"all", "captions"}:
        folders.append(inbox_root / "captions")

    files: list[Path] = []
    for folder in folders:
        if folder.exists():
            files.extend(item for item in folder.rglob("*") if item.is_file() and item.name != ".gitkeep")
    return sorted(files, key=lambda item: str(item).casefold())


def delete_inbox_files(archive_root: Path, target: str = "all") -> int:
    inbox_root = archive_root / "00_INBOX"
    files = inbox_files(archive_root, target)
    deleted_count = 0
    for file_path in files:
        resolved = file_path.resolve()
        if not is_relative_to(resolved, inbox_root):
            raise ArchiveError(f"Refusing to delete a file outside 00_INBOX: {resolved}")
        resolved.unlink()
        deleted_count += 1
    return deleted_count


def command_clear_inbox(args: argparse.Namespace) -> int:
    archive_root = init_archive(args.archive_root)
    inbox_root = archive_root / "00_INBOX"
    files = inbox_files(archive_root, args.target)

    if not files:
        print(f"No inbox files found for target: {args.target}")
        return 0

    print("Inbox files selected:")
    for file_path in files:
        print(f"  {relative_to_archive(file_path, archive_root)}")

    if args.dry_run:
        print(f"Dry run only. {len(files)} file(s) would be deleted from 00_INBOX.")
        return 0

    if args.confirm and not args.yes:
        answer = input(f"Delete these {len(files)} file(s) from 00_INBOX? Type DELETE to confirm: ").strip()
        if answer != "DELETE":
            print("Cancelled. No files were deleted.")
            return 0

    deleted_count = delete_inbox_files(archive_root, args.target)

    print(f"Deleted {deleted_count} inbox file(s).")
    print("Only files inside 00_INBOX were deleted.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Local archive manager for manually saved Facebook photos and captions.",
    )
    parser.add_argument(
        "--archive-root",
        help=f"Archive folder to use. Default: .\\{ARCHIVE_ROOT_NAME}",
    )

    subparsers = parser.add_subparsers(dest="command")

    init_parser = subparsers.add_parser("init", help="Create archive folders and empty CSV files.")
    init_parser.set_defaults(func=command_init)

    new_post = subparsers.add_parser("new-post", help="Create a new source-of-truth post folder.")
    new_post.add_argument("--date", help="Post date, for example 2024-12-15, 2024년 12월 15일, or Dec 15 2024.")
    new_post.add_argument("--title", help="Short English title for the post.")
    new_post.add_argument("--url", help="Source Facebook URL.")
    new_post.add_argument("--images", help="Image file or folder containing manually saved images.")
    new_post.add_argument("--caption", help="Caption .txt file copied manually.")
    new_post.add_argument("--caption-lang", choices=["de", "en", "ko"], default="de", help="Caption source language for Korean translation.")
    new_post.add_argument("--category", help="Optional category label.")
    new_post.add_argument("--event", help="Optional event name.")
    new_post.add_argument("--location", help="Optional location.")
    new_post.add_argument("--mood", help="Optional mood label.")
    new_post.add_argument("--reels-usable", help="yes, maybe, or no.")
    new_post.set_defaults(func=command_new_post)

    curate = subparsers.add_parser("curate", help="Copy or hardlink an original image into a theme folder.")
    curate.add_argument("--original", help="Path to an image inside 01_ORIGINAL_BY_YEAR.")
    curate.add_argument("--theme", help="Supported theme folder name.")
    curate.add_argument("--use-case", help="Optional reels use case label.")
    curate.add_argument("--notes", help="Optional notes.")
    curate.add_argument("--mode", choices=["copy", "hardlink"], default="copy", help="Default: copy.")
    curate.set_defaults(func=command_curate)

    rebuild = subparsers.add_parser("rebuild-index", help="Rebuild master_index.csv from post folders.")
    rebuild.set_defaults(func=command_rebuild_index)

    dedupe = subparsers.add_parser("dedupe", help="Write an exact duplicate image report.")
    dedupe.set_defaults(func=command_dedupe)

    list_posts = subparsers.add_parser("list-posts", help="Print archived posts sorted by date.")
    list_posts.set_defaults(func=command_list_posts)

    clear_inbox = subparsers.add_parser("clear-inbox", help="Delete files from 00_INBOX after archiving.")
    clear_inbox.add_argument(
        "--target",
        choices=["all", "images", "captions"],
        default="all",
        help="Which inbox files to delete. Default: all.",
    )
    clear_inbox.add_argument("--dry-run", action="store_true", help="Show what would be deleted, but delete nothing.")
    clear_inbox.add_argument("--confirm", action="store_true", help="Ask for DELETE confirmation before deleting.")
    clear_inbox.add_argument("--yes", action="store_true", help="Accepted for old commands; deletion is already non-interactive unless --confirm is used.")
    clear_inbox.set_defaults(func=command_clear_inbox)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not hasattr(args, "func"):
        parser.print_help()
        return 0

    try:
        return args.func(args)
    except ArchiveError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nCancelled.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
