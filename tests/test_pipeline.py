"""
Regression tests for the existing functional recommendation pipeline.

These lock in the *current* behavior of the functions the CLI actually uses
(``load_songs``, ``get_scoring_weights``, ``score_song``, ``recommend_songs``)
so later phases can refactor safely. They do not add or change behavior.

Most tests use small in-memory song dicts; ``data/songs.csv`` is only used for
the CSV-loading test and the CLI-facing integration regression.
"""

import pytest

from src.recommender import (
    get_scoring_weights,
    score_song,
    recommend_songs,
    load_songs,
)


def make_song(**overrides) -> dict:
    """Build a song dict with all fields score_song/recommend_songs read."""
    song = {
        "id": 1,
        "title": "Test Song",
        "artist": "Test Artist",
        "genre": "pop",
        "mood": "happy",
        "energy": 0.5,
        "acousticness": 0.5,
        "popularity": 50,
        "instrumentalness": 0.0,
    }
    song.update(overrides)
    return song


# ---------------------------------------------------------------------------
# get_scoring_weights
# ---------------------------------------------------------------------------

def test_balanced_weights_are_expected():
    """(1) balanced mode returns the documented weight set."""
    assert get_scoring_weights("balanced") == {
        "genre": 2.0,
        "mood": 1.0,
        "energy": 1.0,
        "acoustic": 1.0,
    }


def test_invalid_mode_falls_back_to_balanced():
    """(2) an unknown mode falls back to balanced weights."""
    assert get_scoring_weights("does_not_exist") == get_scoring_weights("balanced")


# ---------------------------------------------------------------------------
# score_song
# ---------------------------------------------------------------------------

def test_score_song_returns_number_and_nonempty_reasons():
    """(3) score is numeric and reasons is a non-empty list of strings."""
    user = {
        "favorite_genre": "pop",
        "favorite_mood": "happy",
        "target_energy": 0.5,
        "likes_acoustic": False,
    }
    score, reasons = score_song(user, make_song())

    assert isinstance(score, (int, float))
    assert isinstance(reasons, list)
    assert len(reasons) > 0
    assert all(isinstance(r, str) for r in reasons)


def test_matching_genre_and_mood_add_expected_contributions():
    """(4) a genre+mood match yields the +2.0 / +1.0 reasons and outscores a miss."""
    user = {
        "favorite_genre": "pop",
        "favorite_mood": "happy",
        "target_energy": 0.5,
        "likes_acoustic": False,
    }
    match = make_song(genre="pop", mood="happy")
    miss = make_song(genre="rock", mood="sad")

    match_score, match_reasons = score_song(user, match)
    miss_score, _ = score_song(user, miss)

    assert "genre match (+2.0)" in match_reasons
    assert "mood match (+1.0)" in match_reasons
    # The +2.0 genre and +1.0 mood contributions must make the match score higher.
    assert match_score == pytest.approx(miss_score + 3.0)


def test_energy_closeness_is_highest_on_exact_match():
    """(5) energy_score peaks (+1.00) when song energy equals target energy."""
    exact_user = {
        "favorite_genre": "x",
        "favorite_mood": "x",
        "target_energy": 0.5,
        "likes_acoustic": False,
    }
    far_user = {**exact_user, "target_energy": 0.0}
    song = make_song(energy=0.5, genre="none", mood="none")

    exact_score, exact_reasons = score_song(exact_user, song)
    far_score, _ = score_song(far_user, song)

    assert "energy closeness (+1.00)" in exact_reasons
    # energy 0.5 vs target 0.5 (closeness 1.0) beats vs target 0.0 (closeness 0.5).
    assert exact_score == pytest.approx(far_score + 0.5)


