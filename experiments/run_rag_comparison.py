"""
RAG before/after comparison for TuneGuide AI (stretch feature).

Compares the baseline pipeline (``use_knowledge=False`` — song CSV only) with the
knowledge-enhanced pipeline (``use_knowledge=True`` — CSV plus the two custom
knowledge sources) across three predefined cases, using the integrated
``RecommendationAgent`` for both paths. It also writes a verified results table
to ``experiments/rag_comparison_results.md``.

Reproducible and non-interactive:

    python -m experiments.run_rag_comparison
"""

from src.recommender import load_songs
from src.agent import RecommendationAgent

RESULTS_PATH = "experiments/rag_comparison_results.md"

# (label, profile, context, description)
CASES = [
    (
        "Genre alias",
        {"favorite_genre": "edm", "favorite_mood": "euphoric", "target_energy": 0.85, "likes_acoustic": False},
        None,
        "Baseline uses 'edm' (no catalog match); enhanced normalizes it to 'electronic'.",
    ),
    (
        "Listening context",
        {"favorite_genre": "lofi"},  # mood / energy / acoustic intentionally missing
        "studying",
        "Baseline is missing optional fields and fails validation; enhanced fills them from the 'studying' context.",
    ),
    (
        "Unsupported context",
        {"favorite_genre": "pop", "favorite_mood": "happy", "target_energy": 0.80, "likes_acoustic": False},
        "underwater basket weaving",
        "Unknown context: enhanced path retrieves nothing and falls back safely with no invented knowledge.",
    ),
]


def summarize(result) -> dict:
    """Compact, comparable summary of a RecommendationResult."""
    summary = {
        "success": result.success,
        "candidates": result.metadata.get("retrieved_candidates", 0),
        "recommendations": result.metadata.get("returned_recommendations", 0),
        "sources": result.metadata.get("knowledge_sources_used", []),
        "normalized_genre": result.metadata.get("normalized_genre"),
        "inferred_context": result.metadata.get("inferred_context"),
        "reliability": None,
        "alignment": None,
        "genre": result.cleaned_profile.get("favorite_genre") if result.cleaned_profile else None,
    }
    if result.success and result.reliability_report is not None:
        summary["reliability"] = result.reliability_report.score
        summary["alignment"] = result.reliability_report.metrics.get("preference_alignment")
    return summary


def improvement_note(baseline: dict, enhanced: dict) -> str:
    """Deterministic description of how enhancement changed the outcome."""
    if not baseline["success"] and enhanced["success"]:
        return "Enhanced retrieval enabled a request the baseline could not complete."
    if (
        baseline["alignment"] is not None
        and enhanced["alignment"] is not None
        and enhanced["alignment"] > baseline["alignment"]
    ):
        return (
            f"Preference alignment improved "
            f"({baseline['alignment']} -> {enhanced['alignment']})."
        )
    if baseline == enhanced or enhanced["sources"] == []:
        return "No knowledge applied; identical to baseline (safe fallback)."
    return "No measurable change in preference alignment."


def run_case(agent, label, profile, context, description):
    baseline = summarize(agent.recommend(profile, k=5, use_knowledge=False))
    enhanced = summarize(agent.recommend(profile, k=5, context=context, use_knowledge=True))
    return {
        "label": label,
        "profile": profile,
        "context": context,
        "description": description,
        "baseline": baseline,
        "enhanced": enhanced,
        "note": improvement_note(baseline, enhanced),
    }


def _fmt(value) -> str:
    return "—" if value is None else str(value)


