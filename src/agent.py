"""
Recommendation agent for TuneGuide AI (Phase 3).

This is the orchestration layer. It coordinates the existing, unchanged
modules — validation (guardrails), retrieval (retriever), and scoring/ranking
(recommender) — into a single workflow. It adds no scoring, ranking, retrieval,
or diversity logic of its own; it only wires the pieces together and packages
the outcome.

Public API:
- ``RecommendationResult`` — structured outcome of a recommendation request.
- ``RecommendationAgent`` — holds a catalog and exposes ``recommend(...)``.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.guardrails import validate_input
from src.retriever import retrieve_candidates
from src.recommender import recommend_songs
from src.explainer import generate_explanations
from src.evaluator import evaluate_recommendations
from src.knowledge_retriever import retrieve_knowledge, apply_knowledge_to_profile
from src.trace import AgentTrace, make_request_id, count_critical_failures
from src.logging_config import get_logger


@dataclass
class RecommendationResult:
    """Outcome of a recommendation request.

    Attributes:
        success: True when validation passed and the workflow ran.
        recommendations: the list produced by ``recommend_songs`` — tuples of
            ``(song, score, explanation)``. Empty on failure.
        cleaned_profile: the validated/cleaned profile.
        cleaned_k: the validated/adjusted number of recommendations.
        warnings: non-fatal adjustments (from validation).
        errors: fatal validation problems (empty on success).
        metadata: workflow metadata (catalog size, candidate/result counts,
            scoring mode).
    """

    success: bool
    recommendations: List[Any] = field(default_factory=list)
    cleaned_profile: Dict[str, Any] = field(default_factory=dict)
    cleaned_k: Optional[int] = None
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    # One RecommendationExplanation per entry in ``recommendations`` (same order).
    # Empty on failure. The ``recommendations`` field is unchanged for backward
    # compatibility.
    explanations: List[Any] = field(default_factory=list)
    # ReliabilityReport for a successful result; None for a failed/invalid request.
    reliability_report: Optional[Any] = None
    # AgentTrace of observable workflow steps. Present for both successful and
    # failed runs. Records execution metadata only (no private reasoning).
    trace: Optional[Any] = None
    # KnowledgeRetrievalResult from the RAG stretch feature (None when knowledge
    # retrieval is disabled or unused). Backward compatible: defaults to None.
    retrieved_knowledge: Optional[Any] = None


class RecommendationAgent:
    """Coordinates validation, retrieval, and scoring over a fixed catalog."""

    def __init__(self, songs: List[Dict[str, Any]]):
        self.songs = songs or []
        self.logger = get_logger("tuneguide.agent")

    def recommend(
        self,
        profile: Any,
        *,
        k: int = 5,
        mode: str = "balanced",
        retrieval_options: Optional[Dict[str, Any]] = None,
        context: Optional[str] = None,
        use_knowledge: bool = True,
    ) -> RecommendationResult:
        """Run the full recommendation workflow and return a structured result.

        The steps are: (optionally) retrieve custom knowledge and enrich the
        profile, validate input, retrieve candidates from the catalog, then rank
        them with the existing ``recommend_songs``. Validation failures return a
        result with ``success=False`` rather than raising.

        Knowledge retrieval (RAG stretch feature) normalizes genre aliases and
        fills *missing* profile fields from listening-context knowledge. Explicit
        user preferences are never overwritten. When ``use_knowledge`` is False
        (or no knowledge matches), behavior is identical to the prior pipeline.
        """
        total_catalog_size = len(self.songs)
        self.logger.info(
            "Recommendation request received: k=%s, mode=%s, catalog_size=%d.",
            k,
            mode,
            total_catalog_size,
        )

        # Observable execution trace (records metadata only, no reasoning).
        trace = AgentTrace(request_id=make_request_id(profile, k, mode, total_catalog_size))
        trace.add_step(
            "request_received",
            "ok",
            {
                "requested_k": k,
                "scoring_mode": mode,
                "catalog_size": total_catalog_size,
            },
        )

        # Step 0: knowledge retrieval + profile enrichment (RAG). Only records a
        # trace step and changes the profile when a knowledge source matches, so
        # a plain request behaves exactly as before.
        working_profile = profile
        retrieved_knowledge = None
        knowledge_warnings: List[str] = []
        if use_knowledge:
            genre_in = profile.get("favorite_genre") if isinstance(profile, dict) else None
            retrieved_knowledge = retrieve_knowledge(genre=genre_in, context=context)
            if retrieved_knowledge.sources_used:
                working_profile, knowledge_warnings, applied_fields = apply_knowledge_to_profile(
                    profile, retrieved_knowledge
                )
                trace.add_step(
                    "knowledge_retrieval",
                    "ok",
                    {
                        "sources_used": list(retrieved_knowledge.sources_used),
                        "normalized_genre": retrieved_knowledge.normalized_genre,
                        "inferred_context": retrieved_knowledge.inferred_context,
                        "profile_fields_filled": applied_fields,
                        "warning_count": len(knowledge_warnings),
                    },
                )

        # Knowledge metadata is surfaced on every result (empty when unused).
        knowledge_metadata = {
            "knowledge_sources_used": (
                list(retrieved_knowledge.sources_used) if retrieved_knowledge else []
            ),
            "normalized_genre": (
                retrieved_knowledge.normalized_genre if retrieved_knowledge else None
            ),
            "inferred_context": (
                retrieved_knowledge.inferred_context if retrieved_knowledge else None
            ),
        }

        # Step 1: validate input. Reduce k against the catalog size if needed.
        validation = validate_input(working_profile, k, available_songs=total_catalog_size)
        if not validation.is_valid:
            self.logger.info(
                "Validation failed with %d error(s); returning early.",
                len(validation.errors),
            )
            trace.add_step(
                "validation",
                "failed",
                {
                    "warning_count": len(validation.warnings),
                    "error_count": len(validation.errors),
                },
            )
            trace.add_step("completion", "failure", {"success": False})
            trace.final_status = "failure"
            return RecommendationResult(
                success=False,
                recommendations=[],
                cleaned_profile=validation.cleaned_profile,
                cleaned_k=validation.cleaned_k,
                warnings=knowledge_warnings + validation.warnings,
                errors=validation.errors,
                metadata={
                    "total_catalog_size": total_catalog_size,
                    "retrieved_candidates": 0,
                    "returned_recommendations": 0,
                    "scoring_mode": mode,
                    **knowledge_metadata,
                },
                trace=trace,
                retrieved_knowledge=retrieved_knowledge,
            )
        self.logger.info(
            "Validation succeeded with %d warning(s).", len(validation.warnings)
        )
        trace.add_step(
            "validation",
            "passed",
            {
                "warning_count": len(validation.warnings),
                "error_count": len(validation.errors),
            },
        )

        # Step 2: retrieve candidates using the validated profile.
        options = dict(retrieval_options or {})
        candidates = retrieve_candidates(self.songs, validation.cleaned_profile, **options)
        self.logger.info("Retrieval returned %d candidate(s).", len(candidates))
        trace.add_step(
            "retrieval",
            "ok",
            {
                "candidates_found": len(candidates),
                # The retriever does not expose fallback usage in its return
                # value, so this is recorded as null (not observable here).
                "fallback_used": None,
                "filters_used": {
                    "genre_filter": options.get("genre_filter", True),
                    "mood_filter": options.get("mood_filter", False),
                    "energy_window": options.get("energy_window", 0.25),
                    "max_candidates": options.get("max_candidates", None),
                },
            },
        )

        # Step 3: rank candidates with the existing scoring pipeline.
        # No scoring/ranking/diversity logic is duplicated here.
        recommendations = recommend_songs(
            validation.cleaned_profile,
            candidates,
            k=validation.cleaned_k,
            mode=mode,
        )
        self.logger.info("Produced %d recommendation(s).", len(recommendations))
        trace.add_step(
            "recommendation",
            "ok",
            {
                "candidates_scored": len(candidates),
                "recommendations_returned": len(recommendations),
            },
        )

        # Step 3b: attach an evidence-based explanation per recommendation.
        # This does not alter the recommendations, their order, or their scores.
        explanations = generate_explanations(recommendations, validation.cleaned_profile)
        trace.add_step(
            "explanation",
            "ok",
            {"explanations_generated": len(explanations)},
        )

        # Step 3c: evaluate reliability of the completed result (read-only).
        reliability_report = evaluate_recommendations(
            recommendations,
            explanations,
            validation.cleaned_profile,
            requested_k=validation.cleaned_k,
            retrieved_candidate_count=len(candidates),
        )
        trace.add_step(
            "reliability_evaluation",
            "passed" if reliability_report.passed else "failed",
            {
                "reliability_score": reliability_report.score,
                "passed": reliability_report.passed,
                "critical_failure_count": count_critical_failures(reliability_report),
            },
        )

        # Step 4: package the result.
        result = RecommendationResult(
            success=True,
            recommendations=recommendations,
            cleaned_profile=validation.cleaned_profile,
            cleaned_k=validation.cleaned_k,
            warnings=knowledge_warnings + validation.warnings,
            errors=validation.errors,
            metadata={
                "total_catalog_size": total_catalog_size,
                "retrieved_candidates": len(candidates),
                "returned_recommendations": len(recommendations),
                "scoring_mode": mode,
                **knowledge_metadata,
            },
            explanations=explanations,
            reliability_report=reliability_report,
            trace=trace,
            retrieved_knowledge=retrieved_knowledge,
        )
        trace.add_step("completion", "success", {"success": True})
        trace.final_status = "success"
        self.logger.info("Recommendation request complete: success=%s.", result.success)
        return result
