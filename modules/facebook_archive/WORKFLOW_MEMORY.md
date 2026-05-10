# Workflow Memory

Use this file only for stable operating rules. Do not add a running log of posts here.

## Rules

- Do not scrape Facebook.
- Do not use internet.
- Work only inside this project folder.
- Archive manually saved local files only.
- Use copy when adding posts to `01_ORIGINAL_BY_YEAR`.
- Never overwrite an existing post folder or destination image without asking.
- Default source URL is `TEMP_URL` unless the user gives a real URL.

## Inbox Cleanup

- After a post is successfully copied into `01_ORIGINAL_BY_YEAR`, delete files from `Muenchner_Knabenchor_Archive/00_INBOX` automatically.
- Do not ask the user again before this inbox cleanup.
- Delete only files inside `Muenchner_Knabenchor_Archive/00_INBOX`.
- Keep the inbox folders themselves.

## Caption Rules

- If the user gives no caption:
  - Do not create `caption_original.txt`.
  - Do not create `caption_ko.txt`.
  - Leave caption fields blank in `master_index.csv`.
- If the user gives a caption:
  - Create `caption_original.txt`.
  - Create `caption_ko.txt`.
  - If the caption is German, translate it into Korean in `caption_ko.txt`.

## Defaults

- No-caption title:
  - `No Caption Photo` for one image.
  - `No Caption Photos` for multiple images.
- No-caption metadata:
  - `category`: `Unknown`
  - `reels_usable`: `maybe`

## Environment Note

- `python` and `py` were not found on PATH in this environment.
- Until Python is available, post additions may be done with safe PowerShell commands that mirror the archive manager behavior.
- The Python scripts should work once Python is installed or added to PATH.

## Continue Workflow

When the user gives a date and image count:

1. Check `00_INBOX/images`.
2. Create the post folder under `01_ORIGINAL_BY_YEAR/YYYY`.
3. Copy inbox images into `images/001.jpg`, `002.jpg`, etc.
4. Create `post_info.md` and `source_url.txt`.
5. Create caption files only if the user supplied a caption.
6. Append a row to `03_INDEX/master_index.csv`.
7. Delete inbox files after successful copy.
8. Verify the new post and index row.

Use `03_INDEX/master_index.csv` as the source for the list of posts already added.
