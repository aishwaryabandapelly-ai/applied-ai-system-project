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
    ) -> RecommendationResult:
        """Run the full recommendation workflow and return a structured result.

        The steps are: validate input, retrieve candidates from the catalog,
        then rank them with the existing ``recommend_songs``. Validation
        failures return a result with ``success=False`` rather than raising.
        """
        total_catalog_size = len(self.songs)
        self.logger.info(
            "Recommendation request received: k=%s, mode=%s, catalog_size=%d.",
            k,
            mode,
            total_catalog_size,
        )

        # Step 1: validate input. Reduce k against the catalog size if needed.
        validation = validate_input(profile, k, available_songs=total_catalog_size)
        if not validation.is_valid:
            self.logger.info(
                "Validation failed with %d error(s); returning early.",
                len(validation.errors),
            )
            return RecommendationResult(
                success=False,
                recommendations=[],
                cleaned_profile=validation.cleaned_profile,
                cleaned_k=validation.cleaned_k,
                warnings=validation.warnings,
                errors=validation.errors,
                metadata={
                    "total_catalog_size": total_catalog_size,
                    "retrieved_candidates": 0,
                    "returned_recommendations": 0,
                    "scoring_mode": mode,
                },
            )
        self.logger.info(
            "Validation succeeded with %d warning(s).", len(validation.warnings)
        )

        # Step 2: retrieve candidates using the validated profile.
        options = dict(retrieval_options or {})
        candidates = retrieve_candidates(self.songs, validation.cleaned_profile, **options)
        self.logger.info("Retrieval returned %d candidate(s).", len(candidates))

        # Step 3: rank candidates with the existing scoring pipeline.
        # No scoring/ranking/diversity logic is duplicated here.
        recommendations = recommend_songs(
            validation.cleaned_profile,
            candidates,
            k=validation.cleaned_k,
            mode=mode,
        )
        self.logger.info("Produced %d recommendation(s).", len(recommendations))

        # Step 3b: attach an evidence-based explanation per recommendation.
        # This does not alter the recommendations, their order, or their scores.
        explanations = generate_explanations(recommendations, validation.cleaned_profile)

        # Step 4: package the result.
        result = RecommendationResult(
            success=True,
            recommendations=recommendations,
            cleaned_profile=validation.cleaned_profile,
            cleaned_k=validation.cleaned_k,
            warnings=validation.warnings,
            errors=validation.errors,
            metadata={
                "total_catalog_size": total_catalog_size,
                "retrieved_candidates": len(candidates),
                "returned_recommendations": len(recommendations),
                "scoring_mode": mode,
            },
            explanations=explanations,
        )
        self.logger.info("Recommendation request complete: success=%s.", result.success)
        return result
