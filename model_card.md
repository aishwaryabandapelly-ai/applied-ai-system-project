# 🎧 Model Card: Music Recommender Simulation

## 1. Model Name  

**VibeFinder 1.0**

A simple, explainable recommender that picks songs by comparing a listener's stated taste to each song's tags and numbers.

---

## 2. Intended Use  

Describe what your recommender is designed to do and who it is for. 

Prompts:  

- What kind of recommendations does it generate  
- What assumptions does it make about the user  
- Is this for real users or classroom exploration  

**Goal:** VibeFinder suggests songs by comparing a user's taste profile (favorite genre, favorite mood, target energy, and whether they like acoustic songs) to each song's features, and recommending whichever songs match best.

**Intended use:** This is a beginner educational simulation. It's meant to help me understand, hands-on, how a scoring-and-ranking recommender works under the hood — not to serve real listeners. It assumes a user can state simple, clear preferences up front; it does not learn from listening history or feedback.

**Non-intended use:** VibeFinder is not meant for a real music app. It is not production-level software, and it is not personalized enough for real users — it only knows four simple preferences and works off of a tiny, fictional catalog of songs.

---

## 3. How the Model Works  

Explain your scoring approach in simple language.  

Prompts:  

- What features of each song are used (genre, energy, mood, etc.)  
- What user preferences are considered  
- How does the model turn those into a score  
- What changes did you make from the starter logic  

Avoid code here. Pretend you are explaining the idea to a friend who does not program.

VibeFinder gives every song a score based on how well it matches the listener's taste profile, then recommends the highest-scoring songs.

- If a song's genre matches the listener's favorite genre, it earns extra points — this is the biggest single bonus.
- If a song's mood matches the listener's favorite mood, it earns a smaller bonus.
- If a song's energy level is close to the energy the listener asked for, it earns points for that closeness. A song doesn't have to match exactly — the closer it is, the more points it earns.
- If the listener likes acoustic songs, more acoustic songs earn more points; if the listener does not like acoustic songs, less acoustic songs earn more points instead.
- All of these points get added together into one final score for the song.
- Once every song in the catalog has a score, they're sorted from highest to lowest, and the top few are shown as recommendations, along with a short explanation of why each one was picked.

---

## 4. Data  

Describe the dataset the model uses.  

Prompts:  

- How many songs are in the catalog  
- What genres or moods are represented  
- Did you add or remove data  
- Are there parts of musical taste missing in the dataset  

The dataset lives in `data/songs.csv` and now has 18 songs. The original starter set had 10 songs; I expanded it with 8 additional fictional songs covering genres the original catalog didn't have — hip hop, folk, electronic, classical, r&b, metal, reggae, and country. Each song has a title, an artist, a genre tag, a mood tag, and five numeric features: energy, tempo_bpm, valence, danceability, and acousticness. All of the songs and artists are fictional and made up for this project — none of them are real tracks. The dataset is still intentionally small and sample-based rather than a realistic catalog, so some genres and moods are represented only once or twice, and parts of musical taste (tempo, valence, danceability, lyrics, instrumentation) aren't factored into the scoring yet even though the data for some of them already exists.

---

## 5. Strengths  

Where does your system seem to work well  

Prompts:  

- User types for which it gives reasonable results  
- Any patterns you think your scoring captures correctly  
- Cases where the recommendations matched your intuition  

The recommender works well whenever a listener's genre, mood, and numeric preferences all point the same direction. The High-Energy Pop, Chill Lofi, and Deep Intense Rock profiles (see Evaluation below) each produced a clear, obviously-correct #1 recommendation — a song that was already tagged with the right genre and mood, and that also happened to sit close to the requested energy level and acoustic preference. In those "everything agrees" cases, the scoring behaves exactly the way a person would expect it to.

---

## 6. Limitations and Bias 

Where the system struggles or behaves unfairly. 

Prompts:  

- Features it does not consider  
- Genres or moods that are underrepresented  
- Cases where the system overfits to one preference  
- Ways the scoring might unintentionally favor some users  

The scoring formula may over-prioritize genre by giving it the largest fixed bonus (+2.0), so a song can rank highly even when its mood, energy, and acousticness are not a perfect fit. Because the catalog is small, with only a limited number of songs and some genres or moods represented only once, certain user profiles may not have many strong candidates to choose from. The `likes_acoustic` field is also too simple because it forces every user into a True/False preference, while real acoustic preference is usually more flexible. The weight-shift experiment showed that changing feature weights can significantly change the rankings, meaning the recommender is sensitive to design choices and could accidentally override a user's stated preference. The system can also create a filter bubble: because genre and mood dominate the score and the catalog is small, the same handful of songs tend to resurface at the top for a given profile, with no built-in way to encourage variety or new discovery.

---

## 7. Evaluation  

How you checked whether the recommender behaved as expected. 

Prompts:  

- Which user profiles you tested  
- What you looked for in the recommendations  
- What surprised you  
- Any simple tests or comparisons you ran  

