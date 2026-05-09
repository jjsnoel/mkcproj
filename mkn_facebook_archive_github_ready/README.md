# Muenchner Knabenchor Facebook Archive Manager

Local archive helper for manually saved Facebook photos and captions.

This project **does not scrape Facebook**, **does not use Meta/Facebook APIs**, and **does not bypass permissions**. It only organizes files that already exist on your computer.

## What to upload to GitHub

Upload only these project files:

```text
archive_manager.py
setup_archive.py
requirements.txt
README.md
PROJECT_CONTEXT.md
.gitignore
```

Do **not** upload `Muenchner_Knabenchor_Archive/`. That folder contains local photo/caption archive data and is intentionally ignored by Git.

## Requirements

- Windows 11
- PowerShell
- Python 3.11 or newer recommended
- No external Python packages required

Check Python:

```powershell
python --version
```

If that fails, try:

```powershell
py --version
```

## First setup

From the folder that contains this README:

```powershell
python setup_archive.py
```

This creates the local archive folder:

```text
Muenchner_Knabenchor_Archive/
  00_INBOX/
    images/
    captions/
  01_ORIGINAL_BY_YEAR/
  02_CURATED_BY_THEME/
  03_INDEX/
```

The command is safe to run more than once. Existing files are not deleted.

## Basic workflow

1. Manually save Facebook photos.
2. Manually copy the post caption into a `.txt` file, if there is a caption.
3. Put unsorted images here:

```text
Muenchner_Knabenchor_Archive\00_INBOX\images
```

4. Put caption text files here:

```text
Muenchner_Knabenchor_Archive\00_INBOX\captions
```

5. Add the post to the archive:

```powershell
python archive_manager.py new-post --date 2024-12-15 --title "Christmas Concert" --url "TEMP_URL" --images ".\Muenchner_Knabenchor_Archive\00_INBOX\images" --caption ".\Muenchner_Knabenchor_Archive\00_INBOX\captions\caption.txt"
```

No-caption example:

```powershell
python archive_manager.py new-post --date 2024-12-15 --title "No Caption Photos" --url "TEMP_URL" --images ".\Muenchner_Knabenchor_Archive\00_INBOX\images"
```

## Useful commands

Initialize archive folders:

```powershell
python archive_manager.py init
```

List archived posts:

```powershell
python archive_manager.py list-posts
```

Rebuild the master CSV index from existing post folders:

```powershell
python archive_manager.py rebuild-index
```

Find exact duplicate image files:

```powershell
python archive_manager.py dedupe
```

Preview inbox cleanup:

```powershell
python archive_manager.py clear-inbox --dry-run
```

Delete inbox files after confirming the post was archived:

```powershell
python archive_manager.py clear-inbox --yes
```

## Theme curation

Copy one archived original image into a theme folder:

```powershell
python archive_manager.py curate --original ".\Muenchner_Knabenchor_Archive\01_ORIGINAL_BY_YEAR\2024\2024-12-15_post_001_christmas_concert\images\001.jpg" --theme "02_Concert" --use-case "christmas_reel" --mode copy
```

Supported themes are defined in `SUPPORTED_THEMES` inside `archive_manager.py`.

## Notes for future editing

- `01_ORIGINAL_BY_YEAR` is the source-of-truth archive.
- `02_CURATED_BY_THEME` is for copied or hardlinked selections.
- `03_INDEX/master_index.csv` can be rebuilt from existing post folders.
- `clear-inbox` only deletes files inside `00_INBOX`.
- Real photo/caption data should stay local and out of GitHub.
