import csv
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

@dataclass
class Song:
    """
    Represents a song and its attributes.
    Required by tests/test_recommender.py
    """
    id: int
    title: str
    artist: str
    genre: str
    mood: str
    energy: float
    tempo_bpm: float
    valence: float
    danceability: float
    acousticness: float

@dataclass
class UserProfile:
    """
    Represents a user's taste preferences.
    Required by tests/test_recommender.py
    """
    favorite_genre: str
    favorite_mood: str
    target_energy: float
    likes_acoustic: bool

class Recommender:
    """
    OOP implementation of the recommendation logic.
    Required by tests/test_recommender.py
    """
    def __init__(self, songs: List[Song]):
        self.songs = songs

    def recommend(self, user: UserProfile, k: int = 5) -> List[Song]:
        # TODO: Implement recommendation logic
        return self.songs[:k]

    def explain_recommendation(self, user: UserProfile, song: Song) -> str:
        # TODO: Implement explanation logic
        return "Explanation placeholder"

def load_songs(csv_path: str) -> List[Dict]:
    """Load song data from a CSV file and convert numeric fields."""
    songs = []
    with open(csv_path, newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            row["id"] = int(row["id"])
            row["energy"] = float(row["energy"])
            row["tempo_bpm"] = float(row["tempo_bpm"])
            row["valence"] = float(row["valence"])
            row["danceability"] = float(row["danceability"])
            row["acousticness"] = float(row["acousticness"])
            row["popularity"] = int(row["popularity"])
            row["release_decade"] = int(row["release_decade"])
            row["instrumentalness"] = float(row["instrumentalness"])
            row["is_explicit"] = row["is_explicit"].strip().lower() == "true"
            songs.append(row)

    print(f"Loaded {len(songs)} songs from {csv_path}")
    return songs

def get_scoring_weights(mode: str) -> Dict[str, float]:
    """Return the genre/mood/energy/acoustic multipliers for a ranking strategy."""
    scoring_modes = {
        "balanced": {"genre": 2.0, "mood": 1.0, "energy": 1.0, "acoustic": 1.0},
        "genre_first": {"genre": 3.0, "mood": 1.0, "energy": 1.0, "acoustic": 1.0},
        "mood_first": {"genre": 2.0, "mood": 2.0, "energy": 1.0, "acoustic": 1.0},
        "energy_focused": {"genre": 2.0, "mood": 1.0, "energy": 2.0, "acoustic": 1.0},
    }
    return scoring_modes.get(mode, scoring_modes["balanced"])

def score_song(user_prefs: Dict, song: Dict, mode: str = "balanced") -> Tuple[float, List[str]]:
    """Calculate a recommendation score and reasons for one song, using the given scoring mode."""
    weights = get_scoring_weights(mode)
    reasons = []

    genre_score = weights["genre"] if song["genre"] == user_prefs["favorite_genre"] else 0.0
    if genre_score:
        reasons.append(f"genre match (+{genre_score:.1f})")

    mood_score = weights["mood"] if song["mood"] == user_prefs["favorite_mood"] else 0.0
    if mood_score:
        reasons.append(f"mood match (+{mood_score:.1f})")

    energy_score = weights["energy"] * (1 - abs(song["energy"] - user_prefs["target_energy"]))
    reasons.append(f"energy closeness (+{energy_score:.2f})")

    if user_prefs["likes_acoustic"]:
        acoustic_score = weights["acoustic"] * song["acousticness"]
    else:
        acoustic_score = weights["acoustic"] * (1 - song["acousticness"])
    reasons.append(f"acoustic preference (+{acoustic_score:.2f})")

    # popularity and instrumentalness are the only new features scored for now;
    # language, release_decade, and is_explicit are loaded but not used in scoring yet.
    popularity_score = song["popularity"] / 100
    reasons.append(f"popularity bonus (+{popularity_score:.2f})")

    instrumental_score = song["instrumentalness"] * 0.5
    reasons.append(f"instrumentalness bonus (+{instrumental_score:.2f})")

    final_score = (
        genre_score
        + mood_score
        + energy_score
        + acoustic_score
        + popularity_score
        + instrumental_score
    )

    return final_score, reasons

def recommend_songs(
    user_prefs: Dict, songs: List[Dict], k: int = 5, mode: str = "balanced"
) -> List[Tuple[Dict, float, str]]:
    """Rank songs by score and return the top recommendations, using the given scoring mode."""
    scored_songs = []
    for song in songs:
        score, reasons = score_song(user_prefs, song, mode=mode)
        explanation = ", ".join(reasons)
        scored_songs.append((song, score, explanation))

    ranked_songs = sorted(scored_songs, key=lambda item: item[1], reverse=True)

    return ranked_songs[:k]
