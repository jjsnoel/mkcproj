# Muenchner Knabenchor Facebook Archive Manager

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
Muenchner_Knabenchor_Archive\00_INBOX\images
```

4. Put caption text files in:

```text
Muenchner_Knabenchor_Archive\00_INBOX\captions
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
python archive_manager.py new-post --date 2024-12-15 --title "Christmas Concert" --url "https://www.facebook.com/example" --images ".\00_INBOX\images" --caption ".\00_INBOX\captions\caption.txt"
```

Curate one original image into a theme folder:

```powershell
python archive_manager.py curate --original ".\01_ORIGINAL_BY_YEAR\2024\2024-12-15_post_001_christmas_concert\images\001.jpg" --theme "02_Concert" --use-case "christmas_reel" --mode copy
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

The examples above use short paths like `.\00_INBOX\images`. The tool checks inside `Muenchner_Knabenchor_Archive` automatically, so you can run these commands from the folder that contains `archive_manager.py`.

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
- `rebuild-index` rewrites `03_INDEX\master_index.csv` from the folders on disk. It does not delete files.
- Use quotes around Windows paths that contain spaces.