No need for numeric metrics unless you created some.

### Profiles Tested

I ran `python -m src.main` against four kinds of user profiles to see how the recommender behaves: three "normal" listener personas (High-Energy Pop, Chill Lofi, Deep Intense Rock), and one adversarial profile designed to expose weaknesses (Conflicting Signals). I compared the top recommendations across all four to see whether the scoring behaved consistently, and I also ran a weight-shift experiment — temporarily changing the genre and energy weights — to see how much the rankings changed when the formula was tuned differently (see Limitations and Bias above for what that revealed).

**1. High-Energy Pop** (`favorite_genre="pop"`, `favorite_mood="happy"`, `target_energy=0.85`, `likes_acoustic=False`)

```text
Rank | Song Title     | Artist        | Score | Reasons
-----+----------------+---------------+-------+---------------------------------------------------------------------------------------------
1    | Sunrise City   | Neon Echo     | 4.79  | genre match (+2.0); mood match (+1.0); energy closeness (+0.97); acoustic preference (+0.82)
2    | Gym Hero       | Max Pulse     | 3.87  | genre match (+2.0); energy closeness (+0.92); acoustic preference (+0.95)
3    | Rooftop Lights | Indigo Parade | 2.56  | mood match (+1.0); energy closeness (+0.91); acoustic preference (+0.65)
4    | Pulse Horizon  | Kilowatt      | 1.87  | energy closeness (+0.90); acoustic preference (+0.97)
5    | Iron Verdict   | Grave Circuit | 1.86  | energy closeness (+0.88); acoustic preference (+0.98)
```

This one makes sense at a glance: the winner, "Sunrise City," is literally tagged `pop`/`happy` in the data, so it collects both fixed bonuses, and it also happens to be high-energy and not very acoustic — exactly what this listener asked for. Everything lined up, so the #1 pick feels obviously correct.

**2. Chill Lofi** (`favorite_genre="lofi"`, `favorite_mood="chill"`, `target_energy=0.35`, `likes_acoustic=True`)

```text
Rank | Song Title          | Artist         | Score | Reasons
-----+---------------------+----------------+-------+---------------------------------------------------------------------------------------------
1    | Library Rain        | Paper Lanterns | 4.86  | genre match (+2.0); mood match (+1.0); energy closeness (+1.00); acoustic preference (+0.86)
2    | Midnight Coding     | LoRoom         | 4.64  | genre match (+2.0); mood match (+1.0); energy closeness (+0.93); acoustic preference (+0.71)
3    | Focus Flow          | LoRoom         | 3.73  | genre match (+2.0); energy closeness (+0.95); acoustic preference (+0.78)
4    | Spacewalk Thoughts  | Orbit Bloom    | 2.85  | mood match (+1.0); energy closeness (+0.93); acoustic preference (+0.92)
5    | Coffee Shop Stories | Slow Stereo    | 1.87  | energy closeness (+0.98); acoustic preference (+0.89)
```

Same story here — a soft, low-energy, mostly-acoustic song ("Library Rain") that's already tagged `lofi`/`chill` comes out on top with a near-perfect score. Compared to the High-Energy Pop result, the ranking "shape" is the same (a clean top pick everyone would agree with), just built from opposite raw numbers — low energy and high acousticness instead of high energy and low acousticness. That's a good sign: the formula treats "closeness to target" the same way regardless of which direction the target points.

**3. Deep Intense Rock** (`favorite_genre="rock"`, `favorite_mood="intense"`, `target_energy=0.90`, `likes_acoustic=False`)

```text
Rank | Song Title    | Artist        | Score | Reasons
-----+---------------+---------------+-------+---------------------------------------------------------------------------------------------
1    | Storm Runner  | Voltline      | 4.89  | genre match (+2.0); mood match (+1.0); energy closeness (+0.99); acoustic preference (+0.90)
2    | Gym Hero      | Max Pulse     | 2.92  | mood match (+1.0); energy closeness (+0.97); acoustic preference (+0.95)
3    | Pulse Horizon | Kilowatt      | 1.92  | energy closeness (+0.95); acoustic preference (+0.97)
4    | Iron Verdict  | Grave Circuit | 1.91  | energy closeness (+0.93); acoustic preference (+0.98)
5    | Sunrise City  | Neon Echo     | 1.74  | energy closeness (+0.92); acoustic preference (+0.82)
```

"Storm Runner" wins clearly and correctly — but this also reveals a catalog limitation: it's the *only* `rock`-tagged song in the whole dataset. There's no runner-up that also matches genre, so anyone with this taste profile only ever gets one "real" match no matter how the recommender is tuned. The #2 pick, "Gym Hero," is a `pop` song that only sneaks in because it happens to be high-energy — a plausible backup, but not a genuine rock recommendation.

**4. Edge case — Conflicting Signals** (`favorite_genre="rock"`, `favorite_mood="chill"`, `target_energy=0.15`, `likes_acoustic=True` — a listener who says they like rock, but everything else about them points toward soft, quiet music)

