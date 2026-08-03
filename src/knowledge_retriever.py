"""
Knowledge retriever for TuneGuide AI (RAG stretch feature).

Extends retrieval beyond the single song CSV by consulting two hand-authored,
local knowledge sources before recommendations are generated:

- ``knowledge/genre_aliases.json`` — maps informal genre spellings to the
  canonical genres present in ``data/songs.csv``.
- ``knowledge/listening_contexts.md`` — maps listening contexts (studying,
  working out, ...) to supported recommendation attributes.

This module only *retrieves and normalizes*. It performs no song scoring or
ranking, invents no mappings, uses no external API/LLM/vector store, and fails
safely when a knowledge file is missing or malformed.

Public API:
- ``RetrievedKnowledge`` / ``KnowledgeRetrievalResult`` — structured evidence.
- ``retrieve_knowledge(...)`` — look up genre alias and/or context guidance.
- ``apply_knowledge_to_profile(...)`` — fill only missing profile fields and
  normalize a genre alias, never overwriting an explicit valid value.
"""

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from src.logging_config import get_logger

logger = get_logger("tuneguide.knowledge")

_ALIASES_FILE = "genre_aliases.json"
_CONTEXTS_FILE = "listening_contexts.md"

# Keys recognized in a listening-contexts section.
_LIST_KEYS = {"suggested_moods", "possible_genres"}
_RANGE_KEYS = {"target_energy"}
_BOOL_KEYS = {"acoustic_preference"}
_STR_KEYS = {"instrumentalness_preference"}


@dataclass
class RetrievedKnowledge:
    """A single piece of retrieved knowledge and which source produced it."""

    source: str
    query: str
    matched_key: str
    attributes: Dict[str, Any] = field(default_factory=dict)
    confidence: str = "high"


@dataclass
class KnowledgeRetrievalResult:
    """Aggregate result of a knowledge retrieval."""

    items: List[RetrievedKnowledge] = field(default_factory=list)
    normalized_genre: Optional[str] = None
    inferred_context: Optional[str] = None
    profile_updates: Dict[str, Any] = field(default_factory=dict)
    sources_used: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """JSON-serializable view (used by trace/result metadata)."""
        return {
            "normalized_genre": self.normalized_genre,
            "inferred_context": self.inferred_context,
            "profile_updates": dict(self.profile_updates),
            "sources_used": list(self.sources_used),
            "items": [
                {
                    "source": item.source,
                    "query": item.query,
                    "matched_key": item.matched_key,
                    "attributes": item.attributes,
                    "confidence": item.confidence,
                }
                for item in self.items
            ],
        }


def _load_aliases(knowledge_dir: str) -> Dict[str, str]:
    """Load genre aliases, returning {} on missing/malformed file."""
    path = os.path.join(knowledge_dir, _ALIASES_FILE)
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        logger.info("Genre alias file not found at %s; skipping alias normalization.", path)
        return {}
    except (json.JSONDecodeError, OSError) as exc:
        logger.info("Genre alias file at %s is malformed (%s); skipping.", path, type(exc).__name__)
        return {}

    if not isinstance(data, dict):
        logger.info("Genre alias file at %s is not an object; skipping.", path)
        return {}
    # Normalize keys to lowercase for case-insensitive matching.
    return {str(k).strip().lower(): str(v) for k, v in data.items()}


def _parse_context_value(key: str, raw: str):
    """Parse a single context attribute value by key type."""
    raw = raw.strip()
    if key in _LIST_KEYS:
        return [part.strip() for part in raw.split(",") if part.strip()]
    if key in _RANGE_KEYS:
        # Expect "low-high"; return (low, high) as floats.
        parts = raw.split("-")
        if len(parts) == 2:
            try:
                return (float(parts[0]), float(parts[1]))
            except ValueError:
                return None
        return None
    if key in _BOOL_KEYS:
        return raw.strip().lower() == "true"
    if key in _STR_KEYS:
        return raw.strip().lower()
    return raw


def _load_contexts(knowledge_dir: str) -> Dict[str, Dict[str, Any]]:
    """Parse listening_contexts.md into {context_name: {attr: value}}.

    Tolerant of malformed lines; returns {} on missing/unreadable file.
    """
    path = os.path.join(knowledge_dir, _CONTEXTS_FILE)
    try:
        with open(path, encoding="utf-8") as handle:
            lines = handle.readlines()
    except (FileNotFoundError, OSError) as exc:
        logger.info("Listening contexts file at %s unavailable (%s); skipping.", path, type(exc).__name__)
        return {}

    contexts: Dict[str, Dict[str, Any]] = {}
    current: Optional[str] = None
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## "):
            current = stripped[3:].strip().lower()
            contexts[current] = {}
        elif stripped.startswith("- ") and current is not None and ":" in stripped:
            body = stripped[2:]
            key, _, value = body.partition(":")
            key = key.strip().strip("`").lower()
            if key in _LIST_KEYS | _RANGE_KEYS | _BOOL_KEYS | _STR_KEYS:
                parsed = _parse_context_value(key, value)
                if parsed is not None:
                    contexts[current][key] = parsed
    return contexts


