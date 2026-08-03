# 🎵 TuneGuide AI — Explainable Music Recommendation Agent

## Project Summary

TuneGuide AI is an Applied AI System that transforms a simple music recommender into a modular, explainable, and reliable recommendation pipeline.

The project demonstrates how multiple AI-inspired components—including input validation, candidate retrieval, agent orchestration, explanation generation, and reliability evaluation—can work together to produce trustworthy recommendations while remaining fully transparent and deterministic.

Unlike traditional recommendation systems that simply return a ranked list, TuneGuide AI explains why each recommendation was selected, validates user inputs before processing, evaluates the quality of its own recommendations, and logs every stage of the workflow for reproducibility and debugging.

This project was developed as the final Applied AI System project for CodePath AI110 by extending a previous Music Recommender Simulation into a complete end-to-end AI application.

---

# Original Project (Modules 1–3)

## Music Recommender Simulation

This project evolved from my earlier **Music Recommender Simulation**, developed during Modules 1–3.

The original recommender used a transparent content-based scoring system that compared each song's attributes against a user's taste profile. Songs were ranked using weighted preference matching while applying diversity penalties to reduce repeated artists and genres.

Rather than replacing that implementation, TuneGuide AI builds directly on top of it by introducing modular AI system components while preserving the original recommendation engine.

---

# Why This Project Matters

Modern recommendation systems are often difficult to understand because they behave like black boxes.

TuneGuide AI explores a different design philosophy:

- transparent recommendation logic
- explainable decision making
- deterministic behaviour
- modular AI architecture
- reliability evaluation
- human-centered system design

The goal is not to build the most complex recommender, but to demonstrate how AI systems can be understandable, testable, and trustworthy.

---

# Key Features

## Existing Recommendation Engine

- Content-based recommendation algorithm
- Weighted preference matching
- Four configurable scoring modes
- Diversity penalty for repeated artists and genres
- Explainable score contributions

## Applied AI Extensions

### Input Guardrails

- Validates user preference profiles
- Handles invalid values safely
- Cleans malformed inputs
- Prevents crashes before recommendation begins

### Candidate Retriever

Rather than scoring the full catalog immediately, TuneGuide AI first retrieves candidate songs using configurable filters:

- Genre
- Mood
- Energy range

If strict filtering produces no candidates, the retriever progressively relaxes constraints while ensuring deterministic behaviour.

### Recommendation Agent

The Recommendation Agent orchestrates the complete workflow:

Input Validation

↓

Candidate Retrieval

↓

Recommendation Engine

↓

Explanation Generation

↓

Reliability Evaluation

↓

Final Result

The agent coordinates existing modules instead of duplicating their logic.

### Evidence-Based Explanations

Each recommendation includes:

- recommendation summary
- structured evidence
- confidence level
- limitations

Every explanation is generated only from:

- song metadata
- user preferences
- recommendation score
- existing scoring reasons

No external LLM is used.

### Reliability Evaluation

After recommendations are produced, TuneGuide AI evaluates their quality using deterministic reliability checks.

Current checks include:

- duplicate detection
- explanation coverage
- score validity
- ranking correctness
- preference alignment
- diversity metrics
- result completeness

Each recommendation session receives:

- Reliability Score (0–100)
- pass/fail status
- detailed reliability report

### Logging

The system records:

- validation
- retrieval
- recommendation generation
- explanation generation
- reliability evaluation

using Python's built-in logging framework.

### Automated Testing

The project currently contains 114 automated tests, covering recommendation scoring, retrieval, guardrails, explanation generation, reliability evaluation, logging, orchestration, and regression protection.

---

# System Architecture

The project follows a modular AI architecture where every component performs a single responsibility.

```
User Request
      │
      ▼
Input Validation
      │
      ▼
Candidate Retrieval
      │
      ▼
Recommendation Agent
      │
      ▼
Recommendation Engine
      │
      ▼
Explanation Generator
      │
      ▼
Reliability Evaluator
      │
      ▼
Final Recommendation
```

A detailed Mermaid architecture diagram is available in:

```
diagrams/architecture.mmd
```

---

![TuneGuide AI Architecture](assets/architecture.png)

# Project Structure

