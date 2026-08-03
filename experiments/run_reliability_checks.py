"""
Reliability experiment for TuneGuide AI (Phase 5).

Runs several fixed profiles through the integrated ``RecommendationAgent`` and
prints a compact reliability summary for each. It uses the reliability report
the agent already attaches — it does NOT re-implement any evaluator logic.

Reproducible and non-interactive:

    python -m experiments.run_reliability_checks
"""

from src.recommender import load_songs
from src.agent import RecommendationAgent

# Fixed profiles (no user input) so the run is reproducible.
PROFILES = [
    (
        "High-Energy Pop",
        {"favorite_genre": "pop", "favorite_mood": "happy", "target_energy": 0.85, "likes_acoustic": False},
    ),
    (
        "Chill Lofi",
        {"favorite_genre": "lofi", "favorite_mood": "chill", "target_energy": 0.35, "likes_acoustic": True},
    ),
    (
        "Intense Rock",
        {"favorite_genre": "rock", "favorite_mood": "intense", "target_energy": 0.90, "likes_acoustic": False},
    ),
    (
        "No Catalog Match (k-pop / euphoric)",
        {"favorite_genre": "k-pop", "favorite_mood": "euphoric", "target_energy": 0.50, "likes_acoustic": False},
    ),
]


def _print_report(label: str, result) -> None:
    print("=" * 68)
    print(f"Profile: {label}")
    if not result.success:
        print(f"  Request invalid: {result.errors}")
        return

    report = result.reliability_report
    m = report.metrics
    print(f"  Success: {result.success} | Reliability: {report.score}/100 | Passed: {report.passed}")
    print(f"  Summary: {report.summary}")
    print(
        "  Metrics: "
        f"coverage={m['explanation_coverage']}, "
        f"alignment={m['preference_alignment']}, "
        f"unique_artist_ratio={m['unique_artist_ratio']}, "
        f"unique_genre_ratio={m['unique_genre_ratio']}, "
        f"duplicates={m['duplicate_count']}"
    )
    print(f"  Returned {m['returned_count']} of {m['retrieved_candidate_count']} retrieved candidate(s).")
    print("  Checks:")
    for check in report.checks:
        status = "PASS" if check.passed else "FAIL"
        print(f"    [{status}] {check.name}: {check.message}")


def main() -> None:
    songs = load_songs("data/songs.csv")
    agent = RecommendationAgent(songs)

    for label, profile in PROFILES:
        result = agent.recommend(profile, k=5, mode="balanced")
        _print_report(label, result)
    print("=" * 68)


if __name__ == "__main__":
    main()
