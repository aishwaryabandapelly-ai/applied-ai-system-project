"""
Evidence-based explanation generator for TuneGuide AI (Phase 4).

This module turns the reason strings the recommender already produces into
structured, human-readable explanations. It does NOT re-implement or duplicate
the scoring formula, and it never invents information: every claim is derived
strictly from the song's own attributes, the validated profile, the numeric
score, and the existing raw reason strings.

Public API:
- ``RecommendationExplanation`` — structured explanation for one recommendation.
- ``generate_explanation(song, score, raw_reasons, profile)`` — build one.
- ``generate_explanations(recommendations, profile)`` — batch helper used by
  the agent; logs start/count and handles malformed input safely.

No external LLM or API is used; everything here is deterministic.
"""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.logging_config import get_logger

logger = get_logger("tuneguide.explainer")

# Matches a numeric contribution like "(+2.0)" or "(-0.25)" inside a reason.
_CONTRIBUTION_RE = re.compile(r"\(([+-]?\d+(?:\.\d+)?)\)")

# Keyword -> canonical evidence category for the recommender's known reasons.
_KNOWN_CATEGORIES = [
    ("genre match", "genre match"),
    ("mood match", "mood match"),
    ("energy closeness", "energy closeness"),
    ("acoustic preference", "acoustic preference"),
    ("popularity bonus", "popularity bonus"),
    ("instrumentalness bonus", "instrumentalness bonus"),
]

# How close (absolute energy difference) counts as "close to your target".
# This is a descriptive threshold on raw attributes, not part of the score.
_ENERGY_CLOSE_THRESHOLD = 0.15


@dataclass
class RecommendationExplanation:
    """A structured, evidence-only explanation for a single recommendation."""

    song_title: str
    artist: str
    score: Optional[float]
    summary: str
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    confidence: str = "Low"
    limitations: List[str] = field(default_factory=list)


