"""
Tests for the reliability evaluator (src/evaluator.py) and its integration
into the agent. The evaluator is read-only: it must not change recommendations,
scores, order, or explanations.
"""

from src.evaluator import evaluate_recommendations, ReliabilityReport
from src.explainer import generate_explanations
from src.agent import RecommendationAgent
from src.recommender import recommend_songs, load_songs
from src.retriever import retrieve_candidates


PROFILE = {
    "favorite_genre": "pop",
    "favorite_mood": "happy",
    "target_energy": 0.80,
    "likes_acoustic": False,
}


def song(**o) -> dict:
    base = {
        "id": 1, "title": "S", "artist": "A", "genre": "pop", "mood": "happy",
        "energy": 0.8, "acousticness": 0.2, "popularity": 50, "instrumentalness": 0.0,
    }
    base.update(o)
    return base


def good_recs() -> list:
    """Three distinct, descending-score pop/happy recommendations."""
    return [
        (song(id=1, title="S1", artist="A", genre="pop", mood="happy", energy=0.80), 5.5, "genre match (+2.0), mood match (+1.0)"),
        (song(id=2, title="S2", artist="B", genre="pop", mood="happy", energy=0.78), 4.2, "genre match (+2.0), mood match (+1.0)"),
        (song(id=3, title="S3", artist="C", genre="pop", mood="sad", energy=0.60), 3.1, "genre match (+2.0)"),
    ]


def check(report: ReliabilityReport, name: str):
    return next(c for c in report.checks if c.name == name)


def evaluate(recs, *, requested_k=5, retrieved=None):
    if retrieved is None:
        retrieved = len(recs)
    explanations = generate_explanations(recs, PROFILE)
    return evaluate_recommendations(
        recs, explanations, PROFILE, requested_k=requested_k, retrieved_candidate_count=retrieved
    )


# ---------------------------------------------------------------------------
# Duplicate detection
# ---------------------------------------------------------------------------

def test_no_duplicates_passes():
    report = evaluate(good_recs())
    assert check(report, "no_duplicate_songs").passed


def test_duplicate_song_detected_and_fails():
    recs = good_recs()
    recs.append((song(id=1, title="S1", artist="A"), 2.0, "genre match (+2.0)"))  # dup id=1
    report = evaluate(recs, retrieved=10)
    assert not check(report, "no_duplicate_songs").passed
    assert report.passed is False  # duplicate is critical


def test_duplicate_fallback_by_title_artist_when_no_id():
    recs = [
        (song(id=None, title="X", artist="A"), 3.0, "genre match (+2.0)"),
        (song(id=None, title="X", artist="A"), 2.0, "genre match (+2.0)"),
    ]
    report = evaluate(recs, retrieved=5)
    assert check(report, "no_duplicate_songs").value == 1


# ---------------------------------------------------------------------------
# Explanation coverage
# ---------------------------------------------------------------------------

def test_full_coverage_passes():
    report = evaluate(good_recs())
    assert check(report, "explanation_coverage").passed
    assert report.metrics["explanation_coverage"] == 1.0


def test_incomplete_coverage_fails():
    recs = good_recs()
    explanations = generate_explanations(recs, PROFILE)
    explanations = explanations[:-1]  # drop one explanation
    report = evaluate_recommendations(
        recs, explanations, PROFILE, requested_k=5, retrieved_candidate_count=5
    )
    cov = check(report, "explanation_coverage")
    assert not cov.passed
    assert report.passed is False


# ---------------------------------------------------------------------------
# Score validity and order
# ---------------------------------------------------------------------------

def test_valid_descending_scores_pass():
    report = evaluate(good_recs())
    assert check(report, "score_validity_and_order").passed


def test_non_descending_scores_fail():
    recs = good_recs()
    recs[1] = (recs[1][0], 9.9, recs[1][2])  # out-of-order (higher than first)
    report = evaluate(recs)
    assert not check(report, "score_validity_and_order").passed
    assert report.passed is False


def test_non_numeric_score_fails():
    recs = good_recs()
    recs[0] = (recs[0][0], "high", recs[0][2])
    report = evaluate(recs)
    assert not check(report, "score_validity_and_order").passed


# ---------------------------------------------------------------------------
# Preference alignment
# ---------------------------------------------------------------------------

def test_preference_alignment_metric():
    report = evaluate(good_recs())
    # S1,S2 match genre+mood+energy; S3 matches genre only.
    m = report.metrics
    assert m["genre_match_count"] == 3
    assert m["mood_match_count"] == 2
    assert 0.0 < m["preference_alignment"] <= 1.0


