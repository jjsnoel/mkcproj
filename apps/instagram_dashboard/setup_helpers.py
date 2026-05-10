from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path


VIDEO_TRANSLATION_MODULES = {
    "whisper": "openai-whisper",
    "transformers": "transformers",
    "sentencepiece": "sentencepiece",
    "sacremoses": "sacremoses",
    "accelerate": "accelerate",
    "torch": "torch",
}


def missing_video_translation_packages() -> list[str]:
    missing: list[str] = []
    for module_name, package_name in VIDEO_TRANSLATION_MODULES.items():
        if importlib.util.find_spec(module_name) is None:
            missing.append(package_name)
    return missing


def install_video_translation_requirements(toolkit_root: Path, timeout_seconds: int = 1800) -> dict[str, object]:
    requirements_path = toolkit_root / "requirements_video_stt.txt"
    if not requirements_path.exists():
        return {
            "ok": False,
            "command": "",
            "output": "",
            "error": f"requirements file not found: {requirements_path}",
        }

    command = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "-r",
        str(requirements_path),
    ]
    try:
        completed = subprocess.run(
            command,
            cwd=str(toolkit_root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            check=False,
        )
    except Exception as exc:
        return {
            "ok": False,
            "command": " ".join(command),
            "output": "",
            "error": str(exc),
        }

    return {
        "ok": completed.returncode == 0,
        "command": " ".join(command),
        "output": (completed.stdout or "") + (completed.stderr or ""),
        "error": "" if completed.returncode == 0 else f"pip exited with code {completed.returncode}",
    }