def print_case(case) -> None:
    b, e = case["baseline"], case["enhanced"]
    print("=" * 72)
    print(f"Case: {case['label']}")
    print(f"  Input profile : {case['profile']}")
    print(f"  Context       : {case['context']}")
    print(f"  Baseline      : success={b['success']} candidates={b['candidates']} "
          f"recs={b['recommendations']} reliability={_fmt(b['reliability'])} "
          f"alignment={_fmt(b['alignment'])} genre={_fmt(b['genre'])}")
    print(f"  Knowledge used: {e['sources'] or 'none'} "
          f"(normalized_genre={_fmt(e['normalized_genre'])}, inferred_context={_fmt(e['inferred_context'])})")
    print(f"  Enhanced      : success={e['success']} candidates={e['candidates']} "
          f"recs={e['recommendations']} reliability={_fmt(e['reliability'])} "
          f"alignment={_fmt(e['alignment'])} genre={_fmt(e['genre'])}")
    print(f"  Outcome       : {case['note']}")


def write_markdown(cases) -> None:
    lines = []
    lines.append("# TuneGuide AI — RAG Before/After Comparison")
    lines.append("")
    lines.append(
        "Verified results comparing the baseline pipeline (song CSV only, "
        "`use_knowledge=False`) with the knowledge-enhanced pipeline "
        "(CSV plus `knowledge/genre_aliases.json` and "
        "`knowledge/listening_contexts.md`, `use_knowledge=True`). Both paths "
        "use the integrated `RecommendationAgent`."
    )
    lines.append("")
    lines.append("*Generated by `python -m experiments.run_rag_comparison`.*")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("| Case | Input Genre | Context | Baseline | Knowledge Sources | Enhanced | Reliability (base → enh) | Outcome |")
    lines.append("|------|-------------|---------|----------|-------------------|----------|--------------------------|---------|")
    for c in cases:
        b, e = c["baseline"], c["enhanced"]
        base_state = (
            f"success, {b['candidates']} cand." if b["success"] else "validation failed"
        )
        enh_state = (
            f"success, {e['candidates']} cand." if e["success"] else "validation failed"
        )
        sources = ", ".join(e["sources"]) if e["sources"] else "none"
        rel = f"{_fmt(b['reliability'])} → {_fmt(e['reliability'])}"
        lines.append(
            f"| {c['label']} | `{c['profile'].get('favorite_genre')}` | "
            f"{_fmt(c['context'])} | {base_state} | {sources} | {enh_state} | {rel} | {c['note']} |"
        )
    lines.append("")
    lines.append("## Case Details")
    lines.append("")
    for c in cases:
        b, e = c["baseline"], c["enhanced"]
        lines.append(f"### {c['label']}")
        lines.append("")
        lines.append(c["description"])
        lines.append("")
        lines.append("| Field | Baseline | Enhanced |")
        lines.append("|-------|----------|----------|")
        lines.append(f"| success | {b['success']} | {e['success']} |")
        lines.append(f"| cleaned genre | {_fmt(b['genre'])} | {_fmt(e['genre'])} |")
        lines.append(f"| retrieved candidates | {b['candidates']} | {e['candidates']} |")
        lines.append(f"| recommendations | {b['recommendations']} | {e['recommendations']} |")
        lines.append(f"| preference alignment | {_fmt(b['alignment'])} | {_fmt(e['alignment'])} |")
        lines.append(f"| reliability score | {_fmt(b['reliability'])} | {_fmt(e['reliability'])} |")
        lines.append(f"| knowledge sources | none | {', '.join(e['sources']) if e['sources'] else 'none'} |")
        lines.append(f"| normalized genre | — | {_fmt(e['normalized_genre'])} |")
        lines.append(f"| inferred context | — | {_fmt(e['inferred_context'])} |")
        lines.append("")
        lines.append(f"**Outcome:** {c['note']}")
        lines.append("")

    with open(RESULTS_PATH, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


def main() -> None:
    songs = load_songs("data/songs.csv")
    agent = RecommendationAgent(songs)

    cases = [run_case(agent, *case) for case in CASES]
    for case in cases:
        print_case(case)
    print("=" * 72)

    write_markdown(cases)
    print(f"Comparison table written to {RESULTS_PATH}")


if __name__ == "__main__":
    main()
