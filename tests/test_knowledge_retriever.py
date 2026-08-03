"""
Tests for the RAG knowledge retriever (src/knowledge_retriever.py) and its
integration into the agent.

The retriever must be deterministic, fail safely on missing/malformed files,
invent no mappings, and never overwrite explicit user preferences. Integration
must be backward compatible and observable via the trace/metadata.
"""

import json

from src.knowledge_retriever import (
    retrieve_knowledge,
    apply_knowledge_to_profile,
    KnowledgeRetrievalResult,
)
from src.agent import RecommendationAgent
from src.recommender import load_songs, recommend_songs
from src.retriever import retrieve_candidates

# Canonical genres present in data/songs.csv (used to assert no invented data).
CATALOG_GENRES = {
    "ambient", "classical", "country", "electronic", "folk", "hip hop",
    "indie pop", "jazz", "lofi", "metal", "pop", "r&b", "reggae", "rock", "synthwave",
}


# ---------------------------------------------------------------------------
# Retrieval: genre aliases
# ---------------------------------------------------------------------------

def test_genre_alias_retrieval():
    result = retrieve_knowledge(genre="edm")
    assert result.normalized_genre == "electronic"
    assert "genre_aliases.json" in result.sources_used
    assert len(result.items) == 1
    assert result.items[0].matched_key == "edm"


def test_genre_alias_case_insensitive():
    assert retrieve_knowledge(genre="EDM").normalized_genre == "electronic"
    assert retrieve_knowledge(genre="Lo-Fi").normalized_genre == "lofi"


def test_unsupported_alias_leaves_genre_unchanged():
    result = retrieve_knowledge(genre="kpop")  # not an alias, not invented
    assert result.normalized_genre == "kpop"
    assert result.sources_used == []
    assert result.items == []


# ---------------------------------------------------------------------------
# Retrieval: contexts
# ---------------------------------------------------------------------------

def test_context_retrieval():
    result = retrieve_knowledge(context="studying")
    assert result.inferred_context == "studying"
    assert "listening_contexts.md" in result.sources_used
    updates = result.profile_updates
    assert updates["favorite_mood"] == "focused"
    assert updates["likes_acoustic"] is True
    assert 0.2 <= updates["target_energy"] <= 0.45
    assert updates["favorite_genre"] == "lofi"


def test_unsupported_context_safe_fallback():
    result = retrieve_knowledge(context="scuba diving")
    assert result.inferred_context is None
    assert result.profile_updates == {}
    assert result.sources_used == []


def test_multiple_source_usage():
    result = retrieve_knowledge(genre="edm", context="party")
    assert result.normalized_genre == "electronic"
    assert result.inferred_context == "party"
    assert set(result.sources_used) == {"genre_aliases.json", "listening_contexts.md"}


# ---------------------------------------------------------------------------
# Fail-safe: missing / malformed files
# ---------------------------------------------------------------------------

def test_missing_knowledge_files(tmp_path):
    result = retrieve_knowledge(genre="edm", context="studying", knowledge_dir=str(tmp_path))
    # No files -> no alias, no context; but no crash and genre left unchanged.
    assert result.normalized_genre == "edm"
    assert result.inferred_context is None
    assert result.sources_used == []


def test_malformed_knowledge_files(tmp_path):
    (tmp_path / "genre_aliases.json").write_text("{ this is not valid json", encoding="utf-8")
    (tmp_path / "listening_contexts.md").write_text("garbage without structure", encoding="utf-8")
    result = retrieve_knowledge(genre="edm", context="studying", knowledge_dir=str(tmp_path))
    assert result.normalized_genre == "edm"      # malformed aliases ignored safely
    assert result.inferred_context is None       # malformed contexts ignored safely
    assert result.sources_used == []


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

def test_deterministic_output():
    a = retrieve_knowledge(genre="edm", context="party")
    b = retrieve_knowledge(genre="edm", context="party")
    assert a.to_dict() == b.to_dict()


# ---------------------------------------------------------------------------
# apply_knowledge_to_profile precedence
# ---------------------------------------------------------------------------

def test_apply_fills_only_missing_fields():
    knowledge = retrieve_knowledge(context="studying")
    profile = {"favorite_genre": "lofi"}  # mood/energy/acoustic missing
    enriched, warnings, applied = apply_knowledge_to_profile(profile, knowledge)
    assert enriched["favorite_mood"] == "focused"
    assert "target_energy" in enriched
    assert enriched["likes_acoustic"] is True
    assert "favorite_mood" in applied


def test_apply_does_not_overwrite_explicit_values():
    knowledge = retrieve_knowledge(context="studying")
    profile = {
        "favorite_genre": "lofi", "favorite_mood": "happy",
        "target_energy": 0.9, "likes_acoustic": False,
    }
    enriched, warnings, applied = apply_knowledge_to_profile(profile, knowledge)
    # Explicit values preserved exactly.
    assert enriched["favorite_mood"] == "happy"
    assert enriched["target_energy"] == 0.9
    assert enriched["likes_acoustic"] is False
    # Conflicts are recorded as warnings, not silent overrides.
    assert any("keeping user's explicit" in w for w in warnings)