def _context_profile_updates(attributes: Dict[str, Any]) -> Dict[str, Any]:
    """Derive suggested profile field values from context attributes.

    Only fields that exist on the user profile are produced. Instrumentalness
    preference has no profile field, so it is intentionally omitted here.
    """
    updates: Dict[str, Any] = {}
    moods = attributes.get("suggested_moods") or []
    if moods:
        updates["favorite_mood"] = moods[0]
    energy_range = attributes.get("target_energy")
    if isinstance(energy_range, tuple) and len(energy_range) == 2:
        updates["target_energy"] = round((energy_range[0] + energy_range[1]) / 2.0, 3)
    acoustic = attributes.get("acoustic_preference")
    if isinstance(acoustic, bool):
        updates["likes_acoustic"] = acoustic
    genres = attributes.get("possible_genres") or []
    if genres:
        updates["favorite_genre"] = genres[0]
    return updates


def retrieve_knowledge(
    *,
    genre: Optional[str] = None,
    context: Optional[str] = None,
    knowledge_dir: str = "knowledge",
) -> KnowledgeRetrievalResult:
    """Retrieve genre-alias and/or listening-context knowledge.

    Returns structured evidence identifying which source matched. Unsupported
    aliases/contexts produce no invented mappings (safe fallback).
    """
    items: List[RetrievedKnowledge] = []
    sources_used: List[str] = []
    normalized_genre: Optional[str] = None
    inferred_context: Optional[str] = None
    profile_updates: Dict[str, Any] = {}

    # --- Genre alias normalization ---
    if isinstance(genre, str) and genre.strip():
        query = genre.strip()
        aliases = _load_aliases(knowledge_dir)
        canonical = aliases.get(query.lower())
        if canonical is not None:
            normalized_genre = canonical
            items.append(
                RetrievedKnowledge(
                    source=_ALIASES_FILE,
                    query=query,
                    matched_key=query.lower(),
                    attributes={"normalized_genre": canonical},
                    confidence="high",
                )
            )
            sources_used.append(_ALIASES_FILE)
            logger.info("Normalized genre alias '%s' -> '%s'.", query, canonical)
        else:
            # Not a known alias: leave the genre unchanged, invent nothing.
            normalized_genre = query

    # --- Listening context retrieval ---
    if isinstance(context, str) and context.strip():
        cquery = context.strip()
        contexts = _load_contexts(knowledge_dir)
        matched = contexts.get(cquery.lower())
        if matched:
            inferred_context = cquery.lower()
            items.append(
                RetrievedKnowledge(
                    source=_CONTEXTS_FILE,
                    query=cquery,
                    matched_key=cquery.lower(),
                    attributes=dict(matched),
                    confidence="high",
                )
            )
            sources_used.append(_CONTEXTS_FILE)
            profile_updates = _context_profile_updates(matched)
            logger.info("Matched listening context '%s'.", cquery.lower())
        else:
            logger.info("No knowledge for context '%s'; safe fallback (no updates).", cquery)

    return KnowledgeRetrievalResult(
        items=items,
        normalized_genre=normalized_genre,
        inferred_context=inferred_context,
        profile_updates=profile_updates,
        sources_used=sources_used,
    )


def _differs(current: Any, suggested: Any) -> bool:
    """Type-aware inequality for conflict detection."""
    if isinstance(current, bool) or isinstance(suggested, bool):
        return bool(current) != bool(suggested)
    if isinstance(current, str) and isinstance(suggested, str):
        return current.strip().lower() != suggested.strip().lower()
    try:
        return float(current) != float(suggested)
    except (TypeError, ValueError):
        return current != suggested


def _is_missing(value: Any) -> bool:
    return value is None or (isinstance(value, str) and value.strip() == "")


def apply_knowledge_to_profile(
    profile: Any, knowledge: KnowledgeRetrievalResult
) -> Tuple[Any, List[str], List[str]]:
    """Enrich a profile with retrieved knowledge.

    Precedence rules:
      1. Genre alias normalization replaces an alias spelling with its canonical
         genre (same intent), recording a warning.
      2. Context suggestions fill ONLY missing profile fields.
      3. An explicit, valid user value is never overwritten; when a context
         suggestion conflicts with such a value, a warning is recorded instead.

    Returns (enriched_profile, warnings, applied_fields).
    """
    warnings: List[str] = []
    applied: List[str] = []

    if not isinstance(profile, dict):
        return profile, warnings, applied

    enriched = dict(profile)

    # 1. Genre alias normalization (only when it actually changes the value).
    if knowledge.normalized_genre is not None:
        current_genre = enriched.get("favorite_genre")
        if (
            isinstance(current_genre, str)
            and current_genre.strip()
            and current_genre.strip().lower() != knowledge.normalized_genre.lower()
        ):
            warnings.append(
                f"Normalized genre alias '{current_genre.strip()}' to "
                f"'{knowledge.normalized_genre}'."
            )
            enriched["favorite_genre"] = knowledge.normalized_genre
            applied.append("favorite_genre")

    # 2/3. Fill missing fields from context; never overwrite explicit values.
    for key, suggested in knowledge.profile_updates.items():
        current = enriched.get(key)
        if _is_missing(current):
            enriched[key] = suggested
            applied.append(key)
        elif _differs(current, suggested):
            warnings.append(
                f"Context '{knowledge.inferred_context}' suggested {key}={suggested!r}, "
                f"but keeping user's explicit {key}={current!r}."
            )

    return enriched, warnings, applied
