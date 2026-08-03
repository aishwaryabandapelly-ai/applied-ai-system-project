"""
Structured execution trace for TuneGuide AI (stretch feature).

This records the agent's *observable* workflow steps and outcomes — component
names, statuses, counts, warnings, and scores. It deliberately does NOT capture
any private chain-of-thought, hidden reasoning, or narrative: only execution
metadata that could equally be reconstructed from logs.

The trace is deterministic (no timestamps, no randomness) and adds no behavior
to the pipeline — it only observes and records.

Public API:
- ``TraceStep`` / ``AgentTrace`` — plain dataclasses.
- ``make_request_id(...)`` — deterministic id from observable request metadata.
- ``count_critical_failures(report)`` — critical failures in a reliability report.
"""

import hashlib
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

# Mirrors the evaluator's critical checks; used only to report a count in the
# trace. This does not change evaluator behavior.
_CRITICAL_CHECK_NAMES = {
    "no_duplicate_songs",
    "explanation_coverage",
    "score_validity_and_order",
    "result_completeness",
}


@dataclass
class TraceStep:
    """One observable workflow step."""

    step: int
    component: str
    status: str
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentTrace:
    """An ordered record of the agent's observable workflow."""

    request_id: str
    steps: List[TraceStep] = field(default_factory=list)
    final_status: str = "pending"

    def add_step(
        self, component: str, status: str, details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Append a step; its 1-based index is assigned automatically."""
        self.steps.append(
            TraceStep(
                step=len(self.steps) + 1,
                component=component,
                status=status,
                details=details or {},
            )
        )

    def to_dict(self) -> Dict[str, Any]:
        """A JSON-serializable dict of the trace (stable key order)."""
        return {
            "request_id": self.request_id,
            "final_status": self.final_status,
            "steps": [asdict(step) for step in self.steps],
        }


def make_request_id(profile: Any, k: Any, mode: Any, catalog_size: int) -> str:
    """Deterministic request id from observable request metadata only.

    Uses no time or randomness, so the same request always yields the same id.
    Contains no data beyond the already-supplied profile metadata.
    """
    if isinstance(profile, dict):
        profile_repr = repr(sorted((str(key), str(value)) for key, value in profile.items()))
    else:
        profile_repr = repr(profile)
    canonical = f"{profile_repr}|k={k}|mode={mode}|catalog={catalog_size}"
    digest = hashlib.sha1(canonical.encode("utf-8")).hexdigest()
    return "req_" + digest[:12]


def count_critical_failures(reliability_report: Any) -> int:
    """Count failed critical checks in a reliability report (0 if none/None)."""
    if reliability_report is None:
        return 0
    checks = getattr(reliability_report, "checks", []) or []
    return sum(
        1
        for check in checks
        if getattr(check, "name", None) in _CRITICAL_CHECK_NAMES
        and not getattr(check, "passed", True)
    )
