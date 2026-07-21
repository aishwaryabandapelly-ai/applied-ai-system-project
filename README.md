# 🎵 Music Recommender Simulation

## Project Summary

In this project you will build and explain a small music recommender system.

Your goal is to:

- Represent songs and a user "taste profile" as data
- Design a scoring rule that turns that data into recommendations
- Evaluate what your system gets right and wrong
- Reflect on how this mirrors real world AI recommenders

Replace this paragraph with your own summary of what your version does.

---

## How The System Works

This recommender uses a simple content-based scoring system. Each song has a set of attributes (`genre`, `mood`, `energy`, `acousticness`), and the user has a taste profile with matching preferences (`favorite_genre`, `favorite_mood`, `target_energy`, `likes_acoustic`). The system compares every song against the user's profile, turns that comparison into a single number, and recommends whichever songs score the highest — so a song moves from raw data into a recommendation purely by how closely its attributes line up with what the user said they want.

The starter catalog was also expanded with additional fictional songs spanning genres and moods the original dataset didn't cover (e.g. hip hop, folk, electronic, classical, r&b, metal, reggae, country), so the recommender has more variety to distinguish between when scoring.

### Example User Profile

```python
user_profile = {
    "favorite_genre": "lofi",
    "favorite_mood": "chill",
    "target_energy": 0.35,
    "likes_acoustic": True
}
```

### Algorithm Recipe

- **Genre match** — `+2.0` points if `song.genre == user.favorite_genre`, else `0`.
- **Mood match** — `+1.0` point if `song.mood == user.favorite_mood`, else `0`.
- **Energy closeness** — `energy_score = 1 - abs(song.energy - user.target_energy)`, so a song doesn't need to match the target energy exactly, just be close to it (range `0`–`1`).
- **Acoustic preference** — if `likes_acoustic` is `True`, `acoustic_score = song.acousticness`; if `False`, `acoustic_score = 1 - song.acousticness` (range `0`–`1`).

Final score:

```python
final_score = genre_score + mood_score + energy_score + acoustic_score
```

The maximum possible score is `5.0` (`2.0 + 1.0 + 1.0 + 1.0`).

### Ranking Rule

Every song in the catalog is scored the same way, one at a time. Once all songs have a `final_score`, the full list is sorted from highest to lowest, and the Top K songs are returned as recommendations.

### Bias Note

This system may over-prioritize genre and miss good songs that match the user's mood or energy but are from a different genre. It may also create a filter bubble by repeatedly recommending similar songs. Since the dataset is small, some genres and moods may be underrepresented, which can skew what the recommender is able to surface.

---

## Getting Started

### Setup

1. Create a virtual environment (optional but recommended):

   ```bash
   python -m venv .venv
   source .venv/bin/activate      # Mac or Linux
   .venv\Scripts\activate         # Windows

2. Install dependencies

```bash
pip install -r requirements.txt
```

3. Run the app:

```bash
python -m src.main
```

### Running Tests

Run the starter tests with:

```bash
pytest
```

You can add more tests in `tests/test_recommender.py`.

---

## Sample Recommendation Output

Paste a sample of your recommender's output here as a text block so a reader can see what it produces:

```
# e.g.:
# User profile: genre=indie, mood=chill, energy=low
# Recommendations:
#   1. ...
#   2. ...
#   3. ...
```

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or demo video link here -->

---

## Experiments You Tried

Use this section to document the experiments you ran. For example:

- What happened when you changed the weight on genre from 2.0 to 0.5
- What happened when you added tempo or valence to the score
- How did your system behave for different types of users

---

## Limitations and Risks

Summarize some limitations of your recommender.

Examples:

- It only works on a tiny catalog
- It does not understand lyrics or language
- It might over favor one genre or mood

You will go deeper on this in your model card.

---

## Reflection

Read and complete `model_card.md`:

[**Model Card**](model_card.md)

Write 1 to 2 paragraphs here about what you learned:

- about how recommenders turn data into predictions
- about where bias or unfairness could show up in systems like this



