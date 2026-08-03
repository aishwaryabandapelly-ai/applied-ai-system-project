"""
Reliability evaluator for TuneGuide AI (Phase 5).

This module inspects a *completed* recommendation result and reports how
trustworthy it is. It is read-only: it never changes recommendations, scores,
order, or explanations, and it does not re-run scoring or retrieval. It only
measures and reports.

Public API:
- ``ReliabilityCheck`` — the outcome of a single check.
- ``ReliabilityReport`` — the aggregate report.
- ``evaluate_recommendations(...)`` — run all checks over one result.

No external model is used; every metric is computed deterministically.
"""

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.logging_config import get_logger

logger = get_logger("tuneguide.evaluator")

# Same descriptive threshold the explainer uses for "energy close to target".
_ENERGY_CLOSE_THRESHOLD = 0.15

# Placeholder summary the explainer emits for malformed entries; it must NOT
# count as valid explanation coverage.
_MALFORMED_SUMMARY = "No explanation available for this item."

# Checks whose failure makes the whole report fail.
_CRITICAL_CHECKS = {
    "no_duplicate_songs",
    "explanation_coverage",
    "score_validity_and_order",
    "result_completeness",
}

# Reliability score weights (sum = 100). See evaluate_recommendations docstring.
_WEIGHTS = {
    "duplicate": 20,
    "coverage": 20,
    "order": 20,
    "alignment": 20,
    "diversity": 20,
}


@dataclass
class ReliabilityCheck:
    """The outcome of a single reliability check."""

    name: str
    passed: bool
    value: Any
    message: str


@dataclass
class ReliabilityReport:
    """Aggregate reliability report for one recommendation result."""

    passed: bool
    score: int
    checks: List[ReliabilityCheck] = field(default_factory=list)
    summary: str = ""
    metrics: Dict[str, Any] = field(default_factory=dict)


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _song_key(song: Any):
    """A stable identity for a song: prefer id, else (title, artist)."""
    if isinstance(song, dict):
        if song.get("id") is not None:
            return ("id", song["id"])
        return ("title_artist", song.get("title"), song.get("artist"))
    return ("object", id(song))


def _ratio(unique: int, total: int) -> float:
    """unique/total, or 1.0 when there is nothing to divide (vacuous)."""
    return unique / total if total else 1.0


