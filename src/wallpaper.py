"""Apply a rendered PNG as the macOS desktop wallpaper."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    args = argv or sys.argv[1:]
    if len(args) != 1:
        print("Usage: python -m src.wallpaper IMAGE_PATH", file=sys.stderr)
        return 2

    image_path = Path(args[0]).expanduser().resolve()
    if not image_path.exists():
        print(f"Missing wallpaper image: {image_path}", file=sys.stderr)
        return 1

    apply_wallpaper(image_path)
    print(f"Applied wallpaper from {image_path}")
    return 0


def apply_wallpaper(image_path: Path) -> None:
    if os.environ.get("LOCKSCREEN_WALLPAPER_NOOP") in {"1", "true", "TRUE", "yes", "YES"}:
        return

    quoted_path = _apple_script_string(image_path)
    scripts = [
        f'tell application "Finder" to set desktop picture to POSIX file "{quoted_path}"',
        (
            'tell application "System Events"'
            f' to tell every desktop to set picture to POSIX file "{quoted_path}"'
        ),
    ]

    last_error: subprocess.CalledProcessError | None = None
    for script in scripts:
        try:
            subprocess.run(["osascript", "-e", script], check=True, capture_output=True, text=True)
            return
        except subprocess.CalledProcessError as exc:
            last_error = exc

    detail = ""
    if last_error:
        detail = (last_error.stderr or last_error.stdout or "").strip()
    if detail:
        raise RuntimeError(f"Failed to apply wallpaper: {detail}")
    raise RuntimeError("Failed to apply wallpaper with osascript.")


def _apple_script_string(path: Path) -> str:
    return str(path).replace("\\", "\\\\").replace('"', '\\"')


if __name__ == "__main__":
    raise SystemExit(main())
