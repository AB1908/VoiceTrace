"""Main audio processing pipeline for Obsidian capture with observability."""
from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import re
import shutil
import time
from typing import Any

from config import Config
from llm import LLMProcessor
from transcription import Transcriber


class AudioProcessor:
    def __init__(self) -> None:
        self.transcriber = Transcriber()
        self.llm = LLMProcessor()

    def process(
        self, audio_path: Path, raw_only: bool = False, clean_only: bool = False
    ) -> bool:
        if raw_only and clean_only:
            raise ValueError("raw_only and clean_only cannot both be true")

        started_at = datetime.now()
        session_id = self._make_session_id(audio_path, started_at)
        session_dir = Config.sessions_dir() / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        metrics: dict[str, Any] = {
            "session_id": session_id,
            "timestamp": started_at.isoformat(),
            "audio_file": audio_path.name,
            "audio_path": str(audio_path),
            "raw_only": raw_only,
            "clean_only": clean_only,
            "status": "started",
            "durations_sec": {},
            "transcription_method": None,
            "breakdown_model": None,
            "capture_file": str(Config.capture_file()),
            "session_dir": str(session_dir),
        }

        print("\n" + "=" * 60)
        print(f"Processing: {audio_path.name}")
        print("=" * 60)
        print(f"Session dir: {session_dir}")
        print(f"Capture file: {Config.capture_file()}")

        try:
            t0 = time.perf_counter()
            print("Step 1/4: Transcribing...")
            raw_text, transcription_method = self.transcriber.transcribe(audio_path)
            metrics["durations_sec"]["transcription"] = round(time.perf_counter() - t0, 3)
            metrics["transcription_method"] = transcription_method
            print(f"  OK ({transcription_method})")

            raw_path = self._save_raw_transcript(audio_path, raw_text, session_dir)
            metrics["raw_transcript_path"] = str(raw_path)
            metrics["raw_chars"] = len(raw_text)
            metrics["raw_words"] = len(raw_text.split())
            print(f"  Raw transcript saved: {raw_path}")

            if raw_only:
                print("Step 2/2: Raw-only mode, skipping cleanup and task breakdown...")
                archived_path = self._archive_audio(audio_path)
                metrics["archived_audio_path"] = str(archived_path)
                metrics["breakdown_model"] = "raw_only"
                metrics["status"] = "success"
                metrics["durations_sec"]["total"] = round(time.perf_counter() - t0, 3)
                self._write_session_metadata(session_dir, metrics)
                self._append_metrics(metrics)
                self._log_event(audio_path, transcription_method, "raw_only")
                print("Complete (raw-only)")
                return True

            t_cleanup = time.perf_counter()
            print("Step 2/4: Cleaning transcription...")
            clean_text = self.llm.cleanup_transcription(raw_text)
            metrics["durations_sec"]["cleanup"] = round(time.perf_counter() - t_cleanup, 3)
            metrics["clean_chars"] = len(clean_text)
            metrics["clean_words"] = len(clean_text.split())
            metrics["compression_ratio"] = round(
                (len(clean_text) / max(1, len(raw_text))), 4
            )
            clean_path = self._write_text(session_dir / "cleaned_transcript.txt", clean_text)
            metrics["clean_transcript_path"] = str(clean_path)
            print("  OK")

            if clean_only:
                print("Step 3/3: Clean-only mode, skipping task breakdown...")
                model_used = "skipped_clean_only"
                breakdown = "_Skipped due to --clean-only mode._"
                metrics["breakdown_model"] = model_used
            else:
                t_breakdown = time.perf_counter()
                print("Step 3/4: Breaking down tasks...")
                breakdown, model_used = self.llm.breakdown_tasks(clean_text)
                metrics["durations_sec"]["breakdown"] = round(
                    time.perf_counter() - t_breakdown, 3
                )
                metrics["breakdown_model"] = model_used
                breakdown_path = self._write_text(session_dir / "tasks_breakdown.md", breakdown)
                metrics["tasks_path"] = str(breakdown_path)
                print(f"  OK ({model_used})")

            t_capture = time.perf_counter()
            if clean_only:
                print("Step 4/4: Writing Obsidian capture (without task breakdown)...")
            else:
                print("Step 4/4: Writing Obsidian capture...")
            self._append_capture(
                audio_path=audio_path,
                raw_text=raw_text,
                clean_text=clean_text,
                breakdown=breakdown,
                transcription_method=transcription_method,
                breakdown_model=model_used,
            )
            metrics["durations_sec"]["capture_write"] = round(
                time.perf_counter() - t_capture, 3
            )

            archived_path = self._archive_audio(audio_path)
            metrics["archived_audio_path"] = str(archived_path)
            metrics["status"] = "success"
            metrics["durations_sec"]["total"] = round(time.perf_counter() - t0, 3)

            self._write_session_metadata(session_dir, metrics)
            self._append_metrics(metrics)
            self._log_event(audio_path, transcription_method, model_used)

            print("Complete")
            return True
        except Exception as exc:
            metrics["status"] = "failed"
            metrics["error"] = str(exc)
            metrics["durations_sec"]["total"] = round(time.perf_counter() - t0, 3)
            self._write_session_metadata(session_dir, metrics)
            self._append_metrics(metrics)
            print(f"Error processing {audio_path.name}: {exc}")
            return False

    def _append_capture(
        self,
        audio_path: Path,
        raw_text: str,
        clean_text: str,
        breakdown: str,
        transcription_method: str,
        breakdown_model: str,
    ) -> None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

        entry = f"""
## {timestamp}
**Audio:** [[{audio_path.name}]]
**Transcription:** {transcription_method} | **Breakdown:** {breakdown_model}

**Raw Transcription:**
> {raw_text}

**Cleaned:**
{clean_text}

**Tasks:**
{breakdown}

---
"""

        with open(Config.capture_file(), "a", encoding="utf-8") as handle:
            handle.write(entry)

    def _save_raw_transcript(self, audio_path: Path, raw_text: str, session_dir: Path) -> Path:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        raw_output = Config.raw_dir() / f"{timestamp}-{audio_path.stem}.txt"
        self._write_text(raw_output, raw_text)

        session_output = session_dir / "raw_transcript.txt"
        self._write_text(session_output, raw_text)
        return session_output

    def _archive_audio(self, audio_path: Path) -> Path:
        destination = Config.processed_dir() / audio_path.name
        if destination.exists():
            suffix = datetime.now().strftime("%Y%m%d-%H%M%S")
            destination = Config.processed_dir() / f"{audio_path.stem}-{suffix}{audio_path.suffix}"
        shutil.move(str(audio_path), str(destination))
        return destination

    def _log_event(self, audio_path: Path, transcription_method: str, model_used: str) -> None:
        log_file = Config.logs_dir() / f"{datetime.now().strftime('%Y-%m')}-processing.jsonl"
        payload = {
            "timestamp": datetime.now().isoformat(),
            "audio_file": audio_path.name,
            "transcription_method": transcription_method,
            "breakdown_model": model_used,
        }
        with open(log_file, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload) + "\n")

    def _append_metrics(self, metrics: dict[str, Any]) -> None:
        with open(Config.metrics_file(), "a", encoding="utf-8") as handle:
            handle.write(json.dumps(metrics) + "\n")

    def _write_session_metadata(self, session_dir: Path, metrics: dict[str, Any]) -> None:
        metadata = session_dir / "session_meta.json"
        self._write_text(metadata, json.dumps(metrics, indent=2))

    def _write_text(self, path: Path, content: str) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(content.strip() + "\n")
        return path

    def _make_session_id(self, audio_path: Path, now: datetime) -> str:
        base = re.sub(r"[^a-zA-Z0-9._-]+", "-", audio_path.stem).strip("-").lower() or "audio"
        return f"{now.strftime('%Y%m%d-%H%M%S')}-{base}"
