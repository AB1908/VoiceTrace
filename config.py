"""Configuration and path management."""
from __future__ import annotations

import os
import platform
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


class Config:
    IS_WINDOWS = platform.system() == "Windows"
    IS_MAC = platform.system() == "Darwin"
    IS_LINUX = platform.system() == "Linux"

    @staticmethod
    def get_vault_path() -> Path:
        env_path = os.getenv("OBSIDIAN_VAULT_PATH")
        if env_path:
            return Path(env_path).expanduser()
        return Path.home() / "Documents" / "ObsidianVault"

    @classmethod
    def vault_path(cls) -> Path:
        return cls.get_vault_path()

    @classmethod
    def audio_dir(cls) -> Path:
        return cls.vault_path() / "audio"

    @classmethod
    def processed_dir(cls) -> Path:
        return cls.audio_dir() / "processed"

    @classmethod
    def capture_file(cls) -> Path:
        return cls.vault_path() / "capture.md"

    @classmethod
    def logs_dir(cls) -> Path:
        return cls.vault_path() / "logs"

    @classmethod
    def raw_dir(cls) -> Path:
        return cls.vault_path() / "raw"

    @classmethod
    def sessions_dir(cls) -> Path:
        return cls.vault_path() / "sessions"

    @classmethod
    def metrics_file(cls) -> Path:
        return cls.logs_dir() / "metrics.jsonl"

    # API keys / models
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")
    LOCAL_LLM_MODEL = os.getenv("LOCAL_LLM_MODEL", "meta-llama-3-8b-instruct")
    CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-5")
    LOCAL_LLM_API_BASE = os.getenv("LOCAL_LLM_API_BASE", "http://127.0.0.1:1234/v1")
    LOCAL_LLM_API_KEY = os.getenv("LOCAL_LLM_API_KEY")
    LOCAL_LLM_CONNECT_TIMEOUT_SEC = float(os.getenv("LOCAL_LLM_CONNECT_TIMEOUT_SEC", "5"))
    LOCAL_LLM_READ_TIMEOUT_SEC = float(os.getenv("LOCAL_LLM_READ_TIMEOUT_SEC", "120"))
    LOCAL_LLM_RETRIES = int(os.getenv("LOCAL_LLM_RETRIES", "2"))
    LOCAL_LLM_RETRY_BACKOFF_SEC = float(os.getenv("LOCAL_LLM_RETRY_BACKOFF_SEC", "2"))

    # Features
    USE_CLAUDE_FOR_COMPLEX = os.getenv("USE_CLAUDE_FOR_COMPLEX", "true").lower() == "true"
    ANONYMIZE_FOR_CLAUDE = os.getenv("ANONYMIZE_FOR_CLAUDE", "true").lower() == "true"

    # Watcher
    WATCH_EXTENSIONS = [".webm", ".m4a", ".mp3", ".wav", ".ogg", ".flac"]
    WATCH_SETTLE_SECONDS = float(os.getenv("WATCH_SETTLE_SECONDS", "2"))
    TRANSCRIPTION_PROGRESS_EVERY = int(os.getenv("TRANSCRIPTION_PROGRESS_EVERY", "10"))

    @classmethod
    def ensure_dirs(cls) -> None:
        cls.audio_dir().mkdir(parents=True, exist_ok=True)
        cls.processed_dir().mkdir(parents=True, exist_ok=True)
        cls.logs_dir().mkdir(parents=True, exist_ok=True)
        cls.raw_dir().mkdir(parents=True, exist_ok=True)
        cls.sessions_dir().mkdir(parents=True, exist_ok=True)
        cls.capture_file().touch(exist_ok=True)
        cls.metrics_file().touch(exist_ok=True)

    @classmethod
    def validate(cls) -> None:
        if not cls.vault_path().exists():
            raise ValueError(f"Vault path does not exist: {cls.vault_path()}")

        if cls.USE_CLAUDE_FOR_COMPLEX and not cls.ANTHROPIC_API_KEY:
            print(
                "Warning: Claude routing requested, but ANTHROPIC_API_KEY is missing. "
                "No requests will be sent to Anthropic; local LLM will be used."
            )


Config.ensure_dirs()
