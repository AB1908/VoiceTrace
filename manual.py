"""Manual processing trigger."""
from __future__ import annotations

import sys
from pathlib import Path

from config import Config
from process_audio import AudioProcessor


def _iter_audio_files() -> list[Path]:
    return sorted(
        [
            f
            for f in Config.audio_dir().iterdir()
            if f.is_file() and f.suffix.lower() in Config.WATCH_EXTENSIONS
        ]
    )


def _parse_args(argv: list[str]) -> tuple[str, bool, bool]:
    raw_only = "--raw-only" in argv
    clean_only = "--clean-only" in argv
    args = [arg for arg in argv if arg not in {"--raw-only", "--clean-only"}]

    if raw_only and clean_only:
        print("Error: --raw-only and --clean-only cannot be used together.")
        sys.exit(1)

    if len(args) < 2:
        print("Usage: python manual.py [--raw-only|--clean-only] <audio_file>")
        print("   or: python manual.py [--raw-only|--clean-only] --all")
        sys.exit(1)
    return args[1], raw_only, clean_only


def main() -> None:
    Config.validate()
    processor = AudioProcessor()
    target, raw_only, clean_only = _parse_args(sys.argv)

    if target == "--all":
        files = _iter_audio_files()
        if not files:
            print("No audio files found")
            return

        print(f"Found {len(files)} file(s)")
        for item in files:
            processor.process(item, raw_only=raw_only, clean_only=clean_only)
        return

    audio_path = Path(target).expanduser()
    if not audio_path.exists():
        print(f"File not found: {audio_path}")
        sys.exit(1)

    processor.process(audio_path, raw_only=raw_only, clean_only=clean_only)


if __name__ == "__main__":
    main()
