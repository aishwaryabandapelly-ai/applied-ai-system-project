"""
Tests for the evidence-based explanation generator (src/explainer.py) and its
minimal integration into the agent.

Explanations must be deterministic, derive every claim only from supported
inputs (song attributes, profile, score, raw reasons), and never crash on
malformed reason input.
"""

from src.explainer import (
    generate_explanation,
    generate_explanations,
    RecommendationExplanation,
)
from src.agent import RecommendationAgent
from src.recommender import recommend_songs
from src.retriever import retrieve_candidates


PROFILE = {
    "favorite_genre": "pop",
    "favorite_mood": "happy",
    "target_energy": 0.80,
    "likes_acoustic": False,
}

SONG = {
    "id": 1,
    "title": "Sunrise City",
    "artist": "Neon Echo",
    "genre": "pop",
    "mood": "happy",
    "energy": 0.82,
    "acousticness": 0.18,
    "popularity": 78,
    "instrumentalness": 0.02,
}

FULL_REASONS = [
    "genre match (+2.0)",
    "mood match (+1.0)",
    "energy closeness (+0.97)",
    "acoustic preference (+0.82)",
    "popularity bonus (+0.78)",
    "instrumentalness bonus (+0.01)",
]


def categories(exp: RecommendationExplanation) -> set:
    return {item["category"] for item in exp.evidence}


# ---------------------------------------------------------------------------
# Evidence content
# ---------------------------------------------------------------------------

def test_genre_and_mood_matches_appear_in_evidence():
    exp = generate_explanation(SONG, 5.58, FULL_REASONS, PROFILE)
    assert "genre match" in categories(exp)
    assert "mood match" in categories(exp)


def test_numeric_contributions_preserved():
    exp = generate_explanation(SONG, 5.58, FULL_REASONS, PROFILE)
    by_cat = {item["category"]: item["contribution"] for item in exp.evidence}
    assert by_cat["genre match"] == 2.0
    assert by_cat["mood match"] == 1.0
    assert by_cat["energy closeness"] == 0.97


# ---------------------------------------------------------------------------
# Confidence rule (deterministic)
# ---------------------------------------------------------------------------

def test_confidence_high_two_matches_no_penalty():
    exp = generate_explanation(SONG, 5.58, FULL_REASONS, PROFILE)
    assert exp.confidence == "High"


def test_confidence_medium_single_match():
    reasons = [r for r in FULL_REASONS if "mood match" not in r]  # drop mood match
    exp = generate_explanation(SONG, 4.0, reasons, PROFILE)
    assert exp.confidence == "Medium"


def test_confidence_low_no_matches():
    reasons = [
        "energy closeness (+0.50)",
        "acoustic preference (+0.30)",
        "popularity bonus (+0.40)",
        "instrumentalness bonus (+0.00)",
    ]
    exp = generate_explanation(SONG, 1.2, reasons, PROFILE)
    assert exp.confidence == "Low"


def test_confidence_is_deterministic():
    a = generate_explanation(SONG, 5.58, FULL_REASONS, PROFILE)
    b = generate_explanation(SONG, 5.58, FULL_REASONS, PROFILE)
    assert a == b


def test_diversity_penalty_limits_confidence():
    reasons = FULL_REASONS + ["diversity penalty: repeated artist (-0.50)"]
    exp = generate_explanation(SONG, 5.08, reasons, PROFILE)
    # Two matches would be High, but a penalty caps it at Medium.
    assert exp.confidence == "Medium"
    assert any("diversity penalty" in lim.lower() for lim in exp.limitations)


# ---------------------------------------------------------------------------
# Robustness
# ---------------------------------------------------------------------------

def test_string_and_list_reason_formats_match():
    from_list = generate_explanation(SONG, 5.58, FULL_REASONS, PROFILE)
    from_string = generate_explanation(SONG, 5.58, ", ".join(FULL_REASONS), PROFILE)
    assert from_list.evidence == from_string.evidence
    assert from_list.confidence == from_string.confidence
    assert from_list.summary == from_string.summary


def test_malformed_reasons_do_not_crash():
    for bad in (None, 123, {"x": 1}, "", "   ", ["", None]):
        exp = generate_explanation(SONG, 5.0, bad, PROFILE)
        assert isinstance(exp, RecommendationExplanation)
        assert exp.confidence == "Low"  # no matches parsed


def test_missing_song_fields_do_not_crash():
    exp = generate_explanation({}, "not-a-number", FULL_REASONS, {})
    assert exp.song_title == "Unknown title"
    assert exp.artist == "Unknown artist"
    assert exp.score is None


def test_score_is_coerced_to_float():
    exp = generate_explanation(SONG, "5.58", FULL_REASONS, PROFILE)
    assert exp.score == 5.58


# ---------------------------------------------------------------------------
# No unsupported claims
# ---------------------------------------------------------------------------

def test_no_unsupported_claims_in_summary_and_evidence():
    exp = generate_explanation(SONG, 5.58, FULL_REASONS, PROFILE)
    forbidden = ["lyric", "album", "chart", "listening history", "emotion"]
    text = (exp.summary + " " + " ".join(item["detail"] for item in exp.evidence)).lower()
    for token in forbidden:
        assert token not in text
    # Every evidence detail must be one of the supplied raw reasons.
    for item in exp.evidence:
        assert item["detail"] in FULL_REASONS


# ---------------------------------------------------------------------------
# Batch helper
# ---------------------------------------------------------------------------

def test_generate_explanations_handles_malformed_entries():
    recs = [(SONG, 5.58, FULL_REASONS), "not a tuple", (SONG, 4.0, "genre match (+2.0)")]
    explanations = generate_explanations(recs, PROFILE)
    assert len(explanations) == 3
    assert all(isinstance(e, RecommendationExplanation) for e in explanations)


# ---------------------------------------------------------------------------
# Agent integration (backward compatible)
# ---------------------------------------------------------------------------

def make_catalog() -> list:
    def song(**o):
        base = {
            "id": 1, "title": "S", "artist": "A", "genre": "pop", "mood": "happy",
            "energy": 0.8, "acousticness": 0.2, "popularity": 50, "instrumentalness": 0.0,
        }
        base.update(o)
        return base
    return [
        song(id=1, title="S1", artist="A", genre="pop", mood="happy", energy=0.80, popularity=90),
        song(id=2, title="S2", artist="B", genre="pop", mood="happy", energy=0.75, popularity=60),
        song(id=3, title="S3", artist="C", genre="pop", mood="sad", energy=0.60, popularity=50),
    ]


def test_agent_explanations_one_to_one_with_recommendations():
    agent = RecommendationAgent(make_catalog())
    result = agent.recommend(PROFILE, k=3)

    assert len(result.explanations) == len(result.recommendations)
    for (song, _score, _reason), exp in zip(result.recommendations, result.explanations):
        assert exp.song_title == song["title"]


def test_agent_recommendations_unchanged_by_explanations():
    catalog = make_catalog()
    agent = RecommendationAgent(catalog)
    result = agent.recommend(PROFILE, k=3, mode="balanced")

    # The recommendations field must equal a direct recommend_songs call:
    # explanations are additive and must not alter order or scores.
    candidates = retrieve_candidates(catalog, result.cleaned_profile)
    expected = recommend_songs(result.cleaned_profile, candidates, k=3, mode="balanced")
    assert result.recommendations == expected


def test_agent_failure_has_no_explanations():
    agent = RecommendationAgent(make_catalog())
    result = agent.recommend({"favorite_mood": "happy"}, k=3)  # invalid: missing genre
    assert result.success is False
    assert result.explanations == []
