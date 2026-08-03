"""
Unit tests for the candidate retriever (src/retriever.py).

The retriever only filters/selects candidates: it must preserve dataset order,
never sort or score, never return empty unless the catalog is empty, and fall
back by relaxing constraints when filters remove everything.
"""

from src.retriever import retrieve_candidates


def make_catalog() -> list:
    """A small ordered catalog with known genre/mood/energy values."""
    return [
        {"id": 1, "title": "S1", "artist": "A", "genre": "pop", "mood": "happy", "energy": 0.80},
        {"id": 2, "title": "S2", "artist": "B", "genre": "pop", "mood": "sad", "energy": 0.20},
        {"id": 3, "title": "S3", "artist": "C", "genre": "rock", "mood": "happy", "energy": 0.90},
        {"id": 4, "title": "S4", "artist": "D", "genre": "lofi", "mood": "chill", "energy": 0.30},
        {"id": 5, "title": "S5", "artist": "E", "genre": "pop", "mood": "happy", "energy": 0.50},
    ]


def titles(songs) -> list:
    return [s["title"] for s in songs]


BASE_PROFILE = {
    "favorite_genre": "pop",
    "favorite_mood": "happy",
    "target_energy": 0.80,
}


# ---------------------------------------------------------------------------
# Genre filtering
# ---------------------------------------------------------------------------

def test_genre_filter_keeps_only_exact_matches_in_order():
    result = retrieve_candidates(
        make_catalog(), BASE_PROFILE, genre_filter=True, energy_window=1.0
    )
    # pop songs, in original dataset order.
    assert titles(result) == ["S1", "S2", "S5"]


def test_genre_filter_off_keeps_all():
    result = retrieve_candidates(
        make_catalog(), BASE_PROFILE, genre_filter=False, energy_window=1.0
    )
    assert titles(result) == ["S1", "S2", "S3", "S4", "S5"]


# ---------------------------------------------------------------------------
# Mood filtering
# ---------------------------------------------------------------------------

def test_mood_filter_keeps_only_exact_mood():
    result = retrieve_candidates(
        make_catalog(),
        BASE_PROFILE,
        genre_filter=False,
        mood_filter=True,
        energy_window=1.0,
    )
    assert titles(result) == ["S1", "S3", "S5"]  # happy songs


def test_mood_filter_default_off():
    # With mood filter off, a 'sad' pop song is still retained.
    result = retrieve_candidates(
        make_catalog(), BASE_PROFILE, genre_filter=True, energy_window=1.0
    )
    assert "S2" in titles(result)


# ---------------------------------------------------------------------------
# Energy filtering
# ---------------------------------------------------------------------------

def test_energy_window_filters_by_range():
    result = retrieve_candidates(
        make_catalog(),
        BASE_PROFILE,
        genre_filter=False,
        mood_filter=False,
        energy_window=0.15,
    )
    # target 0.80 +/- 0.15 -> [0.65, 0.95]; only S1 (0.80) and S3 (0.90).
    assert titles(result) == ["S1", "S3"]


def test_energy_window_bounds_are_clamped():
    profile = {**BASE_PROFILE, "target_energy": 0.95}
    result = retrieve_candidates(
        make_catalog(),
        profile,
        genre_filter=False,
        mood_filter=False,
        energy_window=0.25,
    )
    # high clamps to 1.0, low = 0.70 -> S1 (0.80), S3 (0.90).
    assert titles(result) == ["S1", "S3"]


def test_energy_filter_skipped_when_target_missing():
    profile = {"favorite_genre": "pop", "favorite_mood": "happy"}  # no target_energy
    result = retrieve_candidates(
        make_catalog(), profile, genre_filter=False, energy_window=0.05
    )
    assert titles(result) == ["S1", "S2", "S3", "S4", "S5"]


# ---------------------------------------------------------------------------
# Combined filters
# ---------------------------------------------------------------------------

def test_combined_genre_and_energy():
    result = retrieve_candidates(
        make_catalog(),
        BASE_PROFILE,
        genre_filter=True,
        mood_filter=False,
        energy_window=0.15,
    )
    # pop AND energy in [0.65, 0.95] -> only S1.
    assert titles(result) == ["S1"]


def test_combined_all_filters():
    result = retrieve_candidates(
        make_catalog(),
        BASE_PROFILE,
        genre_filter=True,
        mood_filter=True,
        energy_window=0.15,
    )
    # pop AND happy AND energy window -> S1.
    assert titles(result) == ["S1"]


# ---------------------------------------------------------------------------
# Fallback behavior
# ---------------------------------------------------------------------------

def test_fallback_when_no_match_returns_full_catalog():
    profile = {"favorite_genre": "metal", "favorite_mood": "happy", "target_energy": 0.8}
    result = retrieve_candidates(
        make_catalog(), profile, genre_filter=True, mood_filter=True, energy_window=0.1
    )
    # Nothing is 'metal', so filters relax all the way back to the full catalog.
    assert titles(result) == ["S1", "S2", "S3", "S4", "S5"]


def test_fallback_partial_relaxation_keeps_genre_when_possible():
    # pop exists, but no pop song is happy AND in a tiny energy window at 0.2.
    profile = {"favorite_genre": "pop", "favorite_mood": "happy", "target_energy": 0.20}
    result = retrieve_candidates(
        make_catalog(), profile, genre_filter=True, mood_filter=True, energy_window=0.01
    )
    # Relaxing energy first still leaves pop+happy: S1 and S5.
    assert titles(result) == ["S1", "S5"]


# ---------------------------------------------------------------------------
# Candidate limit
# ---------------------------------------------------------------------------

def test_max_candidates_limits_without_reordering():
    result = retrieve_candidates(
        make_catalog(),
        BASE_PROFILE,
        genre_filter=True,
        energy_window=1.0,
        max_candidates=2,
    )
    # pop songs are S1, S2, S5; first 2 in order.
    assert titles(result) == ["S1", "S2"]


def test_max_candidates_larger_than_results_returns_all():
    result = retrieve_candidates(
        make_catalog(),
        BASE_PROFILE,
        genre_filter=True,
        energy_window=1.0,
        max_candidates=99,
    )
    assert titles(result) == ["S1", "S2", "S5"]


# ---------------------------------------------------------------------------
# Empty catalog
# ---------------------------------------------------------------------------

def test_empty_catalog_returns_empty():
    assert retrieve_candidates([], BASE_PROFILE) == []


# ---------------------------------------------------------------------------
# Determinism & order
# ---------------------------------------------------------------------------

def test_deterministic_output():
    catalog = make_catalog()
    first = retrieve_candidates(catalog, BASE_PROFILE, genre_filter=True, energy_window=1.0)
    second = retrieve_candidates(catalog, BASE_PROFILE, genre_filter=True, energy_window=1.0)
    assert titles(first) == titles(second)


def test_dataset_order_preserved_not_sorted():
    # Even though energies differ, retrieval must not sort by energy or anything.
    result = retrieve_candidates(
        make_catalog(), BASE_PROFILE, genre_filter=True, energy_window=1.0
    )
    ids = [s["id"] for s in result]
    assert ids == sorted(ids)  # original catalog is already id-ordered
    assert ids == [1, 2, 5]