```
applied-ai-system-project/

│
├── assets/
│
├── data/
│   └── songs.csv
│
├── diagrams/
│   └── architecture.mmd
│
├── experiments/
│   └── run_reliability_checks.py
│
├── logs/
│
├── src/
│   ├── agent.py
│   ├── evaluator.py
│   ├── explainer.py
│   ├── guardrails.py
│   ├── logging_config.py
│   ├── recommender.py
│   ├── retriever.py
│   └── main.py
│
├── tests/
│
├── README.md
├── model_card.md
└── ai_interactions.md
```

---

# How the System Works

The recommendation pipeline consists of several modular stages.

## Step 1 — User Preferences

The user provides:

- favorite genre
- favorite mood
- preferred energy level
- acoustic preference
- number of requested recommendations

---

## Step 2 — Guardrails

Inputs are validated before recommendation begins.

Examples include:

- invalid genres
- invalid mood values
- out-of-range energy values
- invalid recommendation counts

The guardrails either clean the input or return useful validation errors.

---

## Step 3 — Candidate Retrieval

The retriever narrows the search space using configurable filters.

Filters may include:

- genre
- mood
- energy window

If no candidates remain, constraints are progressively relaxed until valid recommendations can still be generated.

---

## Step 4 — Recommendation Engine

Candidate songs are scored using the original recommendation algorithm developed during Modules 1–3.

Scoring considers:

- genre similarity
- mood similarity
- energy closeness
- acoustic preference
- popularity bonus
- instrumentalness bonus

The recommendation engine itself was intentionally preserved rather than rewritten.

---

## Step 5 — Explanation Generation

Every recommendation is translated into a structured explanation describing:

- why it was selected
- supporting evidence
- confidence level
- known limitations

---

## Step 6 — Reliability Evaluation

Before returning recommendations, TuneGuide AI evaluates:

- explanation coverage
- ranking correctness
- duplicate recommendations
- diversity
- preference alignment
- result completeness

The system then assigns a reliability score between 0 and 100.

---

# Getting Started

## Prerequisites

- Python 3.11 or later (Python 3.14 was used during development)
- Git
- pip

---

## Installation

Clone the repository:

```bash
git clone https://github.com/<your-username>/applied-ai-system-project.git

cd applied-ai-system-project
```

Create a virtual environment.

macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows

```bash
python -m venv .venv
.venv\Scripts\activate
```

Install dependencies.

```bash
pip install -r requirements.txt
```

---

# Running the Project

Run the original demonstration application:

```bash
python3 -m src.main
```

The program loads the music catalog, scores songs against predefined user profiles, and prints ranked recommendations together with the scoring reasons.

---

# Running Reliability Experiments

To evaluate the integrated AI system:

```bash
python3 -m experiments.run_reliability_checks
```

The experiment runs several representative user profiles through the complete TuneGuide AI workflow:

- Guardrails
- Candidate Retrieval
- Recommendation Agent
- Explanation Generator
- Reliability Evaluator

Each profile produces:

- recommendations
- explanations
- reliability score
- detailed evaluation metrics

---

# Running Tests

Run the complete automated test suite.

```bash
python3 -m pytest -q
```

The current project contains more than **110 automated tests** covering every major module.

---

# Sample Interactions

## Example 1 — High-Energy Pop

### Input

```python
{
    "favorite_genre": "pop",
    "favorite_mood": "happy",
    "target_energy": 0.85,
    "likes_acoustic": False
}
```

### System Workflow

```
Input Validation

↓

Candidate Retrieval

↓

Recommendation Engine

↓

Explanation Generation

↓

Reliability Evaluation
```

### Output (Summary)

```
Top Recommendation

Sunrise City
Artist: Neon Echo

Reliability Score: 92 / 100

Explanation

Genre matches your preference.

Mood matches your preference.

Energy level closely matches your target.

High confidence recommendation.
```

---

## Example 2 — Chill Lofi

### Input

```python
{
    "favorite_genre": "lofi",
    "favorite_mood": "chill",
    "target_energy": 0.35,
    "likes_acoustic": True
}
```

### Output (Summary)

```
Top Recommendation

Night Window

Reliability Score: 88 / 100

Explanation

Strong genre match.

Acoustic preference satisfied.

Energy closely matches target.
```

---

## Example 3 — No Direct Catalog Match

### Input

```python
{
    "favorite_genre": "k-pop",
    "favorite_mood": "euphoric",
    "target_energy": 0.50,
    "likes_acoustic": False
}
```

