"""
Tests for the specialization preference interpreter (src/preference_interpreter.py)
and its integration into the agent.

The interpreter is deterministic keyword matching (no model, no randomness). It
must infer only supported genres/moods, respect explicit user values, stay
backward compatible, and surface itself in the trace/metadata.
"""

import json

from src.preference_interpreter import (
    interpret_request,
    merge_interpreted_profile,
    InterpretedPreference,
    DEFAULT_EXAMPLES_PATH,
)
from src.agent import RecommendationAgent
from src.recommender import load_songs

CATALOG_GENRES = {
    "ambient", "classical", "country", "electronic", "folk", "hip hop",
    "indie pop", "jazz", "lofi", "metal", "pop", "r&b", "reggae", "rock", "synthwave",
}
CATALOG_MOODS = {
    "angry", "chill", "confident", "euphoric", "focused", "happy", "intense",
    "melancholy", "moody", "nostalgic", "relaxed", "romantic", "uplifting", "wistful",
}


def catalog():
    return load_songs("data/songs.csv")


# ---------------------------------------------------------------------------
# Pattern matching
# ---------------------------------------------------------------------------

def test_studying_pattern():
    ip = interpret_request("I'm studying for my robotics exam.")
    assert ip.inferred_profile["favorite_genre"] == "lofi"
    assert ip.inferred_profile["favorite_mood"] == "focused"


def test_workout_pattern():
    ip = interpret_request("I'm lifting weights.")
    assert ip.inferred_profile["favorite_genre"] == "electronic"
    assert ip.inferred_profile["favorite_mood"] == "intense"
    assert ip.inferred_profile["target_energy"] >= 0.8


def test_party_and_commute_patterns():
    assert interpret_request("I'm going to a party tonight.").inferred_profile["favorite_mood"] == "euphoric"
    assert interpret_request("I'm driving home after work.").inferred_profile["favorite_mood"] == "uplifting"


def test_multiword_keyword_matches():
    ip = interpret_request("I'm working out right now.")
    assert ip.inferred_profile["favorite_genre"] == "electronic"


def test_direct_mood_word():
    ip = interpret_request("give me something intense")
    assert ip.inferred_profile["favorite_mood"] == "intense"


# ---------------------------------------------------------------------------
# Confidence
# ---------------------------------------------------------------------------

def test_confidence_high_for_activity():
    assert interpret_request("I'm studying tonight.").confidence == "High"


def test_confidence_medium_for_attribute_only():
    assert interpret_request("I want something nostalgic.").confidence == "Medium"


def test_confidence_low_for_unknown():
    ip = interpret_request("zzz qwerty asdf")
    assert ip.confidence == "Low"
    assert ip.inferred_profile == {}
    assert ip.specialization_used is False


# ---------------------------------------------------------------------------
# Determinism / robustness
# ---------------------------------------------------------------------------

def test_deterministic_output():
    a = interpret_request("I'm coding late at night.")
    b = interpret_request("I'm coding late at night.")
    assert a.to_dict() == b.to_dict()


def test_empty_and_non_string_inputs():
    assert interpret_request("").confidence == "Low"
    assert interpret_request("   ").inferred_profile == {}
    assert interpret_request(None).specialization_used is False


def test_partial_request_infers_partial_profile():
    # A bare mood word gives only a mood (partial), still Medium confidence.
    ip = interpret_request("play something happy")
    assert ip.inferred_profile == {"favorite_mood": "happy"}
    assert ip.confidence == "Medium"


def test_unmatched_tokens_exclude_stopwords_and_matches():
    ip = interpret_request("I'm studying robotics")
    assert "robotics" in ip.unmatched_tokens
    assert "studying" not in ip.unmatched_tokens
    assert "i'm" not in ip.unmatched_tokens


# ---------------------------------------------------------------------------
# merge precedence
# ---------------------------------------------------------------------------

def test_merge_fills_only_missing():
    ip = interpret_request("I'm studying.")
    enriched, filled = merge_interpreted_profile({"favorite_genre": "rock"}, ip)
    assert enriched["favorite_genre"] == "rock"          # explicit kept
    assert enriched["favorite_mood"] == "focused"        # filled
    assert "favorite_genre" not in filled
    assert "favorite_mood" in filled


