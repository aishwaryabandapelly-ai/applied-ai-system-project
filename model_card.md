# 🎧 Model Card: TuneGuide AI — Explainable Music Recommendation Agent

## 1. System Name

**TuneGuide AI — Explainable Music Recommendation Agent**

An explainable, reliability-aware music recommendation agent that validates input, retrieves candidate songs, scores and ranks them with transparent rules, attaches evidence-based explanations, and evaluates the reliability of its own output.

---

## 2. System Overview

TuneGuide AI takes a user preference profile (favorite genre, favorite mood, target energy, and acoustic preference) and returns a ranked list of song recommendations, each accompanied by a plain-language explanation and an overall reliability report.

It evolved from an earlier Module 1–3 project, the **Music Recommender Simulation**, which scored a small catalog of fictional songs against a taste profile and printed the top matches as a terminal table. TuneGuide AI keeps that original scoring, ranking, and diversity logic as its core and wraps it in a modular agentic workflow that adds validation, dedicated retrieval, structured explanations, reliability evaluation, and logging.

**Main pipeline:**

```
validation → retrieval → scoring/ranking → explanations → reliability evaluation
```

Each stage is a separate module coordinated by a recommendation agent, so components can be tested and reasoned about independently. The architecture is captured in [diagrams/architecture.mmd](diagrams/architecture.mmd).

---

## 3. Intended Use

- **Educational demonstration** of how an explainable, reliability-aware recommendation pipeline is assembled.
- **Music recommendation experimentation** with different profiles and scoring modes.
- **AI system design, explainability, and reliability testing** — studying validation, orchestration, evidence-based explanation, and self-evaluation.
- **Portfolio use** — demonstrating applied AI system design.

---

## 4. Out-of-Scope Use

- **Not** for production-scale music streaming.
- **Not** for emotional or mental-health inference.
- **Not** for sensitive or high-stakes decision-making.
- **Not** a substitute for real user listening history or professional recommendation infrastructure.

---

## 5. Data

- Uses [data/songs.csv](data/songs.csv).
- **18 fictional songs** — all titles and artists are invented for this project; none are real tracks.
- Structured metadata per song, including `genre`, `mood`, `energy`, `acousticness`, `popularity`, `instrumentalness`, `language`, and `release_decade` (plus `tempo_bpm`, `valence`, and `danceability`, which exist in the data but are not currently scored).
- **No real personal data and no real listening history.** The catalog is intentionally small and sample-based, so some genres and moods appear only once or twice.

---

### Retrieval Knowledge Sources (RAG stretch feature)

Beyond `data/songs.csv`, the enhanced retrieval consults two hand-authored local knowledge sources before recommendations are generated:

- `knowledge/genre_aliases.json` — maps informal genre spellings (e.g. `edm` → `electronic`) to canonical catalog genres.
- `knowledge/listening_contexts.md` — maps listening contexts (studying, working out, ...) to supported recommendation attributes.

These sources are small, hand-authored, and limited; incorrect or incomplete mappings can affect recommendations. They are used only to normalize genre aliases and to fill *missing* profile fields. Explicit user preferences always take priority over retrieved context, and unsupported aliases or contexts fail safely with no invented data.

### Specialization: Natural-Language Preference Interpreter (stretch feature)

The system includes a specialization layer that turns a natural-language request
(e.g. "I'm studying for my exam.") into a structured preference profile. It is
**not a learned or fine-tuned model**: it is deterministic keyword pattern
matching, documented in `src/preference_interpreter.py`, inspired by a small
synthetic dataset (`specialization/preference_examples.json`, ~24 hand-authored
examples). No AI model, randomness, or external service is involved.

Limitations: the rules and dataset are small and hand-authored, so requests
outside the documented keywords are not interpreted (they fall back to Low
confidence with no inference), and inferred profiles reflect the author's
mappings rather than a user's true intent. The interpreter fills only *missing*
profile fields; explicit user preferences always take priority.

## 6. Decision Process

- **Rule-based scoring** — transparent, fixed rules combine genre match, mood match, energy closeness, acoustic preference, and small popularity/instrumentalness bonuses into a single score. Four scoring modes (`balanced`, `genre_first`, `mood_first`, `energy_focused`) re-weight the profile-based components.
- **Candidate retrieval** — songs are filtered from the catalog by genre, mood, and energy window before scoring, with progressive fallback so results are never empty when the catalog is non-empty.
- **Diversity penalties** — repeated artists (−0.50) and repeated genres (−0.25) are penalized while building the top list to reduce repetition.
- **Evidence-based explanations** — each recommendation is explained using only the song's attributes, the profile, the score, and the raw scoring reasons.
- **Deterministic reliability score** — a 0–100 score from documented, equally weighted checks.
- **No external LLM or API at runtime** — every step is deterministic and self-contained.

---

## 7. Reliability and Evaluation

