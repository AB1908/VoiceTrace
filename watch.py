"""Watch Obsidian audio folder and auto-process new files."""
from __future__ import annotations

import time
from pathlib import Path

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from config import Config
from process_audio import AudioProcessor


class AudioFileHandler(FileSystemEventHandler):
    def __init__(self) -> None:
        self.processor = AudioProcessor()
        self.processing: set[Path] = set()

    def on_created(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return

        path = Path(event.src_path)
        if path.suffix.lower() not in Config.WATCH_EXTENSIONS:
            return

        if path in self.processing:
            return

        self.processing.add(path)
        print(f"\nNew audio detected: {path.name}")

        time.sleep(Config.WATCH_SETTLE_SECONDS)
        self.processor.process(path)

        self.processing.discard(path)


def watch() -> None:
    Config.validate()
    print(f"Watching: {Config.audio_dir()}")
    print(f"Capture output: {Config.capture_file()}")
    print("Press Ctrl+C to stop\n")

    observer = Observer()
    observer.schedule(AudioFileHandler(), str(Config.audio_dir()), recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()

    observer.join()


if __name__ == "__main__":
    watch()
