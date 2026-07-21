"""
Command line runner for the Music Recommender Simulation.

This file helps you quickly run and test your recommender.

You will implement the functions in recommender.py:
- load_songs
- score_song
- recommend_songs
"""

from src.recommender import load_songs, recommend_songs


# Phase 4: a spread of user profiles to evaluate the recommender against,
# plus two edge cases with conflicting or unmatched preferences.
PROFILES = [
    (
        "High-Energy Pop",
        {
            "favorite_genre": "pop",
            "favorite_mood": "happy",
            "target_energy": 0.85,
            "likes_acoustic": False,
        },
    ),
    (
        "Chill Lofi",
        {
            "favorite_genre": "lofi",
            "favorite_mood": "chill",
            "target_energy": 0.35,
            "likes_acoustic": True,
        },
    ),
    (
        "Deep Intense Rock",
        {
            "favorite_genre": "rock",
            "favorite_mood": "intense",
            "target_energy": 0.90,
            "likes_acoustic": False,
        },
    ),
    (
        "Edge Case: Conflicting Signals (rock genre, but chill/low-energy/acoustic prefs)",
        {
            "favorite_genre": "rock",
            "favorite_mood": "chill",
            "target_energy": 0.15,
            "likes_acoustic": True,
        },
    ),
    (
        "Edge Case: No Catalog Match (genre/mood not in dataset)",
        {
            "favorite_genre": "k-pop",
            "favorite_mood": "euphoric",
            "target_energy": 0.5,
            "likes_acoustic": False,
        },
    ),
]


def print_recommendations(songs, user_prefs, k=5, mode="balanced") -> None:
    """Print recommendations for one profile as a simple ASCII table."""
    recommendations = recommend_songs(user_prefs, songs, k=k, mode=mode)

    headers = ["Rank", "Song Title", "Artist", "Score", "Reasons"]
    rows = []
    for rank, (song, score, explanation) in enumerate(recommendations, start=1):
        reasons = explanation.replace(", ", "; ")
        rows.append([str(rank), song["title"], song["artist"], f"{score:.2f}", reasons])

    widths = [len(header) for header in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    def format_row(row):
        return " | ".join(cell.ljust(widths[i]) for i, cell in enumerate(row))

    separator = "-+-".join("-" * width for width in widths)

    print(format_row(headers))
    print(separator)
    for row in rows:
        print(format_row(row))
    print()


def main() -> None:
    songs = load_songs("data/songs.csv")

    for label, user_prefs in PROFILES:
        print("=" * 60)
        print(f"Profile: {label}")
        print(f"  {user_prefs}")
        print("=" * 60)
        print("Top recommendations (mode: balanced):\n")
        print_recommendations(songs, user_prefs, k=5, mode="balanced")

    # Optional Challenge 2: demonstrate switching scoring modes on one profile.
    demo_label, demo_prefs = PROFILES[0]
    print("=" * 60)
    print(f"Scoring Mode Comparison — Profile: {demo_label}")
    print(f"  {demo_prefs}")
    print("=" * 60)
    for mode in ("balanced", "energy_focused"):
        print(f"Mode: {mode}\n")
        print_recommendations(songs, demo_prefs, k=5, mode=mode)


if __name__ == "__main__":
    main()