TuneGuide AI is validated by an automated test suite and by integrated reliability experiments run through the live agent.

- **166 automated tests passed; 0 failed.**
- **Four integrated reliability experiments** were run through the agent (via `experiments/run_reliability_checks.py`).
- **Reliability scores: 92, 88, 100, 81.**
- **Lowest-performing case:** the no-direct-catalog-match profile (requested k-pop, which is absent from the catalog), where retrieval fell back safely but preference alignment was low.

| Profile | Reliability Score | Overall Result |
|---------|-------------------|----------------|
| High-Energy Pop | 92 | Pass |
| Chill Lofi | 88 | Pass |
| Intense Rock | 100 | Pass |
| No Catalog Match | 81 | Pass |

Full details are in [experiments/reliability_results.md](experiments/reliability_results.md).

---

## 8. Limitations

- **Small fictional dataset** (18 invented songs) limits variety and coverage.
- **Metadata-only recommendations** — scoring relies on hand-authored tags and numbers, not audio analysis.
- **No real listening history** — only a stated profile is used.
- **No persistent learning** — the system does not remember or adapt across runs.
- **Rule-based interpretation** — the fixed formula may miss nuance a learned model could capture.
- **Fallback retrieval can reduce relevance** — when the requested category is absent, relaxed constraints keep results non-empty but less relevant.
- **Single-result diversity scores can look stronger than they really are** — a profile returning one song can earn perfect diversity even though one item cannot demonstrate broad variety.

---

## 9. Bias and Fairness Risks

- **Underrepresented genres or moods** — some categories appear only once or twice, so certain profiles have few strong candidates.
- **Genre-first weighting** — genre carries the largest bonus, so it can over-prioritize genre over mood, energy, or acousticness.
- **Popularity bonus** — awarding points for popularity can favor already-popular songs.
- **Small catalog** — uneven coverage across genres/moods skews what the system can surface.
- **Diversity penalties help but don't eliminate bias** — they reduce repetition of artists and genres but do not correct underlying catalog imbalance.

---

## 10. Transparency and Explainability

- **Every recommendation includes structured evidence** — a list of the contributing factors (genre match, mood match, energy closeness, acoustic preference, popularity/instrumentalness bonuses, and any diversity penalty), with numeric contributions preserved.
- **Confidence is deterministic** — labeled High / Medium / Low from a documented rule based on the number of direct preference matches and whether a diversity penalty applied; it does not depend on a hidden model.
- **Explanations are grounded only** in song metadata, profile values, scores, and the raw scoring reasons.
- **Unsupported claims are intentionally avoided** — the explainer never invents listening history, emotions, lyrics, or artist facts.

---

## 11. Human-in-the-Loop

- **Humans provide the profile** that drives every recommendation.
- **Humans can inspect explanations and reliability results** to judge whether a recommendation is trustworthy.
- **The system does not yet implement persistent feedback learning** — it neither stores nor learns from likes/dislikes across runs.
- **Final judgment remains with the user** — outputs are suggestions to be interpreted, not decisions to be accepted automatically.

---

## 12. Responsible AI Reflection

### A. How I collaborated with AI

I used Claude Code inside VS Code to inspect the repository, propose a phased plan, generate tests, and implement each module. I treated the AI as a coding assistant, not an unchecked decision-maker: I reviewed its outputs, read the diffs, ran the full test suite after every phase, and only accepted changes once they were verified. When something looked off, I asked for read-only diagnosis before making changes.

### B. One helpful AI suggestion

The most useful suggestion was the **phased implementation plan**: regression tests → guardrails → retriever → agent → explainer → evaluator. Starting with regression tests locked in the original recommender's behavior before I extended anything, and building one isolated module per phase meant each addition could be tested on its own. This preserved the working recommender and greatly reduced the risk of silently breaking existing behavior — every phase ended with all prior tests still passing.

### C. One flawed AI suggestion

One AI-generated **README draft included sample energy values that did not exactly match the experiment script** — it described the High-Energy Pop profile as energy 0.90 and the No Catalog Match profile as 0.70, when `experiments/run_reliability_checks.py` actually uses 0.85 and 0.50. The reliability scores were correct, but the input descriptions were not. I caught the mismatch by comparing the documentation against the source script, and corrected the values before finalizing the report. This taught me that confident-looking AI documentation can contain small factual drift, and that generated docs must be checked against the actual code — not trusted automatically just because the surrounding numbers are right.

### D. What I learned

AI can meaningfully accelerate implementation, but human review is still required. Tests, diffs, logs, and direct source verification were essential for catching both code issues and documentation errors. Responsible collaboration means verifying **both** the code and the documentation an AI produces, rather than assuming either is correct.

---

## 13. Risks and Mitigations