def test_apply_normalizes_genre_alias_with_warning():
    knowledge = retrieve_knowledge(genre="edm")
    enriched, warnings, applied = apply_knowledge_to_profile({"favorite_genre": "edm"}, knowledge)
    assert enriched["favorite_genre"] == "electronic"
    assert "favorite_genre" in applied
    assert any("Normalized genre alias" in w for w in warnings)


# ---------------------------------------------------------------------------
# Agent integration
# ---------------------------------------------------------------------------

def catalog():
    return load_songs("data/songs.csv")


def test_enriched_profile_affects_agent_result():
    agent = RecommendationAgent(catalog())
    profile = {"favorite_genre": "edm", "favorite_mood": "euphoric", "target_energy": 0.85, "likes_acoustic": False}
    baseline = agent.recommend(profile, k=5, use_knowledge=False)
    enhanced = agent.recommend(profile, k=5, use_knowledge=True)

    assert baseline.cleaned_profile["favorite_genre"] == "edm"
    assert enhanced.cleaned_profile["favorite_genre"] == "electronic"
    # The enriched genre changes which candidates are retrieved.
    assert enhanced.recommendations != baseline.recommendations


def test_context_enables_otherwise_failing_request():
    agent = RecommendationAgent(catalog())
    profile = {"favorite_genre": "lofi"}  # missing required fields
    baseline = agent.recommend(profile, k=5, use_knowledge=False)
    enhanced = agent.recommend(profile, k=5, context="studying", use_knowledge=True)
    assert baseline.success is False
    assert enhanced.success is True


def test_no_knowledge_leaves_recommendations_unchanged():
    songs = catalog()
    agent = RecommendationAgent(songs)
    profile = {"favorite_genre": "pop", "favorite_mood": "happy", "target_energy": 0.85, "likes_acoustic": False}

    with_knowledge = agent.recommend(profile, k=5, use_knowledge=True)
    without_knowledge = agent.recommend(profile, k=5, use_knowledge=False)
    # 'pop' has no alias and no context, so knowledge changes nothing.
    assert with_knowledge.recommendations == without_knowledge.recommendations

    # And both equal a direct recommend_songs call (scores/order unchanged).
    candidates = retrieve_candidates(songs, without_knowledge.cleaned_profile)
    expected = recommend_songs(without_knowledge.cleaned_profile, candidates, k=5, mode="balanced")
    assert without_knowledge.recommendations == expected


def test_backward_compatible_old_calls():
    agent = RecommendationAgent(catalog())
    # Old-style call with no new parameters must still work.
    result = agent.recommend(
        {"favorite_genre": "pop", "favorite_mood": "happy", "target_energy": 0.85, "likes_acoustic": False},
        k=3,
    )
    assert result.success is True
    assert len(result.recommendations) > 0


def test_knowledge_appears_in_trace_and_metadata():
    agent = RecommendationAgent(catalog())
    result = agent.recommend(
        {"favorite_genre": "edm", "favorite_mood": "euphoric", "target_energy": 0.85, "likes_acoustic": False},
        k=5,
    )
    components = [s.component for s in result.trace.steps]
    assert "knowledge_retrieval" in components
    assert "genre_aliases.json" in result.metadata["knowledge_sources_used"]
    assert result.metadata["normalized_genre"] == "electronic"
    assert isinstance(result.retrieved_knowledge, KnowledgeRetrievalResult)


def test_no_knowledge_step_for_plain_request():
    agent = RecommendationAgent(catalog())
    result = agent.recommend(
        {"favorite_genre": "pop", "favorite_mood": "happy", "target_energy": 0.85, "likes_acoustic": False},
        k=5,
    )
    components = [s.component for s in result.trace.steps]
    assert "knowledge_retrieval" not in components  # preserves the 7-step trace
    assert len(components) == 7


# ---------------------------------------------------------------------------
# No unsupported claims / external data
# ---------------------------------------------------------------------------

def test_no_invented_or_external_data():
    # Every normalized genre must be a real catalog genre.
    for alias in ["edm", "hip-hop", "hiphop", "rnb", "rhythm and blues",
                  "classical music", "lo-fi", "rock music"]:
        normalized = retrieve_knowledge(genre=alias).normalized_genre
        assert normalized in CATALOG_GENRES

    # Sources are only ever the two known local files.
    result = retrieve_knowledge(genre="edm", context="party")
    for item in result.items:
        assert item.source in {"genre_aliases.json", "listening_contexts.md"}

    # Context-derived genres/moods must also exist in the catalog.
    ctx = retrieve_knowledge(context="working out")
    assert ctx.profile_updates["favorite_genre"] in CATALOG_GENRES