```text
Rank | Song Title         | Artist           | Score | Reasons
-----+--------------------+------------------+-------+--------------------------------------------------------------------------
1    | Spacewalk Thoughts | Orbit Bloom      | 2.79  | mood match (+1.0); energy closeness (+0.87); acoustic preference (+0.92)
2    | Library Rain       | Paper Lanterns   | 2.66  | mood match (+1.0); energy closeness (+0.80); acoustic preference (+0.86)
3    | Midnight Coding    | LoRoom           | 2.44  | mood match (+1.0); energy closeness (+0.73); acoustic preference (+0.71)
4    | Storm Runner       | Voltline         | 2.34  | genre match (+2.0); energy closeness (+0.24); acoustic preference (+0.10)
5    | Glass Cathedral    | Solene Marchetti | 1.85  | energy closeness (+0.90); acoustic preference (+0.95)
```

This is the surprise. "Storm Runner" is the *only* song in the whole catalog that matches this listener's stated favorite genre (`rock`), yet it drops to 4th place, beaten out by three lofi/ambient songs that don't match genre at all. The reason is plain arithmetic: the genre bonus (+2.0) is fixed, but "Storm Runner" is a loud, non-acoustic song, so it loses almost a full point on energy and 0.9 of a point on acousticness — enough to sink below songs that match none of the categorical preferences but fit the mood/energy/acoustic numbers closely. In plain terms: a listener who explicitly says "I like rock" can end up not being shown the one rock song available, because the math lets quieter, non-rock songs out-earn it on the numeric side. That's a real limitation — the formula can quietly override an explicit, stated preference.

**Comparing across profiles:** when a listener's genre, mood, and numeric preferences all point the same direction (profiles 1–3), the top pick is obvious and satisfying, and the catalog's small size mostly just means "few options," not "wrong options." But profile 4 shows that once a listener's stated genre conflicts with their other preferences, the recommender doesn't recognize that tension — it just adds up four independent numbers and lets the biggest total win, even if that total buries the one song that actually matches what the listener said they wanted most.

### High-Energy Pop Result Explanation

For the High-Energy Pop profile (`favorite_genre="pop"`, `favorite_mood="happy"`, `target_energy=0.85`, `likes_acoustic=False`), the top recommendation was "Sunrise City" by Neon Echo, scoring 4.79 out of a possible 5.0. This song matched both categorical preferences (genre +2.0, mood +1.0) and scored well on both continuous features (energy closeness +0.97, since its energy of 0.82 sits close to the 0.85 target; acoustic preference +0.82, since its low acousticness of 0.18 suits a user who dislikes acoustic songs). All four components reinforced each other rather than conflicting, which made this an intuitive, easy-to-explain #1 result and confirms the scoring formula behaves as expected in the straightforward case.

---

## 8. Future Work  

Ideas for how you would improve the model next.  

Prompts:  

- Additional features or preferences  
- Better ways to explain recommendations  
- Improving diversity among the top results  
- Handling more complex user tastes  

- Add real user feedback: track likes, skips, playlists, and listening history so the recommender can learn over time instead of relying only on a static, hand-entered profile.
- Expand the dataset with more songs so genres and moods are represented more than once or twice each, and add diversity scoring so the top results don't repeatedly surface the same handful of songs.
- Add preferences for tempo, valence, and danceability (the data already exists in `songs.csv`, it's just not scored yet) for finer-grained matching, and longer-term, explore collaborative filtering — recommending based on what similar listeners liked — instead of relying only on hand-written scoring rules.

---

## 9. Personal Reflection  

A few sentences about your experience.  

Prompts:  

- What you learned about recommender systems  
- Something unexpected or interesting you discovered  
- How this changed the way you think about music recommendation apps  

**Biggest learning moment:** I learned that recommendation systems are not magic — they are built from clear scoring rules and ranking decisions. Once I could see the actual math behind each recommendation (genre points + mood points + energy closeness + acoustic preference, all added together), the idea of a "recommendation algorithm" stopped feeling mysterious.

**How AI tools helped:** Claude helped me brainstorm formulas, debug code, and explain results — from designing the initial scoring recipe, to implementing `load_songs`/`score_song`/`recommend_songs`, to walking through why a specific song ranked where it did.

**When I needed to double-check the AI:** I still had to check whether the weights matched my intended design. For example, I caught that the CLI's default profile had mismatched dictionary keys that would have silently crashed the recommender, and I had to explicitly decide whether to keep or revert the weight-shift experiment rather than assume the "new" numbers were automatically better.

**What surprised me:** I was surprised that even a simple weighted-score algorithm could produce recommendations that felt reasonable — a handful of if-statements and one subtraction formula were enough to produce a top pick that "made sense" for each listener persona.

**What I'd try next:** If I extended the project, I would add real user feedback like likes, skips, playlists, and listening history, so the recommender could learn from behavior instead of only comparing static preferences.