| Risk | Potential Impact | Current Mitigation |
|------|------------------|--------------------|
| Invalid input | Crash or garbage recommendations | Guardrails validate/clamp/reject input and return a safe failure result without raising |
| Missing catalog match | Empty or irrelevant results | Retriever progressively relaxes constraints so results are never empty when the catalog is non-empty; low alignment is surfaced |
| Duplicate recommendations | Repetitive, lower-quality list | Evaluator detects duplicates by stable id (or title + artist) as a critical check |
| Weak explanation coverage | Reduced transparency and trust | Evaluator requires one valid explanation per recommendation; shortfalls fail a critical check |
| Invalid scores/order | Misleading or broken ranking | Evaluator verifies scores are numeric, finite, and in descending order as a critical check |
| Limited diversity | Filter-bubble effect | Diversity penalties plus non-critical diversity metrics that lower the reliability score to keep the issue visible |
| Over-trusting AI-generated code or documentation | Undetected errors ship | Human review of diffs, full test suite per phase, and verifying docs against source (e.g., the energy-value correction above) |

---

## 14. Future Improvements

- Persistent user feedback (likes/dislikes/corrections) that updates the profile over time.
- Natural-language request parsing.
- A larger dataset with more songs per genre and mood.
- Real music metadata rather than hand-authored features.
- Better diversity evaluation for small result sets.
- Human evaluation with multiple reviewers.
- Semantic retrieval (e.g., vector similarity) instead of exact-attribute filtering.

---

## Reflection and Ethics

### 1. What are the limitations or biases in your system?

Working on TuneGuide AI made its limitations concrete for me. The catalog is a small, fictional dataset of only 18 songs, so several genres and moods appear just once or twice and some profiles simply have few strong candidates. Every recommendation is metadata-only: I score hand-authored tags and numbers, with no lyrics, no audio understanding, and no listening history to draw on. The scoring rules themselves carry bias — genre-first weighting gives genre the largest fixed bonus, so it can over-prioritize genre over mood, energy, or acousticness, and the popularity bonus can nudge already-popular songs upward. The diversity penalties I kept from the original recommender reduce repeated artists and genres, but they cannot eliminate the underlying imbalance in a small catalog. Ultimately it is a rule-based system, so it cannot capture the complex, shifting musical preferences a real listener has.

### 2. Could your AI be misused, and how would you prevent that?

TuneGuide AI is an educational recommendation system, and I want its boundaries to be clear. It should not be used for production music streaming, and it should never be used to infer emotions, personality, or mental health from someone's music choices. It is also not built for important decision-making of any kind. Several implemented parts of the system already reduce the chance of misuse. Input validation rejects or safely repairs bad input before it reaches the pipeline, so the system cannot be pushed into undefined behavior. The scoring is transparent, and every recommendation ships with evidence-based explanations, so no result is presented as an unexplained verdict. The reliability evaluation reports how trustworthy each result is instead of hiding weak cases. Most importantly, human interpretation remains central: the outputs are explainable suggestions to be judged by the user, not authoritative conclusions.

### 3. What surprised you while testing your AI's reliability?

The most instructive moment was the unsupported k-pop profile — a request for a genre the catalog does not contain. I expected either an error or an empty list, but the retrieval fallback relaxed its constraints and still returned alternatives, so the run completed successfully. What surprised me was that the reliability score still dropped (to 81) because preference alignment was honestly low. The system did not pretend the alternatives were a good match; it stayed robust while openly reporting reduced recommendation quality. That taught me that robustness and honesty are separate properties, and a good system should have both. I was also struck by how much the automated regression tests earned their place: they protected the original recommender's behavior at every step as I added new modules, so I could extend the system confidently without silently breaking what already worked.

### 4. Describe your collaboration with AI during this project.

I used Claude Code inside Visual Studio Code as a coding assistant throughout this project. It helped me inspect the repository, design the implementation roadmap, generate tests, implement the modular components, and improve the documentation. I did not accept its output blindly: I reviewed every suggestion, compared diffs, ran the full test suite, and verified results before keeping any change.

The single most helpful suggestion was the phased implementation order: regression tests → guardrails → retriever → recommendation agent → explanation generator → reliability evaluator. Writing regression tests first locked in the original recommender's behavior, and building one isolated module per phase meant every addition was tested on its own before the next began. This dramatically reduced the risk of breaking the working recommender, because each phase ended with all prior tests still passing.

Not every suggestion was correct. One AI-generated README draft contained sample `target_energy` values that did not exactly match the experiment configuration. I compared the documentation against `experiments/run_reliability_checks.py`, found the mismatch, and corrected it. The lesson stuck with me: AI-generated documentation should always be verified against the actual source, not accepted automatically just because it reads confidently.

---

## 15. Responsible Use Summary

TuneGuide AI is an **educational, transparent recommendation system**. Its recommendations are explainable suggestions grounded in song metadata and stated preferences — not objective judgments about music or listeners. Outputs should be interpreted with the system's limitations in mind, and the final decision always remains with the user.