### System Behaviour

The retriever cannot find a direct genre match.

Instead of failing, it progressively relaxes retrieval constraints while keeping recommendation generation deterministic.

### Output (Summary)

```
Reliability Score

81 / 100

Explanation

No direct genre match exists.

Recommendations are based on the closest available alternatives.

Preference alignment is lower than usual.

The recommendation process completed successfully.
```

---

# AI Workflow

The final AI workflow combines several independent modules.

```
User

↓

Guardrails

↓

Retriever

↓

Recommendation Agent

↓

Recommendation Engine

↓

Explanation Generator

↓

Reliability Evaluator

↓

Recommendation Result
```

Each module performs one clearly defined responsibility.

This separation improves:

- maintainability
- testing
- transparency
- future extensibility

---

# Experiments

Several experiments were conducted while developing TuneGuide AI.

## Experiment 1 — Scoring Modes

Different weighting strategies were evaluated.

Modes include:

- balanced
- genre_first
- mood_first
- energy_focused

Changing the weights noticeably alters recommendation ordering while preserving deterministic behaviour.

---

## Experiment 2 — Candidate Retrieval

Different retrieval constraints were evaluated.

Observations:

- strict filtering improves recommendation relevance
- overly restrictive filters may eliminate all candidates
- progressive fallback maintains system robustness

---

## Experiment 3 — Reliability Evaluation

The integrated evaluator was tested using several representative user profiles.

Profiles included:

- High-Energy Pop
- Chill Lofi
- Intense Rock
- No Catalog Match

The evaluator measured:

- duplicate recommendations
- explanation coverage
- ranking validity
- preference alignment
- diversity
- result completeness

---

## Experiment 4 — Regression Protection

Regression tests ensure that extending the project never changes the original recommendation algorithm unintentionally.

Every development phase preserved:

- recommendation ordering
- diversity penalties
- scoring formula
- explanation consistency

---

# Testing Summary

The project currently contains automated tests for:

✅ Recommendation scoring

✅ Candidate retrieval

✅ Guardrails

✅ Recommendation Agent

✅ Explanation Generator

✅ Reliability Evaluator

✅ Logging

✅ Regression protection

Together these tests provide confidence that new functionality can be added without breaking existing behaviour.

---

## Reliability Evaluation

For the complete structured evaluation results, including automated test outcomes, integrated reliability experiments, confidence metrics, and human-readable evaluation tables, see:

**[Reliability Evaluation Report](experiments/reliability_results.md)**

# Design Decisions

Several design decisions were made to prioritize transparency, modularity, and maintainability over building the most complex recommendation system.

## Preserving the Original Recommendation Engine

Instead of replacing the original Module 3 recommender, TuneGuide AI extends it through additional AI system components.

This approach demonstrates how an existing application can evolve into a larger AI system while maintaining backwards compatibility and preserving previously tested behaviour.

---

## Modular Architecture

Each component performs one well-defined responsibility.

| Module | Responsibility |
|---------|----------------|
| Guardrails | Validate and clean user inputs |
| Retriever | Retrieve candidate songs |
| Recommendation Agent | Coordinate the complete workflow |
| Recommendation Engine | Score and rank songs |
| Explainer | Generate evidence-based explanations |
| Evaluator | Measure recommendation reliability |
| Logging | Track system execution |

This separation makes the project easier to understand, test, and extend.

---

## Explainability over Complexity

Instead of using an opaque machine learning model, TuneGuide AI intentionally uses transparent scoring rules.

Every recommendation can be traced back to:

- genre similarity
- mood similarity
- energy closeness
- acoustic preference
- popularity
- instrumentalness

Users can understand exactly why a recommendation was produced.

---

## Deterministic Behaviour

The project intentionally avoids randomness.

Given the same:

- user profile
- recommendation mode
- music catalog

the system always produces the same recommendations.

Deterministic behaviour simplifies:

- testing
- debugging
- reliability evaluation

---

## Reliability Before Automation

Recommendations are not returned immediately.

Before the final result is produced, the system evaluates:

- explanation coverage
- duplicate recommendations
- ranking validity
- preference alignment
- diversity
- result completeness

This additional verification improves trust in the recommendation process.

---

## Why CSV Instead of a Vector Database?

A lightweight CSV dataset was chosen because the focus of this project is AI system design rather than large-scale infrastructure.

