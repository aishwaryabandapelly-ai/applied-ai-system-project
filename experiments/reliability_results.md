# TuneGuide AI Reliability Evaluation

## Evaluation Summary

- **114 automated tests passed.**
- **0 automated tests failed.**
- The integrated reliability experiment evaluated **four profiles**.
- **All four** recommendation runs completed successfully.
- **All four** overall reliability reports passed their critical checks.
- The lowest-performing case was the **no-direct-catalog-match** profile, because preference alignment was low after the retriever fell back to relaxed constraints.

114 out of 114 automated tests passed. Four out of four integrated recommendation runs completed successfully and passed all critical reliability checks. Reliability scores ranged from 81 to 100. The system performed best when the catalog contained a direct genre and mood match, and scored lower when retrieval had to fall back because the requested genre was unavailable.

*Results reproduced from `python3 -m experiments.run_reliability_checks` and the full `pytest` suite.*

## Automated Test Results

| Test Area | What Was Tested | Result |
|-----------|-----------------|--------|
| Original recommendation pipeline | Scoring weights, `score_song`, `recommend_songs`, diversity penalty, CSV loading, and CLI-facing ranking remain unchanged | Pass |
| Logging | Reusable logger returns a logger, avoids duplicate handlers, and tolerates an existing log directory | Pass |
| Input guardrails | Validation and safe handling of `k`, `target_energy`, `favorite_genre`, `favorite_mood`, `likes_acoustic`, and missing/malformed input | Pass |
| Candidate retrieval | Genre/mood/energy filters, combined filters, fallback relaxation, candidate limits, empty catalog, determinism, and order preservation | Pass |
| Recommendation agent | Orchestration of validation → retrieval → scoring, metadata population, and safe handling of invalid requests | Pass |
| Explanation generator | Evidence extraction, deterministic confidence, list/string reason formats, malformed input, and one-to-one explanation coverage | Pass |
| Reliability evaluator | Duplicate detection, explanation coverage, score validity/order, preference alignment, diversity metrics, completeness, and deterministic scoring | Pass |

- **Total tests: 114**
- **Passed: 114**
- **Failed: 0**

## Integrated Reliability Experiments

| Test Profile | Requested Preference | Reliability Score | Overall Result | Main Observation |
|--------------|----------------------|-------------------|----------------|------------------|
| High-Energy Pop | pop / happy / energy 0.85 / non-acoustic | 92 | Pass | Full explanation coverage and valid ranking; moderate genre diversity |
| Chill Lofi | lofi / chill / energy 0.35 / acoustic | 88 | Pass | Strong preference alignment; diversity reduced because several retrieved songs shared a genre or artist |
| Intense Rock | rock / intense / high energy | 100 | Pass | Direct catalog match with full alignment, valid ranking, and complete diversity for the single returned result |
| No Catalog Match | k-pop / euphoric / energy 0.50 / non-acoustic | 81 | Pass | Retriever safely relaxed constraints and returned alternatives; preference alignment was low because the catalog contained no k-pop songs |

## Reliability Metrics

| Metric | What It Checks | Criticality |
|--------|----------------|-------------|
| Duplicate detection | No song appears more than once in the final list, identified by stable id (falling back to title + artist) | Critical |
| Explanation coverage | Every returned recommendation has a corresponding valid explanation | Critical |
| Score validity and order | Scores are numeric, finite, and in non-increasing (descending) order | Critical |
| Result completeness | Returned count does not exceed the requested `k` or the number of retrieved candidates, and empty results are handled safely | Critical |
| Preference alignment | Average match across genre, mood, and energy-closeness signals for the returned songs | Non-critical (reduces score) |
| Artist diversity | Unique-artist ratio and repeated-artist count across the returned list | Non-critical (reduces score) |
| Genre diversity | Unique-genre ratio and repeated-genre count across the returned list | Non-critical (reduces score) |

Critical checks gate the overall Pass/Fail result. Non-critical metrics lower the reliability score without failing the report, so weak cases stay visible.

## Human-Readable Evaluation Table

| Test Input | Evaluation Criteria | Result |
|------------|---------------------|--------|
| Valid high-energy pop profile | Runs end-to-end; passes all critical checks | Pass |
| Valid chill lofi profile | Runs end-to-end; passes all critical checks | Pass |
| Valid intense rock profile | Runs end-to-end; passes all critical checks | Pass |
| Unsupported k-pop profile | Retriever falls back safely; result still passes critical checks; low alignment surfaced | Pass — low preference alignment flagged (non-critical) |
| Invalid k value (e.g. 0 or negative) | Guardrails reject it; agent returns a failure result without crashing | Pass — evaluator/guardrails flag the issue |
| Out-of-range target energy | Guardrails clamp the value into [0.0, 1.0] and continue | Pass — value clamped safely |
| Empty catalog | No candidates; empty result handled without crashing | Pass — handled safely |
| Repeated artist or genre | Diversity metrics record the repeats and reduce the score | Pass — evaluator flags the issue (non-critical) |
| Missing explanation | Explanation coverage falls below full; report fails the coverage check | Pass — evaluator flags the issue |
| Duplicate recommendation | Duplicate detected by stable identity; report fails the duplicate check | Pass — evaluator flags the issue |

All rows reflect verified test or experiment behavior. No input produced a crash; conditions marked "evaluator flags the issue" are intentional detections, not failures of the system.

## What Worked

- Guardrails prevented invalid input from crashing the pipeline.
- Retrieval fallback prevented empty results when the catalog had no direct match.
- Explanation coverage was complete in all four integrated runs.
- Scores remained numeric, finite, and correctly ordered.
- Reliability evaluation was integrated into the agent rather than run as a separate disconnected script.

## What Did Not Work as Well

- Preference alignment dropped significantly when the requested genre was absent (0.13 for the k-pop profile).
- Small dataset size limited recommendation diversity.
- Single-result profiles can receive perfect diversity scores even though the sample is too small to prove broad diversity (Intense Rock returned one song).
- The system does not yet learn from user feedback.

## What Improved the System

- Input validation improved error handling by rejecting or repairing bad input before it reached the pipeline.
- Retrieval fallback improved robustness by guaranteeing non-empty results whenever the catalog is non-empty.
- Structured explanations improved transparency by tying each recommendation to concrete attributes and scores.
- Reliability scoring made weak cases visible instead of hiding them.
- Regression tests protected the original recommender during extension.

## Conclusion

Across the evaluated scenarios, TuneGuide AI passed all critical reliability checks, with reliability scores ranging from 81 to 100 and every recommendation run completing successfully. The no-catalog-match case revealed the main limitation: when the dataset lacks the requested category, retrieval falls back safely but relevance drops, producing low preference alignment even though the result remains structurally sound.
