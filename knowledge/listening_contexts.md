# Listening Contexts Knowledge Base

A small, hand-authored knowledge base mapping common listening contexts to
recommendation attributes supported by the TuneGuide AI catalog. Every mood and
genre listed here exists in `data/songs.csv`. These are hints used to fill
*missing* profile fields; explicit user preferences always take priority.

Format per context (parsed deterministically):

- `suggested_moods`: comma-separated moods (first is used to fill a missing mood)
- `target_energy`: a `low-high` range (midpoint fills a missing target energy)
- `acoustic_preference`: `true` or `false`
- `instrumentalness_preference`: `high`, `medium`, or `low` (informational)
- `possible_genres`: comma-separated genres (first fills a missing genre)

## studying
- suggested_moods: focused, chill
- target_energy: 0.20-0.45
- acoustic_preference: true
- instrumentalness_preference: high
- possible_genres: lofi, ambient, classical, jazz

## working out
- suggested_moods: intense, confident, euphoric
- target_energy: 0.75-1.00
- acoustic_preference: false
- instrumentalness_preference: low
- possible_genres: electronic, hip hop, metal, pop

## relaxing
- suggested_moods: relaxed, chill
- target_energy: 0.20-0.45
- acoustic_preference: true
- instrumentalness_preference: medium
- possible_genres: ambient, folk, jazz, lofi

## commuting
- suggested_moods: uplifting, happy
- target_energy: 0.50-0.75
- acoustic_preference: false
- instrumentalness_preference: low
- possible_genres: pop, indie pop, rock, hip hop

## sleeping
- suggested_moods: chill, relaxed
- target_energy: 0.05-0.30
- acoustic_preference: true
- instrumentalness_preference: high
- possible_genres: ambient, classical, lofi

## party
- suggested_moods: euphoric, happy, confident
- target_energy: 0.75-1.00
- acoustic_preference: false
- instrumentalness_preference: low
- possible_genres: pop, electronic, hip hop, reggae