def _is_number(value: Any) -> bool:
    """True for real numbers (excluding bool)."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _normalize_reasons(raw_reasons: Any) -> List[str]:
    """Normalize reasons into a list of non-empty strings.

    Accepts the recommender's list of reason strings, its comma-joined
    explanation string, or malformed input (returns an empty list, logged).
    Individual reason strings contain no commas, so splitting on ',' is safe.
    """
    if raw_reasons is None:
        return []
    if isinstance(raw_reasons, str):
        return [part.strip() for part in raw_reasons.split(",") if part.strip()]
    if isinstance(raw_reasons, (list, tuple)):
        cleaned = []
        for item in raw_reasons:
            if item is None:
                continue
            text = str(item).strip()
            if text:
                cleaned.append(text)
        return cleaned
    # Anything else (int, dict, etc.) is malformed input.
    logger.info(
        "Malformed raw_reasons of type %s handled safely; treating as no evidence.",
        type(raw_reasons).__name__,
    )
    return []


def _extract_contribution(reason: str) -> Optional[float]:
    """Pull the numeric contribution out of a reason string, if present."""
    match = _CONTRIBUTION_RE.search(reason)
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def _classify(reason: str) -> str:
    """Map a raw reason string to a canonical evidence category."""
    text = reason.lower()
    if "diversity penalty" in text or "repeated" in text:
        if "artist" in text:
            return "diversity penalty (repeated artist)"
        if "genre" in text:
            return "diversity penalty (repeated genre)"
        return "diversity penalty"
    for keyword, label in _KNOWN_CATEGORIES:
        if keyword in text:
            return label
    # Unknown reason: keep it as evidence but label it plainly rather than
    # inventing a meaning for it.
    return "other"


def generate_explanation(
    song: Any,
    score: Any,
    raw_reasons: Any,
    profile: Any,
) -> RecommendationExplanation:
    """Build a structured explanation for one recommendation.

    Evidence comes only from ``raw_reasons`` (parsed), while the summary uses
    the song's own attributes and the validated profile. Nothing outside those
    inputs is asserted.

    Confidence rule (transparent, deterministic, mode-independent):
        - ``direct_matches`` = how many of {genre match, mood match} are present.
        - ``has_penalty`` = whether any diversity penalty was applied.
        - High:   two direct matches AND no diversity penalty.
        - Medium: exactly one direct match, OR two matches but a penalty applied.
        - Low:    no direct preference match.
      The numeric score is preserved in the result for the reader to weigh, but
      the label itself is based only on supported preference signals so it does
      not shift with scoring mode / weight scaling.
    """
    song = song if isinstance(song, dict) else {}
    profile = profile if isinstance(profile, dict) else {}

    reasons = _normalize_reasons(raw_reasons)

    evidence: List[Dict[str, Any]] = [
        {
            "category": _classify(reason),
            "contribution": _extract_contribution(reason),
            "detail": reason,
        }
        for reason in reasons
    ]

    categories = {item["category"] for item in evidence}
    direct_matches = sum(
        1 for category in ("genre match", "mood match") if category in categories
    )
    has_penalty = any(category.startswith("diversity penalty") for category in categories)

    # --- Confidence (see docstring for the rule) ---
    if direct_matches == 2 and not has_penalty:
        confidence = "High"
    elif direct_matches >= 1:
        confidence = "Medium"
    else:
        confidence = "Low"

    # --- Summary (only genre/mood matches + raw energy closeness) ---
    matched_phrases = []
    if "genre match" in categories:
        matched_phrases.append("your preferred genre")
    if "mood match" in categories:
        matched_phrases.append("your preferred mood")

    target_energy = profile.get("target_energy")
    song_energy = song.get("energy")
    energy_close = (
        _is_number(target_energy)
        and _is_number(song_energy)
        and abs(song_energy - target_energy) <= _ENERGY_CLOSE_THRESHOLD
    )

    clauses = []
    if matched_phrases:
        clauses.append("it matches " + " and ".join(matched_phrases))
    if energy_close:
        clauses.append("its energy level is close to your target")

    if clauses:
        summary = "This song is recommended because " + " and ".join(clauses) + "."
    else:
        summary = (
            "This song is recommended as one of the closest available options, "
            "though it does not directly match your preferred genre, mood, or "
            "target energy."
        )

    # --- Limitations (only what the data supports) ---
    limitations = ["Based on song metadata rather than real listening history."]
    if has_penalty:
        limitations.append("A diversity penalty affected this song's final score.")
    if direct_matches == 0:
        limitations.append(
            "No direct genre or mood match; recommended by closeness on other attributes."
        )

    # --- Score coercion (robust to non-numeric input) ---
    try:
        score_value: Optional[float] = float(score)
    except (TypeError, ValueError):
        score_value = None

    return RecommendationExplanation(
        song_title=song.get("title") or "Unknown title",
        artist=song.get("artist") or "Unknown artist",
        score=score_value,
        summary=summary,
        evidence=evidence,
        confidence=confidence,
        limitations=limitations,
    )


def generate_explanations(
    recommendations: List[Any], profile: Any
) -> List[RecommendationExplanation]:
    """Generate one explanation per recommendation, preserving order.

    ``recommendations`` are the ``(song, score, reason_string)`` tuples produced
    by ``recommend_songs``. Malformed entries do not crash the batch; they yield
    a minimal explanation instead.
    """
    logger.info(
        "Explanation generation start for %d recommendation(s).", len(recommendations)
    )

    explanations: List[RecommendationExplanation] = []
    for item in recommendations:
        try:
            song, score, raw_reasons = item[0], item[1], item[2]
        except (TypeError, IndexError, KeyError):
            logger.info("Malformed recommendation entry handled safely.")
            explanations.append(
                RecommendationExplanation(
                    song_title="Unknown title",
                    artist="Unknown artist",
                    score=None,
                    summary="No explanation available for this item.",
                    evidence=[],
                    confidence="Low",
                    limitations=["Explanation input was malformed."],
                )
            )
            continue
        explanations.append(generate_explanation(song, score, raw_reasons, profile))

    logger.info("Generated %d explanation(s).", len(explanations))
    return explanations
