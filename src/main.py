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


def print_recommendations(songs, user_prefs, k=5) -> None:
    recommendations = recommend_songs(user_prefs, songs, k=k)
    for rank, (song, score, explanation) in enumerate(recommendations, start=1):
        print(f"{rank}. {song['title']} by {song['artist']}")
        print(f"   Score: {score:.2f}")
        print("   Reasons:")
        for reason in explanation.split(", "):
            print(f"   - {reason}")
        print()


def main() -> None:
    songs = load_songs("data/songs.csv")

    for label, user_prefs in PROFILES:
        print("=" * 60)
        print(f"Profile: {label}")
        print(f"  {user_prefs}")
        print("=" * 60)
        print("Top recommendations:\n")
        print_recommendations(songs, user_prefs, k=5)


if __name__ == "__main__":
    main()
