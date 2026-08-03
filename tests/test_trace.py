"""
Tests for the agentic workflow execution trace (src/trace.py) and its
integration into the agent.

The trace records observable execution metadata only. It must be deterministic,
appear on both successful and failed runs, stay consistent with the agent's
metadata and reliability report, and contain no hidden reasoning/narrative.
"""

from src.agent import RecommendationAgent
from src.trace import AgentTrace
from src.recommender import recommend_songs, load_songs
from src.retriever import retrieve_candidates


PROFILE = {
    "favorite_genre": "pop",
    "favorite_mood": "happy",
    "target_energy": 0.80,
    "likes_acoustic": False,
}

SUCCESS_ORDER = [
    "request_received",
    "validation",
    "retrieval",
    "recommendation",
    "explanation",
    "reliability_evaluation",
    "completion",
]

FAILURE_ORDER = ["request_received", "validation", "completion"]


def song(**o) -> dict:
    base = {
        "id": 1, "title": "S", "artist": "A", "genre": "pop", "mood": "happy",
        "energy": 0.8, "acousticness": 0.2, "popularity": 50, "instrumentalness": 0.0,
    }
    base.update(o)
    return base


def make_catalog() -> list:
    return [
        song(id=1, title="S1", artist="A", genre="pop", mood="happy", energy=0.80, popularity=90),
        song(id=2, title="S2", artist="B", genre="pop", mood="happy", energy=0.75, popularity=60),
        song(id=3, title="S3", artist="C", genre="pop", mood="sad", energy=0.60, popularity=50),
    ]


def components(trace: AgentTrace) -> list:
    return [step.component for step in trace.steps]


def step_by_name(trace: AgentTrace, name: str):
    return next(s for s in trace.steps if s.component == name)


# ---------------------------------------------------------------------------
# Trace presence
# ---------------------------------------------------------------------------

def test_trace_present_on_success():
    agent = RecommendationAgent(make_catalog())
    result = agent.recommend(PROFILE, k=3)
    assert isinstance(result.trace, AgentTrace)
    assert result.trace.final_status == "success"


def test_trace_present_on_invalid_request():
    agent = RecommendationAgent(make_catalog())
    result = agent.recommend({"favorite_mood": "happy"}, k=3)  # missing genre
    assert result.success is False
    assert isinstance(result.trace, AgentTrace)
    assert result.trace.final_status == "failure"


# ---------------------------------------------------------------------------
# Step order
# ---------------------------------------------------------------------------

def test_success_steps_in_expected_order():
    agent = RecommendationAgent(make_catalog())
    result = agent.recommend(PROFILE, k=3)
    assert components(result.trace) == SUCCESS_ORDER
    # step indices are 1-based and sequential
    assert [s.step for s in result.trace.steps] == [1, 2, 3, 4, 5, 6, 7]


def test_failure_steps_in_expected_order():
    agent = RecommendationAgent(make_catalog())
    result = agent.recommend({"favorite_mood": "happy"}, k=3)
    assert components(result.trace) == FAILURE_ORDER


# ---------------------------------------------------------------------------
# Consistency with metadata / reliability
# ---------------------------------------------------------------------------

def test_counts_match_agent_metadata():
    agent = RecommendationAgent(make_catalog())
    result = agent.recommend(PROFILE, k=3)
    meta = result.metadata

    req = step_by_name(result.trace, "request_received").details
    assert req["catalog_size"] == meta["total_catalog_size"]
    assert req["requested_k"] == 3
    assert req["scoring_mode"] == meta["scoring_mode"]

    retr = step_by_name(result.trace, "retrieval").details
    assert retr["candidates_found"] == meta["retrieved_candidates"]

    rec = step_by_name(result.trace, "recommendation").details
    assert rec["recommendations_returned"] == meta["returned_recommendations"]


def test_reliability_score_matches_report():
    agent = RecommendationAgent(make_catalog())
    result = agent.recommend(PROFILE, k=3)
    rel = step_by_name(result.trace, "reliability_evaluation").details
    assert rel["reliability_score"] == result.reliability_report.score
    assert rel["passed"] == result.reliability_report.passed


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

def test_trace_generation_is_deterministic():
    catalog = make_catalog()
    a = RecommendationAgent(catalog).recommend(PROFILE, k=3)
    b = RecommendationAgent(catalog).recommend(PROFILE, k=3)
    assert a.trace.to_dict() == b.trace.to_dict()
    assert a.trace.request_id == b.trace.request_id


# ---------------------------------------------------------------------------
# Recommendations unchanged
# ---------------------------------------------------------------------------

def test_recommendations_unchanged_by_trace():
    catalog = make_catalog()
    agent = RecommendationAgent(catalog)
    result = agent.recommend(PROFILE, k=3, mode="balanced")

    candidates = retrieve_candidates(catalog, result.cleaned_profile)
    expected = recommend_songs(result.cleaned_profile, candidates, k=3, mode="balanced")
    assert result.recommendations == expected


# ---------------------------------------------------------------------------
# No hidden reasoning / narrative
# ---------------------------------------------------------------------------

ALLOWED_DETAIL_KEYS = {
    "requested_k", "scoring_mode", "catalog_size",
    "warning_count", "error_count",
    "candidates_found", "fallback_used", "filters_used",
    "candidates_scored", "recommendations_returned",
    "explanations_generated",
    "reliability_score", "passed", "critical_failure_count",
    "success",
}

FORBIDDEN_TOKENS = ["because", "reasoning", "chain-of-thought", "chain of thought",
                    "i think", "thought", "rationale", "let me", "step-by-step"]


def _string_values(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _string_values(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            yield from _string_values(v)


def test_no_hidden_reasoning_in_trace():
    agent = RecommendationAgent(make_catalog())
    result = agent.recommend(PROFILE, k=3)
    data = result.trace.to_dict()

    for step in data["steps"]:
        # Only whitelisted, observable keys are allowed in details.
        assert set(step["details"].keys()) <= ALLOWED_DETAIL_KEYS
        # No free-text narrative / reasoning tokens anywhere in the values.
        for text in _string_values(step["details"]):
            lowered = text.lower()
            for token in FORBIDDEN_TOKENS:
                assert token not in lowered


# ---------------------------------------------------------------------------
# Integration with real catalog
# ---------------------------------------------------------------------------

def test_real_catalog_trace_serializes():
    songs = load_songs("data/songs.csv")
    agent = RecommendationAgent(songs)
    result = agent.recommend(PROFILE, k=5)
    data = result.trace.to_dict()
    assert data["final_status"] == "success"
    assert data["request_id"].startswith("req_")
    assert len(data["steps"]) == 7
