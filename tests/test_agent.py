"""
Unit tests for the recommendation agent (src/agent.py).

The agent is only a coordinator: it must wire validation -> retrieval ->
recommend_songs without adding scoring/ranking logic, return structured
results (never raising on invalid input), and populate metadata.
"""

from src.agent import RecommendationAgent, RecommendationResult
from src.retriever import retrieve_candidates
from src.recommender import recommend_songs, load_songs


def make_song(**overrides) -> dict:
    song = {
        "id": 1,
        "title": "Song",
        "artist": "Artist",
        "genre": "pop",
        "mood": "happy",
        "energy": 0.8,
        "acousticness": 0.2,
        "popularity": 50,
        "instrumentalness": 0.0,
    }
    song.update(overrides)
    return song


def make_catalog() -> list:
    return [
        make_song(id=1, title="S1", artist="A", genre="pop", mood="happy", energy=0.80, popularity=90),
        make_song(id=2, title="S2", artist="B", genre="pop", mood="happy", energy=0.75, popularity=60),
        make_song(id=3, title="S3", artist="C", genre="pop", mood="sad", energy=0.60, popularity=50),
        make_song(id=4, title="S4", artist="D", genre="rock", mood="happy", energy=0.90, popularity=40),
        make_song(id=5, title="S5", artist="E", genre="lofi", mood="chill", energy=0.30, popularity=30),
        make_song(id=6, title="S6", artist="F", genre="pop", mood="happy", energy=0.50, popularity=70),
    ]


VALID_PROFILE = {
    "favorite_genre": "pop",
    "favorite_mood": "happy",
    "target_energy": 0.80,
    "likes_acoustic": False,
}


# ---------------------------------------------------------------------------
# Valid request
# ---------------------------------------------------------------------------

def test_valid_request_succeeds():
    agent = RecommendationAgent(make_catalog())
    result = agent.recommend(VALID_PROFILE, k=3)

    assert isinstance(result, RecommendationResult)
    assert result.success is True
    assert result.errors == []
    assert len(result.recommendations) > 0
    assert result.cleaned_k == 3


# ---------------------------------------------------------------------------
# Invalid request
# ---------------------------------------------------------------------------

def test_invalid_request_returns_failure_without_raising():
    agent = RecommendationAgent(make_catalog())
    bad_profile = {"favorite_mood": "happy", "target_energy": 0.8, "likes_acoustic": False}
    # missing favorite_genre
    result = agent.recommend(bad_profile, k=3)

    assert result.success is False
    assert result.errors
    assert result.recommendations == []


def test_invalid_k_returns_failure():
    agent = RecommendationAgent(make_catalog())
    result = agent.recommend(VALID_PROFILE, k=0)
    assert result.success is False
    assert any("greater than 0" in e for e in result.errors)


# ---------------------------------------------------------------------------
# Warnings preserved
# ---------------------------------------------------------------------------

def test_warnings_preserved_from_validation():
    agent = RecommendationAgent(make_catalog())  # 6 songs
    result = agent.recommend(VALID_PROFILE, k=100)  # exceeds catalog
    assert result.success is True
    assert any("reducing k" in w for w in result.warnings)
    assert result.cleaned_k == 6


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------

def test_metadata_populated():
    agent = RecommendationAgent(make_catalog())
    result = agent.recommend(VALID_PROFILE, k=3, mode="balanced")

    meta = result.metadata
    assert meta["total_catalog_size"] == 6
    assert "retrieved_candidates" in meta
    assert "returned_recommendations" in meta
    assert meta["scoring_mode"] == "balanced"


def test_metadata_counts_match_result():
    agent = RecommendationAgent(make_catalog())
    result = agent.recommend(VALID_PROFILE, k=3)

    assert result.metadata["returned_recommendations"] == len(result.recommendations)


# ---------------------------------------------------------------------------
# Retrieved candidate count
# ---------------------------------------------------------------------------

def test_retrieved_candidate_count_matches_retriever():
    catalog = make_catalog()
    agent = RecommendationAgent(catalog)
    result = agent.recommend(VALID_PROFILE, k=3)

    # Reproduce retrieval with the same (default) options and cleaned profile.
    candidates = retrieve_candidates(catalog, result.cleaned_profile)
    assert result.metadata["retrieved_candidates"] == len(candidates)


# ---------------------------------------------------------------------------
# Recommendations come from recommend_songs()
# ---------------------------------------------------------------------------

def test_recommendations_come_from_recommend_songs():
    catalog = make_catalog()
    agent = RecommendationAgent(catalog)
    result = agent.recommend(VALID_PROFILE, k=3, mode="balanced")

    candidates = retrieve_candidates(catalog, result.cleaned_profile)
    expected = recommend_songs(result.cleaned_profile, candidates, k=3, mode="balanced")

    assert result.recommendations == expected


def test_agent_only_ranks_retrieved_candidates():
    # With genre filtering on, non-pop songs should never appear in results.
    agent = RecommendationAgent(make_catalog())
    result = agent.recommend(VALID_PROFILE, k=6)
    genres = {song["genre"] for song, _score, _reason in result.recommendations}
    assert genres == {"pop"}


# ---------------------------------------------------------------------------
# Logging does not crash
# ---------------------------------------------------------------------------

def test_logging_does_not_crash_across_calls():
    agent = RecommendationAgent(make_catalog())
    # Multiple calls (valid + invalid) should not raise from logging.
    agent.recommend(VALID_PROFILE, k=3)
    agent.recommend({"favorite_mood": "happy"}, k=3)  # invalid
    result = agent.recommend(VALID_PROFILE, k=2)
    assert result.success is True


# ---------------------------------------------------------------------------
# Empty catalog
# ---------------------------------------------------------------------------

def test_empty_catalog_does_not_crash():
    agent = RecommendationAgent([])
    result = agent.recommend(VALID_PROFILE, k=3)

    assert result.metadata["total_catalog_size"] == 0
    assert result.metadata["retrieved_candidates"] == 0
    assert result.recommendations == []


# ---------------------------------------------------------------------------
# Deterministic behavior
# ---------------------------------------------------------------------------

def test_deterministic_behavior():
    catalog = make_catalog()
    agent = RecommendationAgent(catalog)
    first = agent.recommend(VALID_PROFILE, k=3)
    second = agent.recommend(VALID_PROFILE, k=3)

    assert first.recommendations == second.recommendations
    assert first.metadata == second.metadata


# ---------------------------------------------------------------------------
# Integration with the real dataset
# ---------------------------------------------------------------------------

def test_integration_with_real_catalog():
    songs = load_songs("data/songs.csv")
    agent = RecommendationAgent(songs)
    high_energy_pop = {
        "favorite_genre": "pop",
        "favorite_mood": "happy",
        "target_energy": 0.85,
        "likes_acoustic": False,
    }
    result = agent.recommend(high_energy_pop, k=5, mode="balanced")

    assert result.success is True
    assert result.metadata["total_catalog_size"] == 18
    # Sunrise City is the top pop/happy candidate and should rank first.
    top_song = result.recommendations[0][0]
    assert top_song["title"] == "Sunrise City"
