"""
Candidate retrieval for TuneGuide AI (Phase 2).

The retriever prepares a set of candidate songs *before* scoring. It only
filters/selects candidates — it performs no scoring, ranking, or sorting, and
it preserves the dataset's original order. Later phases feed these candidates
into the existing (unchanged) scoring pipeline.

Guarantees:
- Deterministic: no randomness; input order is preserved.
- Never returns an empty list unless the catalog itself is empty. If filters
  remove every song, constraints are progressively relaxed until at least one
  candidate remains (ultimately the full catalog).
"""

from typing import Any, Dict, List, Optional

from src.logging_config import get_logger

logger = get_logger("tuneguide.retriever")


def _is_number(value: Any) -> bool:
    """True for real numbers (excluding bool)."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _matches(
    song: Dict[str, Any],
    profile: Dict[str, Any],
    use_genre: bool,
    use_mood: bool,
    use_energy: bool,
    window: float,
) -> bool:
    """Return True if a song passes the enabled filters.

    A filter whose profile value is missing/unusable is skipped (treated as a
    no-op) rather than excluding everything, which keeps retrieval graceful.
    """
    if use_genre:
        favorite_genre = profile.get("favorite_genre")
        if favorite_genre and song.get("genre") != favorite_genre:
            return False

    if use_mood:
        favorite_mood = profile.get("favorite_mood")
        if favorite_mood and song.get("mood") != favorite_mood:
            return False

    if use_energy:
        target = profile.get("target_energy")
        if _is_number(target):
            low = max(0.0, target - window)
            high = min(1.0, target + window)
            energy = song.get("energy")
            if not (_is_number(energy) and low <= energy <= high):
                return False

    return True


def retrieve_candidates(
    songs: List[Dict[str, Any]],
    profile: Dict[str, Any],
    *,
    genre_filter: bool = True,
    mood_filter: bool = False,
    energy_window: float = 0.25,
    max_candidates: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Retrieve candidate songs for a profile.

    Args:
        songs: the catalog (list of song dicts). Order is preserved.
        profile: user preferences (``favorite_genre``, ``favorite_mood``,
            ``target_energy``). Missing values simply disable that filter.
        genre_filter: if True, keep only exact genre matches.
        mood_filter: if True, keep only exact mood matches.
        energy_window: keep songs whose energy is within
            ``target_energy ± energy_window`` (bounds clamped to [0, 1]).
        max_candidates: if set, return only the first N candidates (order kept).

    Returns:
        A list of candidate song dicts in the original dataset order. Never
        empty unless the catalog is empty (progressive fallback guarantees at
        least one candidate otherwise).
    """
    profile = profile or {}
    window = max(0.0, energy_window)

    logger.info(
        "Retrieval start: %d songs; genre_filter=%s, mood_filter=%s, "
        "energy_window=%.3f, max_candidates=%s",
        len(songs),
        genre_filter,
        mood_filter,
        window,
        max_candidates,
    )

    if not songs:
        logger.info("Catalog is empty; returning no candidates.")
        return []

    # Progressive relaxation: start with the requested filters, then drop them
    # one at a time (energy, then mood, then genre) until candidates remain.
    # The final config keeps all songs, so a non-empty catalog always yields
    # at least one candidate.
    configs = []
    for cfg in (
        (genre_filter, mood_filter, True),   # requested
        (genre_filter, mood_filter, False),  # drop energy
        (genre_filter, False, False),        # drop mood
        (False, False, False),               # drop genre -> full catalog
    ):
        if cfg not in configs:
            configs.append(cfg)

    result: List[Dict[str, Any]] = []
    for attempt, (use_genre, use_mood, use_energy) in enumerate(configs):
        filtered = [
            song
            for song in songs
            if _matches(song, profile, use_genre, use_mood, use_energy, window)
        ]
        logger.info(
            "Attempt %d (genre=%s, mood=%s, energy=%s): %d candidates",
            attempt,
            use_genre,
            use_mood,
            use_energy,
            len(filtered),
        )
        if filtered:
            result = filtered
            if attempt > 0:
                logger.info(
                    "Fallback activated: relaxed filters to "
                    "genre=%s, mood=%s, energy=%s.",
                    use_genre,
                    use_mood,
                    use_energy,
                )
            break

    if max_candidates is not None:
        result = result[:max_candidates]
        logger.info("Applied max_candidates=%s.", max_candidates)

    logger.info("Final candidate count: %d.", len(result))
    return result
