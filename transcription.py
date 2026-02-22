"""Audio transcription using local faster-whisper."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from faster_whisper import WhisperModel

from config import Config


class Transcriber:
    def __init__(self) -> None:
        self._model: Optional[WhisperModel] = None

    def _load_model(self) -> WhisperModel:
        if self._model is None:
            print(f"Loading Whisper model: {Config.WHISPER_MODEL}")
            self._model = WhisperModel(Config.WHISPER_MODEL, device="cpu", compute_type="int8")
        return self._model

    def transcribe(self, audio_path: Path) -> tuple[str, str]:
        model = self._load_model()
        segments, _info = model.transcribe(str(audio_path))
        pieces: list[str] = []
        count = 0
        for segment in segments:
            count += 1
            pieces.append(segment.text.strip())
            if count % max(1, Config.TRANSCRIPTION_PROGRESS_EVERY) == 0:
                print(
                    f"  ...transcribed {count} segments "
                    f"(up to ~{segment.end:.1f}s)"
                )

        text = " ".join(pieces).strip()
        if not text:
            raise ValueError("Transcription returned empty text")
        return text, "whisper_local"