def evaluate_recommendations(
    recommendations: List[Any],
    explanations: List[Any],
    profile: Any,
    *,
    requested_k: Optional[int],
    retrieved_candidate_count: Optional[int],
) -> ReliabilityReport:
    """Evaluate the reliability of a completed recommendation result.

    Reliability score (0-100), five equally weighted dimensions:
        duplicate check       20  -> full if no duplicate songs, else 0
        explanation coverage  20  -> 20 * (valid explanations / recommendations)
        score validity/order  20  -> full if scores are numeric, finite, and
                                      in non-increasing order, else 0
        preference alignment  20  -> 20 * mean fraction of {genre, mood, energy}
                                      signals matched across recommendations
        diversity             20  -> 20 * mean(unique_artist_ratio,
                                      unique_genre_ratio)

    Overall ``passed`` is gated only by the CRITICAL checks (duplicates,
    coverage, score validity/order, result completeness). Low preference
    alignment or diversity lower the score but do not fail the report.
    """
    profile = profile if isinstance(profile, dict) else {}
    recommendations = recommendations or []
    explanations = explanations or []
    num_recs = len(recommendations)

    logger.info("Reliability evaluation start for %d recommendation(s).", num_recs)

    checks: List[ReliabilityCheck] = []

    # --- 1. Duplicate check (critical) ---
    keys = [_song_key(rec[0]) for rec in recommendations]
    duplicate_count = len(keys) - len(set(keys))
    checks.append(
        ReliabilityCheck(
            name="no_duplicate_songs",
            passed=duplicate_count == 0,
            value=duplicate_count,
            message=(
                "No duplicate songs."
                if duplicate_count == 0
                else f"Found {duplicate_count} duplicate song entry(ies)."
            ),
        )
    )

    # --- 2. Explanation coverage (critical) ---
    valid_explanations = 0
    for i, rec in enumerate(recommendations):
        exp = explanations[i] if i < len(explanations) else None
        summary = str(getattr(exp, "summary", "") or "").strip()
        if not summary or summary == _MALFORMED_SUMMARY:
            continue
        # If both titles are known, they must correspond.
        rec_title = rec[0].get("title") if isinstance(rec[0], dict) else None
        exp_title = getattr(exp, "song_title", None)
        if rec_title and exp_title and rec_title != exp_title:
            continue
        valid_explanations += 1
    coverage = valid_explanations / num_recs if num_recs else 1.0
    checks.append(
        ReliabilityCheck(
            name="explanation_coverage",
            passed=coverage >= 0.999,
            value=round(coverage, 4),
            message=f"{valid_explanations}/{num_recs} recommendations have a valid explanation.",
        )
    )

    # --- 3. Score validity and order (critical) ---
    scores: List[Any] = [rec[1] if len(rec) > 1 else None for rec in recommendations]
    numeric_finite = all(_is_number(s) and math.isfinite(s) for s in scores)
    descending = numeric_finite and all(
        scores[i] >= scores[i + 1] for i in range(len(scores) - 1)
    )
    score_ok = numeric_finite and descending
    checks.append(
        ReliabilityCheck(
            name="score_validity_and_order",
            passed=score_ok,
            value={"numeric_finite": numeric_finite, "descending": descending},
            message=(
                "Scores are numeric, finite, and in descending order."
                if score_ok
                else "Scores are non-numeric, non-finite, or not in descending order."
            ),
        )
    )

    # --- 4. Preference alignment (non-critical metric) ---
    favorite_genre = profile.get("favorite_genre")
    favorite_mood = profile.get("favorite_mood")
    target_energy = profile.get("target_energy")
    genre_matches = mood_matches = energy_close = 0
    signal_sum = 0.0
    for rec in recommendations:
        song = rec[0] if isinstance(rec[0], dict) else {}
        g = bool(favorite_genre) and song.get("genre") == favorite_genre
        m = bool(favorite_mood) and song.get("mood") == favorite_mood
        e = (
            _is_number(target_energy)
            and _is_number(song.get("energy"))
            and abs(song.get("energy") - target_energy) <= _ENERGY_CLOSE_THRESHOLD
        )
        genre_matches += int(g)
        mood_matches += int(m)
        energy_close += int(e)
        signal_sum += (int(g) + int(m) + int(e)) / 3.0
    alignment = signal_sum / num_recs if num_recs else 1.0
    checks.append(
        ReliabilityCheck(
            name="preference_alignment",
            passed=alignment >= 0.5,
            value=round(alignment, 4),
            message=(
                f"Average preference alignment {alignment:.2f} "
                f"(genre={genre_matches}, mood={mood_matches}, energy_close={energy_close})."
            ),
        )
    )

    # --- 5. Diversity (non-critical metric) ---
    artists = [rec[0].get("artist") if isinstance(rec[0], dict) else None for rec in recommendations]
    genres = [rec[0].get("genre") if isinstance(rec[0], dict) else None for rec in recommendations]
    unique_artist_ratio = _ratio(len(set(artists)), num_recs)
    unique_genre_ratio = _ratio(len(set(genres)), num_recs)
    repeated_artist_count = num_recs - len(set(artists)) if num_recs else 0
    repeated_genre_count = num_recs - len(set(genres)) if num_recs else 0
    diversity_fraction = (unique_artist_ratio + unique_genre_ratio) / 2.0
    checks.append(
        ReliabilityCheck(
            name="diversity",
            passed=diversity_fraction >= 0.5,
            value=round(diversity_fraction, 4),
            message=(
                f"Unique artist ratio {unique_artist_ratio:.2f}, "
                f"unique genre ratio {unique_genre_ratio:.2f}."
            ),
        )
    )

    # --- 6. Result completeness (critical) ---
    completeness_issues = []
    if requested_k is not None and num_recs > requested_k:
        completeness_issues.append(f"returned {num_recs} > requested_k {requested_k}")
    if retrieved_candidate_count is not None and num_recs > retrieved_candidate_count:
        completeness_issues.append(
            f"returned {num_recs} > retrieved candidates {retrieved_candidate_count}"
        )
    checks.append(
        ReliabilityCheck(
            name="result_completeness",
            passed=not completeness_issues,
            value=num_recs,
            message=(
                "Result counts are consistent."
                if not completeness_issues
                else "Impossible result counts: " + "; ".join(completeness_issues) + "."
            ),
        )
    )

    # --- Reliability score (deterministic, documented weights) ---
    by_name = {c.name: c for c in checks}
    score = (
        _WEIGHTS["duplicate"] * (1 if by_name["no_duplicate_songs"].passed else 0)
        + _WEIGHTS["coverage"] * coverage
        + _WEIGHTS["order"] * (1 if by_name["score_validity_and_order"].passed else 0)
        + _WEIGHTS["alignment"] * alignment
        + _WEIGHTS["diversity"] * diversity_fraction
    )
    score = int(round(max(0.0, min(100.0, score))))

    overall_passed = all(c.passed for c in checks if c.name in _CRITICAL_CHECKS)

    metrics = {
        "returned_count": num_recs,
        "requested_k": requested_k,
        "retrieved_candidate_count": retrieved_candidate_count,
        "duplicate_count": duplicate_count,
        "explanation_coverage": round(coverage, 4),
        "preference_alignment": round(alignment, 4),
        "genre_match_count": genre_matches,
        "mood_match_count": mood_matches,
        "energy_close_count": energy_close,
        "unique_artist_ratio": round(unique_artist_ratio, 4),
        "unique_genre_ratio": round(unique_genre_ratio, 4),
        "repeated_artist_count": repeated_artist_count,
        "repeated_genre_count": repeated_genre_count,
        "reliability_score": score,
    }

    summary = _build_summary(
        overall_passed, num_recs, coverage, score_ok, diversity_fraction, checks, score
    )

    critical_failures = [
        c.name for c in checks if c.name in _CRITICAL_CHECKS and not c.passed
    ]
    logger.info(
        "Reliability evaluation complete: %d checks, score=%d, passed=%s, critical_failures=%s.",
        len(checks),
        score,
        overall_passed,
        critical_failures or "none",
    )

    return ReliabilityReport(
        passed=overall_passed,
        score=score,
        checks=checks,
        summary=summary,
        metrics=metrics,
    )


def _build_summary(
    passed: bool,
    num_recs: int,
    coverage: float,
    score_ok: bool,
    diversity_fraction: float,
    checks: List[ReliabilityCheck],
    score: int,
) -> str:
    """Deterministic, claim-safe one/two-sentence summary."""
    if num_recs == 0:
        return "No recommendations were returned; reliability checks are vacuously satisfied."

    if not passed:
        failures = [
            c.name for c in checks if c.name in _CRITICAL_CHECKS and not c.passed
        ]
        return (
            f"Reliability checks failed ({', '.join(failures)}). Score {score}/100."
        )

    if coverage >= 0.999:
        coverage_desc = "full explanation coverage"
    elif coverage >= 0.5:
        coverage_desc = "partial explanation coverage"
    else:
        coverage_desc = "weak explanation coverage"

    ranking_desc = "valid ranking" if score_ok else "invalid ranking"

    if diversity_fraction >= 0.8:
        diversity_desc = "high"
    elif diversity_fraction >= 0.5:
        diversity_desc = "moderate"
    else:
        diversity_desc = "low"

    return (
        f"Reliability checks passed with {coverage_desc} and {ranking_desc}. "
        f"Diversity was {diversity_desc}."
    )
