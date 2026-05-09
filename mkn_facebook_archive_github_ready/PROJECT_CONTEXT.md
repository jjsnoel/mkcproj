# Project Context

## Purpose

This is a small local archive manager for manually saved Facebook photos/captions related to Münchner Knabenchor materials.

It is meant to help organize archived posts by year, curate selected images into theme folders, and rebuild CSV indexes for later Instagram/Reels planning.

## Safety / scope rules

- Do not scrape Facebook.
- Do not use the internet inside this tool.
- Do not use Meta/Facebook APIs.
- Do not bypass platform permissions.
- Work only with local files the user already saved manually.
- Keep real archive data out of GitHub.

## Main files

- `archive_manager.py`: CLI tool and all archive logic.
- `setup_archive.py`: small setup entrypoint that creates the archive structure.
- `requirements.txt`: intentionally empty of packages because only Python standard library is used.
- `.gitignore`: excludes local archive data, media files, CSV outputs, env files, and caches.

## Local data folder

The generated local folder is:

```text
Muenchner_Knabenchor_Archive/
```

This folder is intentionally ignored by Git.

## Current CLI commands

```powershell
python archive_manager.py init
python archive_manager.py new-post
python archive_manager.py curate
python archive_manager.py rebuild-index
python archive_manager.py dedupe
python archive_manager.py list-posts
python archive_manager.py clear-inbox --dry-run
python archive_manager.py clear-inbox --yes
```

## Design notes

- The project currently favors a simple single-file CLI over a package/module split.
- Keep Windows PowerShell examples in the README because this is the user's main environment.
- Avoid adding heavy dependencies unless there is a clear reason.
- When adding future features, keep archive data separate from code.
