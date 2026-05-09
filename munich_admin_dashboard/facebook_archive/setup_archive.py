from __future__ import annotations

try:
    from .archive_manager import init_archive, script_dir
except ImportError:  # Allows: python facebook_archive/setup_archive.py
    from archive_manager import init_archive, script_dir


def main() -> int:
    archive_root = init_archive()
    print(f"Archive is ready: {archive_root}")
    print(f"README: {script_dir() / 'README.md'}")
    print("Safe to run again. Existing files were not deleted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
