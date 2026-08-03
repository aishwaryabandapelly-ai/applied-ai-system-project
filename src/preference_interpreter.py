"""
Specialized natural-language preference interpreter for TuneGuide AI
(fine-tuning / specialization stretch feature).

This is NOT a fine-tuned neural model. It specializes the system's behavior with
deterministic, few-shot-inspired pattern matching over a small synthetic dataset
(``specialization/preference_examples.json``). Given a free-text request such as
"I'm studying for my robotics exam.", it infers a structured preference profile
(genre, mood, target energy, acoustic preference).

No AI model, no randomness, no external service, no hidden reasoning — only
documented keyword rules. Every genre and mood produced exists in
``data/songs.csv``.

Public API:
- ``InterpretedPreference`` — structured interpretation result.
- ``interpret_request(text)`` — infer a profile from natural language.
- ``merge_interpreted_profile(profile, interpreted)`` — fill only missing fields.
"""

import json
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

from src.logging_config import get_logger

logger = get_logger("tuneguide.interpreter")

DEFAULT_EXAMPLES_PATH = os.path.join("specialization", "preference_examples.json")

_PROFILE_FIELDS = {"favorite_genre", "favorite_mood", "target_energy", "likes_acoustic"}

# Tokens ignored when reporting unmatched tokens.
_STOPWORDS = {
    "i", "im", "i'm", "a", "an", "the", "to", "my", "me", "for", "some",
    "something", "need", "want", "play", "give", "get", "of", "and", "is",
    "are", "while", "after", "before", "on", "at", "in", "it", "music",
    "songs", "song", "please", "help", "with", "something", "tonight", "up",
}

# Catalog moods that may be named directly in a request.
_CATALOG_MOODS = {
    "angry", "chill", "confident", "euphoric", "focused", "happy", "intense",
    "melancholy", "moody", "nostalgic", "relaxed", "romantic", "uplifting", "wistful",
}

# --- Attribute rules (explicit descriptors; processed first) ---------------
# Each fills a complete 4-field profile so a description alone can validate.
_ATTRIBUTE_RULES = [
    {"name": "nostalgic", "keywords": ["nostalgic", "nostalgia", "throwback"],
     "profile": {"favorite_genre": "indie pop", "favorite_mood": "nostalgic", "target_energy": 0.5, "likes_acoustic": False}},
    {"name": "energetic", "keywords": ["energetic", "hyped", "pumped", "upbeat", "hype"],
     "profile": {"favorite_genre": "electronic", "favorite_mood": "euphoric", "target_energy": 0.85, "likes_acoustic": False}},
    {"name": "instrumental", "keywords": ["instrumental", "no vocals", "without vocals", "no lyrics", "without lyrics", "vocals", "lyrics"],
     "profile": {"favorite_genre": "ambient", "favorite_mood": "chill", "target_energy": 0.4, "likes_acoustic": True}},
    {"name": "acoustic", "keywords": ["acoustic", "unplugged"],
     "profile": {"favorite_genre": "folk", "favorite_mood": "relaxed", "target_energy": 0.35, "likes_acoustic": True}},
]

# --- Activity/context rules (processed after attributes) -------------------
_ACTIVITY_RULES = [
    {"name": "studying", "keywords": ["study", "studying", "exam", "exams", "homework", "revision", "revise", "essay", "thesis"],
     "profile": {"favorite_genre": "lofi", "favorite_mood": "focused", "target_energy": 0.3, "likes_acoustic": True}},
    {"name": "coding", "keywords": ["coding", "code", "programming", "program", "debugging"],
     "profile": {"favorite_genre": "lofi", "favorite_mood": "focused", "target_energy": 0.4, "likes_acoustic": False}},
    {"name": "focus", "keywords": ["focus", "concentrate", "concentration", "concentrating"],
     "profile": {"favorite_genre": "lofi", "favorite_mood": "focused", "target_energy": 0.35, "likes_acoustic": True}},
    {"name": "background", "keywords": ["background"],
     "profile": {"favorite_genre": "ambient", "favorite_mood": "relaxed", "target_energy": 0.3, "likes_acoustic": True}},
    {"name": "workout", "keywords": ["gym", "workout", "working out", "lifting", "lift weights", "weights", "exercise", "exercising", "cardio", "run", "running", "jog", "jogging"],
     "profile": {"favorite_genre": "electronic", "favorite_mood": "intense", "target_energy": 0.9, "likes_acoustic": False}},
    {"name": "party", "keywords": ["party", "partying", "club", "clubbing", "dance", "dancing", "rave"],
     "profile": {"favorite_genre": "pop", "favorite_mood": "euphoric", "target_energy": 0.9, "likes_acoustic": False}},
    {"name": "commute", "keywords": ["drive", "driving", "commute", "commuting", "road", "traffic", "subway", "train"],
     "profile": {"favorite_genre": "pop", "favorite_mood": "uplifting", "target_energy": 0.6, "likes_acoustic": False}},
    {"name": "sleeping", "keywords": ["sleep", "sleeping", "asleep", "bedtime", "insomnia", "nap", "wind down", "before bed"],
     "profile": {"favorite_genre": "ambient", "favorite_mood": "relaxed", "target_energy": 0.15, "likes_acoustic": True}},
    {"name": "relaxing", "keywords": ["relax", "relaxing", "unwind", "reading", "read", "calm"],
     "profile": {"favorite_genre": "ambient", "favorite_mood": "relaxed", "target_energy": 0.3, "likes_acoustic": True}},
    {"name": "cleaning", "keywords": ["cleaning", "clean", "chores", "tidying", "tidy", "housework"],
     "profile": {"favorite_genre": "pop", "favorite_mood": "happy", "target_energy": 0.7, "likes_acoustic": False}},
    {"name": "interview", "keywords": ["interview", "presentation", "meeting", "pitch"],
     "profile": {"favorite_genre": "pop", "favorite_mood": "confident", "target_energy": 0.6, "likes_acoustic": False}},
]


