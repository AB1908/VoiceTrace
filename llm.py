"""LLM cleanup and task breakdown routing (Local OpenAI-compatible LLM + Claude)."""
from __future__ import annotations

import time
from typing import Optional

import requests
from anthropic import Anthropic

from anonymization import anonymize, deanonymize
from config import Config


class LLMProcessor:
    def __init__(self) -> None:
        self.anthropic_client: Optional[Anthropic] = None
        self._local_llm_checked = False
        if Config.ANTHROPIC_API_KEY:
            self.anthropic_client = Anthropic(api_key=Config.ANTHROPIC_API_KEY)

    def _check_local_llm(self) -> None:
        if self._local_llm_checked:
            return
        base = Config.LOCAL_LLM_API_BASE.rstrip("/")
        response = requests.get(
            f"{base}/models",
            timeout=(
                Config.LOCAL_LLM_CONNECT_TIMEOUT_SEC,
                max(2.0, Config.LOCAL_LLM_CONNECT_TIMEOUT_SEC),
            ),
        )
        response.raise_for_status()
        self._local_llm_checked = True

    def _local_chat_completion(self, prompt: str, temperature: float, operation: str) -> str:
        base = Config.LOCAL_LLM_API_BASE.rstrip("/")
        self._check_local_llm()
        last_error: Exception | None = None
        attempts = max(1, Config.LOCAL_LLM_RETRIES + 1)

        for attempt in range(1, attempts + 1):
            try:
                response = requests.post(
                    f"{base}/chat/completions",
                    headers={
                        "Content-Type": "application/json",
                        **(
                            {"Authorization": f"Bearer {Config.LOCAL_LLM_API_KEY}"}
                            if Config.LOCAL_LLM_API_KEY
                            else {}
                        ),
                    },
                    json={
                        "model": Config.LOCAL_LLM_MODEL,
                        "temperature": temperature,
                        "messages": [{"role": "user", "content": prompt}],
                    },
                    timeout=(
                        Config.LOCAL_LLM_CONNECT_TIMEOUT_SEC,
                        Config.LOCAL_LLM_READ_TIMEOUT_SEC,
                    ),
                )
                response.raise_for_status()
                payload = response.json()
                content = (
                    payload.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                    .strip()
                )
                if not content:
                    raise ValueError("Local LLM returned empty content")
                return content
            except (requests.RequestException, ValueError) as exc:
                last_error = exc
                if attempt >= attempts:
                    break
                print(
                    f"  Local LLM {operation} failed (attempt {attempt}/{attempts}). "
                    f"Retrying in {Config.LOCAL_LLM_RETRY_BACKOFF_SEC:.1f}s..."
                )
                time.sleep(Config.LOCAL_LLM_RETRY_BACKOFF_SEC)

        raise RuntimeError(f"Local LLM {operation} failed after {attempts} attempts: {last_error}")

    def cleanup_transcription(self, raw_text: str) -> str:
        prompt = f"""Clean up this voice transcription. Preserve meaning.

Raw transcription:
{raw_text}

Instructions:
- Remove filler words and obvious speech artifacts.
- Fix repeated words and punctuation.
- Keep original intent and facts.

Return only cleaned text."""

        return self._local_chat_completion(prompt=prompt, temperature=0.2, operation="cleanup")

    def should_use_claude(self, text: str) -> bool:
        if not Config.USE_CLAUDE_FOR_COMPLEX or not self.anthropic_client:
            return False

        lowered = text.lower()
        phrases = [
            "break down",
            "step by step",
            "what should i do",
            "what's the best way",
            "plan",
            "depends on",
            "blocked by",
            "sequence",
        ]
        return len(text.split()) > 60 or any(p in lowered for p in phrases)

    def breakdown_with_local_llm(self, clean_text: str) -> str:
        prompt = f"""Convert this note into actionable tasks.

Text:
{clean_text}

Output markdown checklist only.
Format each line as:
- [ ] Action (~time) #tags

Tags allowed: #work #personal #research #quick #deep-work"""
        return self._local_chat_completion(prompt=prompt, temperature=0.2, operation="task breakdown")

    def breakdown_with_claude(self, clean_text: str) -> str:
        if not self.anthropic_client:
            raise ValueError("ANTHROPIC_API_KEY is not configured")

        input_text = clean_text
        reverse_map = {}

        if Config.ANONYMIZE_FOR_CLAUDE:
            input_text, reverse_map = anonymize(clean_text)

        message = self.anthropic_client.messages.create(
            model=Config.CLAUDE_MODEL,
            max_tokens=2048,
            messages=[
                {
                    "role": "user",
                    "content": f"""Break this into specific next actions.

Task:
{input_text}

Output markdown checklist only.
Format:
- [ ] Action (~time) #tags

Include dependencies and execution order if relevant.""",
                }
            ],
        )

        parts = []
        for block in message.content:
            text = getattr(block, "text", None)
            if text:
                parts.append(text)
        result = "\n".join(parts).strip()

        if reverse_map:
            result = deanonymize(result, reverse_map)

        if not result:
            raise ValueError("Claude breakdown returned empty text")
        return result

    def breakdown_tasks(self, clean_text: str) -> tuple[str, str]:
        if self.should_use_claude(clean_text):
            print("  Using Claude for complex breakdown...")
            return self.breakdown_with_claude(clean_text), "claude"

        print("  Using local LLM for breakdown...")
        return self.breakdown_with_local_llm(clean_text), "local_llm"