def test_acoustic_preference_flips_with_likes_acoustic():
    """(6) likes_acoustic True vs False changes the acoustic contribution."""
    base = {
        "favorite_genre": "none",
        "favorite_mood": "none",
        "target_energy": 0.5,
    }
    song = make_song(acousticness=0.8, genre="none", mood="none", energy=0.5)

    likes_score, _ = score_song({**base, "likes_acoustic": True}, song)
    dislikes_score, _ = score_song({**base, "likes_acoustic": False}, song)

    # True -> acousticness (0.8); False -> 1 - acousticness (0.2); diff 0.6.
    assert likes_score == pytest.approx(dislikes_score + 0.6)


# ---------------------------------------------------------------------------
# recommend_songs
# ---------------------------------------------------------------------------

def _diverse_catalog() -> list:
    """A small catalog with known, separable base scores for the pop/happy user."""
    return [
        make_song(id=1, title="A", artist="X", genre="pop", mood="happy",
                  acousticness=0.0, popularity=90),   # base 5.9
        make_song(id=2, title="B", artist="Y", genre="pop", mood="sad",
                  acousticness=0.0, popularity=50),   # base 4.5, repeats genre pop
        make_song(id=3, title="C", artist="X", genre="rock", mood="happy",
                  acousticness=0.0, popularity=40),   # base 3.4, repeats artist X
    ]


POP_HAPPY_USER = {
    "favorite_genre": "pop",
    "favorite_mood": "happy",
    "target_energy": 0.5,
    "likes_acoustic": False,
}


def test_recommend_returns_exactly_k():
    """(7) returns exactly k items when the catalog has at least k songs."""
    recs = recommend_songs(POP_HAPPY_USER, _diverse_catalog(), k=2)
    assert len(recs) == 2


def test_recommendations_sorted_by_adjusted_score_desc():
    """(8) results are ordered highest adjusted score first."""
    recs = recommend_songs(POP_HAPPY_USER, _diverse_catalog(), k=3)
    scores = [score for _song, score, _reason in recs]
    assert scores == sorted(scores, reverse=True)


def test_diversity_penalties_applied():
    """(9) repeated genre (-0.25) and repeated artist (-0.50) penalties appear."""
    recs = recommend_songs(POP_HAPPY_USER, _diverse_catalog(), k=3)
    all_reasons = " || ".join(reason for _song, _score, reason in recs)

    assert "diversity penalty: repeated genre (-0.25)" in all_reasons
    assert "diversity penalty: repeated artist (-0.50)" in all_reasons


# ---------------------------------------------------------------------------
# load_songs (uses the real CSV)
# ---------------------------------------------------------------------------

def test_load_songs_converts_types():
    """(10) load_songs reads the CSV and coerces numeric/boolean fields."""
    songs = load_songs("data/songs.csv")

    assert len(songs) == 18
    first = songs[0]
    assert isinstance(first["id"], int)
    assert isinstance(first["energy"], float)
    assert isinstance(first["tempo_bpm"], float)
    assert isinstance(first["valence"], float)
    assert isinstance(first["danceability"], float)
    assert isinstance(first["acousticness"], float)
    assert isinstance(first["popularity"], int)
    assert isinstance(first["release_decade"], int)
    assert isinstance(first["instrumentalness"], float)
    assert isinstance(first["is_explicit"], bool)


# ---------------------------------------------------------------------------
# CLI-facing integration regression
# ---------------------------------------------------------------------------

def test_cli_top_recommendation_unchanged():
    """(11) the High-Energy Pop profile still ranks 'Sunrise City' first at 5.58."""
    songs = load_songs("data/songs.csv")
    high_energy_pop = {
        "favorite_genre": "pop",
        "favorite_mood": "happy",
        "target_energy": 0.85,
        "likes_acoustic": False,
    }
    recs = recommend_songs(high_energy_pop, songs, k=5, mode="balanced")

    assert len(recs) == 5
    top_song, top_score, _reason = recs[0]
    assert top_song["title"] == "Sunrise City"
    assert top_score == pytest.approx(5.58, abs=0.01)