# ---------------------------------------------------------------------------
# Diversity metrics
# ---------------------------------------------------------------------------

def test_diversity_metrics_all_unique():
    recs = [
        (song(id=1, title="S1", artist="A", genre="pop", mood="happy", energy=0.80), 5.0, "genre match (+2.0)"),
        (song(id=2, title="S2", artist="B", genre="rock", mood="happy", energy=0.78), 4.0, "energy closeness (+0.9)"),
        (song(id=3, title="S3", artist="C", genre="lofi", mood="chill", energy=0.60), 3.0, "energy closeness (+0.5)"),
    ]
    report = evaluate(recs)
    m = report.metrics
    assert m["unique_artist_ratio"] == 1.0
    assert m["unique_genre_ratio"] == 1.0
    assert m["repeated_artist_count"] == 0
    assert m["repeated_genre_count"] == 0


def test_diversity_metrics_with_repeats():
    recs = [
        (song(id=1, title="S1", artist="A", genre="pop"), 5.0, "genre match (+2.0)"),
        (song(id=2, title="S2", artist="A", genre="pop"), 4.0, "genre match (+2.0)"),  # repeat artist+genre
        (song(id=3, title="S3", artist="B", genre="rock"), 3.0, "energy closeness (+0.5)"),
    ]
    report = evaluate(recs)
    m = report.metrics
    assert m["repeated_artist_count"] == 1
    assert m["repeated_genre_count"] == 1
    assert m["unique_artist_ratio"] < 1.0


# ---------------------------------------------------------------------------
# Empty results & impossible counts
# ---------------------------------------------------------------------------

def test_empty_recommendations_handled():
    report = evaluate_recommendations(
        [], [], PROFILE, requested_k=5, retrieved_candidate_count=0
    )
    assert report.passed is True
    assert "No recommendations" in report.summary


def test_impossible_count_detected():
    recs = good_recs()  # 3 recs
    report = evaluate(recs, requested_k=2, retrieved=10)  # returned 3 > requested 2
    assert not check(report, "result_completeness").passed
    assert report.passed is False


def test_returned_more_than_retrieved_detected():
    recs = good_recs()  # 3 recs
    report = evaluate(recs, requested_k=5, retrieved=1)  # returned 3 > retrieved 1
    assert not check(report, "result_completeness").passed


# ---------------------------------------------------------------------------
# Reliability score
# ---------------------------------------------------------------------------

def test_reliability_score_is_deterministic():
    a = evaluate(good_recs())
    b = evaluate(good_recs())
    assert a.score == b.score
    assert a.metrics == b.metrics


def test_reliability_score_in_range():
    report = evaluate(good_recs())
    assert 0 <= report.score <= 100


def test_clean_result_scores_high():
    report = evaluate(good_recs())
    assert report.passed is True
    assert report.score >= 80  # no dups, full coverage, valid order, strong alignment


# ---------------------------------------------------------------------------
# Agent integration
# ---------------------------------------------------------------------------

def make_catalog() -> list:
    return [
        song(id=1, title="S1", artist="A", genre="pop", mood="happy", energy=0.80, popularity=90),
        song(id=2, title="S2", artist="B", genre="pop", mood="happy", energy=0.75, popularity=60),
        song(id=3, title="S3", artist="C", genre="pop", mood="sad", energy=0.60, popularity=50),
    ]


def test_agent_success_includes_one_reliability_report():
    agent = RecommendationAgent(make_catalog())
    result = agent.recommend(PROFILE, k=3)
    assert result.reliability_report is not None
    assert isinstance(result.reliability_report, ReliabilityReport)
    assert result.reliability_report.metrics["returned_count"] == len(result.recommendations)


def test_agent_failure_has_no_reliability_report():
    agent = RecommendationAgent(make_catalog())
    result = agent.recommend({"favorite_mood": "happy"}, k=3)  # invalid
    assert result.success is False
    assert result.reliability_report is None


def test_agent_recommendations_unchanged_by_evaluation():
    catalog = make_catalog()
    agent = RecommendationAgent(catalog)
    result = agent.recommend(PROFILE, k=3, mode="balanced")

    candidates = retrieve_candidates(catalog, result.cleaned_profile)
    expected = recommend_songs(result.cleaned_profile, candidates, k=3, mode="balanced")
    assert result.recommendations == expected  # order and scores intact


def test_agent_integration_with_real_catalog():
    songs = load_songs("data/songs.csv")
    agent = RecommendationAgent(songs)
    result = agent.recommend(PROFILE, k=5)
    report = result.reliability_report
    assert report.passed is True
    assert report.metrics["duplicate_count"] == 0