Using a small, deterministic dataset keeps the project:

- reproducible
- easy to understand
- suitable for experimentation
- appropriate for the project scope

The modular architecture would allow future replacement with a database or vector store without changing the overall workflow.

---

# Limitations and Risks

Although TuneGuide AI demonstrates many important AI engineering concepts, it also has several limitations.

## Small Dataset

The project currently uses a fictional catalog containing only eighteen songs.

A larger and more diverse dataset would produce more representative recommendations.

---

## Metadata-Based Recommendations

Recommendations are generated only from structured song metadata.

The system does not analyze:

- lyrics
- audio signals
- user listening history
- playlists
- artist relationships

---

## No Personal Learning

The current implementation does not permanently learn from user behaviour.

Every recommendation session begins with the supplied user profile.

Future versions could incorporate persistent preference learning.

---

## Rule-Based Recommendation Engine

The recommendation engine is intentionally rule-based rather than machine learned.

While this improves transparency, it also limits the system's ability to discover complex user preferences automatically.

---

## Fictional Dataset

The dataset was designed for educational purposes.

Real-world recommendation systems typically operate on millions of songs and continuously changing user behaviour.

---

# Reflection

Building TuneGuide AI demonstrated that creating a reliable AI application involves much more than generating recommendations.

The recommendation algorithm itself became only one part of a much larger system that required validation, retrieval, orchestration, explainability, logging, testing, and reliability evaluation. Separating these responsibilities into independent modules made the project easier to understand, maintain, and extend without breaking existing functionality.

One of the biggest lessons from this project was that building an AI application involves much more than selecting a model. Reliability, validation, explainability, testing, and modular system design all play an equally important role in creating software that users can trust. Developing TuneGuide AI reinforced that successful AI engineering is about building dependable systems around intelligent components rather than relying on the model alone.

---

# Responsible AI

The complete Responsible AI discussion is documented in:

**[model_card.md](model_card.md)**

The model card discusses:

- Responsible use of AI during development
- System limitations
- Fairness considerations
- Transparency
- Explainability
- One helpful AI suggestion
- One flawed AI suggestion
- Future improvements

---

# Future Improvements

Several enhancements could further extend TuneGuide AI.

## Natural Language Requests

Allow users to describe preferences using natural language instead of manually creating a profile.

Example:

> Recommend relaxing acoustic music for studying.

---

## User Feedback Loop

Allow users to:

- like recommendations
- dislike recommendations
- skip recommendations

and gradually improve future suggestions.

---

## Semantic Retrieval

Replace metadata filtering with vector-based semantic search using song embeddings.

---

## Larger Music Catalog

Expand the recommendation dataset to thousands of songs spanning additional genres, moods, and artists.

---

## Web Interface

Provide an interactive web application using Streamlit or another lightweight framework.

---

## External Music APIs

Integrate services such as Spotify to retrieve real song metadata and recommendations.

---

# Stretch Features

TuneGuide AI includes two stretch features beyond the core pipeline.

## Test Harness / Evaluation Script

This evaluation harness qualifies as a stretch enhancement: it goes beyond the core recommendation pipeline by adding an automated, end-to-end reliability harness that exercises the integrated system.

[experiments/run_reliability_checks.py](experiments/run_reliability_checks.py):

- runs predefined profiles automatically
- uses the integrated `RecommendationAgent` (the real workflow, not a stub)
- prints pass/fail checks for each profile
- prints reliability scores
- prints explanation coverage
- prints preference alignment
- prints artist and genre diversity
- prints result completeness
- requires no user input
- is deterministic and reproducible

It reuses the reliability report the agent already attaches, rather than duplicating evaluator logic.

- Script: [experiments/run_reliability_checks.py](experiments/run_reliability_checks.py)
- Results: [experiments/reliability_results.md](experiments/reliability_results.md)

Run it with:

```bash
python3 -m experiments.run_reliability_checks
```

**Verified results:** across **4 predefined profiles**, all **4 runs completed successfully** with reliability scores of **92, 88, 100, and 81**, and **all critical checks passed**. After the execution-trace stretch feature was added, **124 total automated tests currently pass**.

## Agentic Workflow Execution Trace

