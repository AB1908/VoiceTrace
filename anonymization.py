"""Anonymization helpers for privacy-preserving cloud calls."""
from __future__ import annotations

import re
from typing import Dict, Tuple

ANONYMIZATION_MAP = {
    "Anthropic": "[COMPANY_A]",
    "Google": "[COMPANY_B]",
    "OpenAI": "[COMPANY_C]",
    "Obsidian": "[TOOL_A]",
    "Ollama": "[TOOL_B]",
}


def anonymize(text: str) -> Tuple[str, Dict[str, str]]:
    anonymized = text
    reverse_map: Dict[str, str] = {}

    for original, placeholder in ANONYMIZATION_MAP.items():
        pattern = re.compile(re.escape(original), re.IGNORECASE)
        if pattern.search(anonymized):
            anonymized = pattern.sub(placeholder, anonymized)
            reverse_map[placeholder] = original

    return anonymized, reverse_map


def deanonymize(text: str, reverse_map: Dict[str, str]) -> str:
    output = text
    for placeholder, original in reverse_map.items():
        output = output.replace(placeholder, original)
    return output