@dataclass
class InterpretedPreference:
    """Result of interpreting a natural-language request."""

    inferred_profile: Dict[str, Any] = field(default_factory=dict)
    matched_examples: List[Dict[str, Any]] = field(default_factory=list)
    confidence: str = "Low"
    unmatched_tokens: List[str] = field(default_factory=list)
    specialization_used: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "inferred_profile": dict(self.inferred_profile),
            "matched_examples": list(self.matched_examples),
            "confidence": self.confidence,
            "unmatched_tokens": list(self.unmatched_tokens),
            "specialization_used": self.specialization_used,
        }


def _load_examples(path: str) -> List[Dict[str, Any]]:
    """Load synthetic examples; return [] on missing/malformed file."""
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (FileNotFoundError, OSError) as exc:
        logger.info("Preference examples not found at %s (%s).", path, type(exc).__name__)
        return []
    except json.JSONDecodeError as exc:
        logger.info("Preference examples at %s are malformed (%s).", path, type(exc).__name__)
        return []
    return data if isinstance(data, list) else []


def _rule_hits(keywords: List[str], lowered: str, tokens: set) -> List[str]:
    """Return the rule keywords present in the text (multiword = substring)."""
    hits = []
    for keyword in keywords:
        if " " in keyword:
            if keyword in lowered:
                hits.append(keyword)
        elif keyword in tokens:
            hits.append(keyword)
    return hits


def interpret_request(
    text: Any, *, examples_path: str = DEFAULT_EXAMPLES_PATH
) -> InterpretedPreference:
    """Infer a structured preference profile from a natural-language request.

    Deterministic keyword matching, documented in ``_ATTRIBUTE_RULES`` and
    ``_ACTIVITY_RULES``. Attribute descriptors are applied first, then
    activity/context rules; each rule fills only fields not already set.

    Confidence (deterministic):
        - "High"   — an activity/context rule matched (rich, situational signal).
        - "Medium" — only an attribute descriptor (or a bare mood word) matched.
        - "Low"    — nothing matched; ``inferred_profile`` is empty.
    """
    if not isinstance(text, str) or not text.strip():
        return InterpretedPreference()

    lowered = text.lower()
    tokens = re.findall(r"[a-z0-9']+", lowered)
    token_set = set(tokens)

    inferred: Dict[str, Any] = {}
    matched_keywords: List[str] = []
    activity_matched = False
    attribute_matched = False

    def apply(rule, is_activity):
        nonlocal activity_matched, attribute_matched
        hits = _rule_hits(rule["keywords"], lowered, token_set)
        if not hits:
            return
        matched_keywords.extend(hits)
        for key, value in rule["profile"].items():
            inferred.setdefault(key, value)
        if is_activity:
            activity_matched = True
        else:
            attribute_matched = True

    # Attribute descriptors first (explicit), then activity/context rules.
    for rule in _ATTRIBUTE_RULES:
        apply(rule, is_activity=False)
    # A bare catalog mood word counts as an attribute-level signal.
    for mood in _CATALOG_MOODS:
        if mood in token_set and "favorite_mood" not in inferred:
            inferred["favorite_mood"] = mood
            matched_keywords.append(mood)
            attribute_matched = True
    for rule in _ACTIVITY_RULES:
        apply(rule, is_activity=True)

    if activity_matched:
        confidence = "High"
    elif attribute_matched:
        confidence = "Medium"
    else:
        confidence = "Low"

    specialization_used = bool(inferred)

    # Few-shot linkage: dataset examples that share a matched keyword.
    examples = _load_examples(examples_path)
    matched_examples = []
    for index, example in enumerate(examples):
        request = str(example.get("user_request", "")).lower()
        if any(keyword in request for keyword in matched_keywords):
            matched_examples.append({"index": index, "user_request": example.get("user_request", "")})

    matched_set = set(matched_keywords)
    unmatched_tokens = []
    seen = set()
    for token in tokens:
        if token in matched_set or token in _STOPWORDS or token in seen:
            continue
        seen.add(token)
        unmatched_tokens.append(token)

    logger.info(
        "Interpreted request: confidence=%s, fields=%d, matched_examples=%d.",
        confidence, len(inferred), len(matched_examples),
    )

    return InterpretedPreference(
        inferred_profile=inferred,
        matched_examples=matched_examples,
        confidence=confidence,
        unmatched_tokens=unmatched_tokens,
        specialization_used=specialization_used,
    )


def merge_interpreted_profile(
    profile: Any, interpreted: InterpretedPreference
) -> Tuple[Any, List[str]]:
    """Fill only missing profile fields from an interpretation.

    Explicit user values are never overwritten. Returns
    (enriched_profile, filled_field_names).
    """
    filled: List[str] = []
    if not isinstance(profile, dict):
        return profile, filled

    enriched = dict(profile)
    for key, value in interpreted.inferred_profile.items():
        if key not in _PROFILE_FIELDS:
            continue
        current = enriched.get(key)
        if current is None or (isinstance(current, str) and current.strip() == ""):
            enriched[key] = value
            filled.append(key)
    return enriched, filled