The agent records a structured, deterministic trace of its observable workflow steps — `request_received`, `validation`, `retrieval`, `recommendation`, `explanation`, `reliability_evaluation`, and `completion` — capturing execution metadata only (component names, statuses, counts, warnings, and scores). It contains no private reasoning or chain-of-thought.

- Example trace: [experiments/agent_trace_example.json](experiments/agent_trace_example.json)
- Generator: [experiments/generate_agent_trace.py](experiments/generate_agent_trace.py)

Generate it with:

```bash
python3 -m experiments.generate_agent_trace
```

## Stretch Feature: RAG Enhancement

The original retriever drew candidates from a single source: `data/songs.csv`. The RAG enhancement turns retrieval into a small multi-source system that consults the song catalog **plus two hand-authored local knowledge sources** before recommendations are generated — no external API, LLM, vector database, or internet service is used.

- [knowledge/genre_aliases.json](knowledge/genre_aliases.json) — maps informal genre spellings to canonical catalog genres (e.g. `edm` → `electronic`).
- [knowledge/listening_contexts.md](knowledge/listening_contexts.md) — maps listening contexts (studying, working out, relaxing, commuting, sleeping, party) to supported recommendation attributes.

**How retrieved knowledge changes the pipeline.** Before validation, the agent (`use_knowledge=True`, on by default) normalizes a genre alias to its canonical genre and fills *only missing* profile fields from the matched listening context. Explicit user preferences are never overwritten (conflicts are recorded as warnings), and unsupported aliases or contexts fail safely with no invented data. The normalized/enriched profile then flows through the existing validation → retrieval → scoring → explanation → reliability pipeline, and the retrieval is recorded as an observable `knowledge_retrieval` trace step plus `retrieved_knowledge` on the result.

**Verified before/after example (genre alias `edm`):**

| | Baseline (`use_knowledge=False`) | Enhanced (`use_knowledge=True`) |
|---|---|---|
| Cleaned genre | `edm` (no catalog match) | `electronic` |
| Retrieved candidates | 18 (fallback to whole catalog) | 1 (direct genre match) |
| Preference alignment | 0.3333 | 1.0 |
| Reliability score | 85 | 100 |

Links: [experiments/run_rag_comparison.py](experiments/run_rag_comparison.py) · [experiments/rag_comparison_results.md](experiments/rag_comparison_results.md)

Run it with:

```bash
python -m experiments.run_rag_comparison
```

# Stretch Feature: Fine-Tuning / Specialization

This project **does not fine-tune a neural model**. Instead, as permitted by the rubric, it specializes the system's behavior with:

- **few-shot patterns** — documented deterministic keyword rules,
- a **synthetic dataset** — [specialization/preference_examples.json](specialization/preference_examples.json) (~24 hand-authored examples),
- **deterministic preference interpretation** — a natural-language request is turned into a structured profile with no model, no randomness, and no external service.

The interpreter runs first in the agent (`natural_language_request=...`), filling **only missing** profile fields; explicit user values always take precedence. It is recorded as an observable `preference_interpretation` trace step.

**Before**

```
"I'm studying."  →  baseline (no interpreter)  →  no structured profile  →  validation fails, no recommendations
```

**After**

```
"I'm studying."  →  interpreter  →  favorite_genre = "lofi"
                                    favorite_mood  = "focused"
                                    target_energy  = 0.3
                                    likes_acoustic = true
                 →  validation passes  →  3 candidates, reliability 86, better recommendations
```

Across 8 representative requests, every baseline run failed (no structured profile) while every specialized run succeeded with reliability scores of 86–100.

Links: [specialization/preference_examples.json](specialization/preference_examples.json) · [experiments/run_specialization_comparison.py](experiments/run_specialization_comparison.py) · [experiments/specialization_results.md](experiments/specialization_results.md)

Run it with:

```bash
python -m experiments.run_specialization_comparison
```

# Repository Contents

```
README.md
model_card.md
ai_interactions.md

src/
    agent.py
    evaluator.py
    explainer.py
    guardrails.py
    logging_config.py
    recommender.py
    retriever.py
    main.py

tests/

experiments/

data/

diagrams/

assets/
```

---

# Acknowledgements

This project was developed as part of the **CodePath AI110** course.

It extends the earlier **Music Recommender Simulation** into a modular Applied AI System that demonstrates recommendation pipelines, explainability, reliability evaluation, and AI system engineering principles.

---

# License

This project is intended for educational and portfolio purposes.