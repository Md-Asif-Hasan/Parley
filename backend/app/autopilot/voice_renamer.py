"""
Voice Speaker Renaming Module for Parley.
Extracts speaker identity declarations and rename commands directly from speech.
"""
import re
from typing import Optional, Tuple

SELF_IDENTIFY_PATTERNS = [
    # "my name is Alex", "my name's Alex"
    r"\bmy name(?:'s|\s+is)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b",
    # "i am Alex", "i'm Alex", "this is Alex"
    r"\b(?:i am|i'm|this is)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)(?:\s+speaking|\s+here)?\b",
    # "call me Alex", "you can call me Alex"
    r"\b(?:you can\s+)?call me\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b",
    # "Alex here"
    r"\b([A-Z][a-z]+)\s+here\b",
]

TARGET_RENAME_PATTERNS = [
    # "speaker 0 is Bob", "speaker zero is Bob", "speaker_0 is Bob"
    r"\bspeaker[\s_]+(\d+|zero|one|two|three|four|five)\s+is\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b",
    # "rename speaker 1 to Charlie"
    r"\brename\s+speaker[\s_]+(\d+|zero|one|two|three|four|five)\s+to\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b",
    # "set speaker 0 name to Bob"
    r"\bset\s+speaker[\s_]+(\d+|zero|one|two|three|four|five)(?:'s|\s+name)?\s+to\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b",
]

WORD_TO_DIGIT = {
    "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4", "five": "5"
}

IGNORE_NAMES = {"speaking", "here", "today", "ready", "going", "thinking", "sure", "sorry", "fine", "good"}


def extract_speaker_rename(text: str, current_speaker_id: Optional[str] = None) -> Optional[Tuple[str, str]]:
    """
    Analyzes spoken utterance text for self-identification or speaker rename commands.
    Returns (speaker_id, new_name) or None if no rename intent is detected.
    """
    if not text:
        return None

    cleaned = text.strip()

    # 1. Check explicit target rename (e.g. "Speaker 1 is Bob")
    for pattern in TARGET_RENAME_PATTERNS:
        match = re.search(pattern, cleaned, re.IGNORECASE)
        if match:
            raw_spk = match.group(1).lower()
            digit = WORD_TO_DIGIT.get(raw_spk, raw_spk)
            speaker_id = f"speaker_{digit}"
            name = match.group(2).strip().title()
            if name.lower() not in IGNORE_NAMES:
                return speaker_id, name

    # 2. Check self-identification (e.g. "I am Alex")
    if current_speaker_id:
        for pattern in SELF_IDENTIFY_PATTERNS:
            match = re.search(pattern, cleaned, re.IGNORECASE)
            if match:
                raw_name = match.group(1).strip()
                # Strip trailing conjunctions/prepositions BEFORE .title() so comparison is reliable
                # e.g. "Alex and" — split on lowercase original, keep first word
                parts = raw_name.split()
                STOP_WORDS = {"and", "from", "with", "for", "the", "speaking", "here", "to", "in", "at", "as", "is", "or", "but"}
                if len(parts) > 1 and parts[1].lower() in STOP_WORDS:
                    raw_name = parts[0]
                # Also strip trailing stop words via regex (catches multi-word names like "Alex And Will")
                raw_name = re.sub(
                    r"\s+(?:and|from|with|for|the|speaking|here|or|but)(?:\s.*)?$",
                    "", raw_name, flags=re.IGNORECASE
                ).strip()
                name = raw_name.title()
                if name.lower() not in IGNORE_NAMES and len(name) >= 2:
                    return current_speaker_id, name

    return None