def test_merge_non_dict_profile_is_safe():
    ip = interpret_request("I'm studying.")
    enriched, filled = merge_interpreted_profile("nope", ip)
    assert enriched == "nope"
    assert filled == []


# ---------------------------------------------------------------------------
# No invented attributes
# ---------------------------------------------------------------------------

def test_no_invented_genres_or_moods():
    from src.preference_interpreter import _ATTRIBUTE_RULES, _ACTIVITY_RULES
    for rule in _ATTRIBUTE_RULES + _ACTIVITY_RULES:
        prof = rule["profile"]
        if "favorite_genre" in prof:
            assert prof["favorite_genre"] in CATALOG_GENRES
        if "favorite_mood" in prof:
            assert prof["favorite_mood"] in CATALOG_MOODS


# ---------------------------------------------------------------------------
# Synthetic dataset
# ---------------------------------------------------------------------------

def test_synthetic_dataset_loads_and_is_valid():
    with open(DEFAULT_EXAMPLES_PATH, encoding="utf-8") as handle:
        data = json.load(handle)
    assert 20 <= len(data) <= 30
    for example in data:
        assert set(["user_request", "profile", "context", "notes"]) <= set(example.keys())
        prof = example["profile"]
        assert prof["favorite_genre"] in CATALOG_GENRES
        assert prof["favorite_mood"] in CATALOG_MOODS
        assert 0.0 <= prof["target_energy"] <= 1.0
        assert isinstance(prof["likes_acoustic"], bool)


def test_matched_examples_reference_dataset():
    ip = interpret_request("I'm studying for my exam.")
    assert len(ip.matched_examples) >= 1
    for match in ip.matched_examples:
        assert "index" in match and "user_request" in match


# ---------------------------------------------------------------------------
# Agent integration
# ---------------------------------------------------------------------------

def test_agent_uses_interpreter_and_succeeds():
    agent = RecommendationAgent(catalog())
    result = agent.recommend({}, k=5, natural_language_request="I'm studying for my exam.")
    assert result.success is True
    assert result.cleaned_profile["favorite_genre"] == "lofi"
    assert isinstance(result.interpreted_preference, InterpretedPreference)


def test_specialization_improves_over_baseline():
    agent = RecommendationAgent(catalog())
    baseline = agent.recommend({}, k=5)  # no NL, no profile
    specialized = agent.recommend({}, k=5, natural_language_request="I'm lifting weights.")
    assert baseline.success is False
    assert specialized.success is True
    assert len(specialized.recommendations) > 0


def test_explicit_profile_overrides_interpreter():
    agent = RecommendationAgent(catalog())
    result = agent.recommend(
        {"favorite_genre": "rock", "favorite_mood": "intense", "target_energy": 0.9, "likes_acoustic": False},
        k=3,
        natural_language_request="I'm studying.",  # would infer lofi/focused
    )
    assert result.cleaned_profile["favorite_genre"] == "rock"   # explicit wins
    assert result.cleaned_profile["favorite_mood"] == "intense"


def test_trace_has_preference_interpretation_step():
    agent = RecommendationAgent(catalog())
    result = agent.recommend({}, k=5, natural_language_request="I'm studying.")
    step = next(s for s in result.trace.steps if s.component == "preference_interpretation")
    assert step.details["confidence"] == "High"
    assert step.details["specialization_used"] is True
    assert "matched_examples" in step.details


def test_metadata_reports_specialization():
    agent = RecommendationAgent(catalog())
    result = agent.recommend({}, k=5, natural_language_request="I'm studying.")
    assert result.metadata["specialization_used"] is True
    assert result.metadata["interpretation_confidence"] == "High"


# ---------------------------------------------------------------------------
# Backward compatibility
# ---------------------------------------------------------------------------

def test_backward_compatible_without_nl_request():
    agent = RecommendationAgent(catalog())
    result = agent.recommend(
        {"favorite_genre": "pop", "favorite_mood": "happy", "target_energy": 0.85, "likes_acoustic": False},
        k=3,
    )
    assert result.success is True
    assert result.interpreted_preference is None
    # No interpreter step when no NL request is provided.
    assert all(s.component != "preference_interpretation" for s in result.trace.steps)
