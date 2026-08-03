"""
Input validation and guardrails for TuneGuide AI (Phase 1).

This module only *prepares and validates* input for later phases. It does not
retrieve, score, explain, or recommend anything, and it does not modify the
existing recommendation pipeline. ``recommend_songs`` continues to behave
exactly as before; a caller may choose to feed it the cleaned values produced
here, but that wiring belongs to a later phase.

Public API:
- ``ValidationResult`` — structured outcome of validation.
- ``validate_input(profile, k, available_songs=None)`` — validate a raw user
  profile and requested count, returning a ``ValidationResult``.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ValidationResult:
    """Outcome of validating a recommendation request.

    Attributes:
        cleaned_profile: profile with the four expected keys
            (``favorite_genre``, ``favorite_mood``, ``target_energy``,
            ``likes_acoustic``). A field is ``None`` if it could not be cleaned.
        cleaned_k: the validated/adjusted number of recommendations, or ``None``.
        warnings: non-fatal adjustments made (clamping, coercion, reducing k).
        errors: fatal problems that make the input unusable.
    """

    cleaned_profile: Dict[str, Any]
    cleaned_k: Optional[int]
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """True when there are no fatal errors."""
        return len(self.errors) == 0


# Accepted string spellings when coercing a value to bool.
_TRUE_STRINGS = {"true", "1", "yes", "y", "t"}
_FALSE_STRINGS = {"false", "0", "no", "n", "f"}


def _validate_k(
    raw_k: Any,
    available_songs: Optional[int],
    warnings: List[str],
    errors: List[str],
) -> Optional[int]:
    """Validate the requested number of recommendations.

    Must be a positive integer. Whole-number floats and digit strings are
    coerced (with a warning). If ``k`` exceeds ``available_songs`` it is safely
    reduced. Never raises.
    """
    if raw_k is None:
        errors.append("k is required (number of recommendations).")
        return None
    # bool is a subclass of int; reject it explicitly so True/False aren't 1/0.
    if isinstance(raw_k, bool):
        errors.append("k must be an integer, not a boolean.")
        return None

    value: Optional[int] = None
    if isinstance(raw_k, int):
        value = raw_k
    elif isinstance(raw_k, float):
        if raw_k.is_integer():
            value = int(raw_k)
            warnings.append(f"k was a float ({raw_k}); using {value}.")
        else:
            errors.append(f"k must be a whole number, got {raw_k}.")
            return None
    elif isinstance(raw_k, str):
        text = raw_k.strip()
        if text.lstrip("+").isdigit():
            value = int(text)
            warnings.append(f"k was a string ('{raw_k}'); using {value}.")
        else:
            errors.append(f"k must be an integer, got '{raw_k}'.")
            return None
    else:
        errors.append(f"k must be an integer, got type {type(raw_k).__name__}.")
        return None

    if value <= 0:
        errors.append(f"k must be greater than 0, got {value}.")
        return None

    if available_songs is not None and value > available_songs:
        warnings.append(
            f"k ({value}) exceeds available songs ({available_songs}); "
            f"reducing k to {available_songs}."
        )
        value = available_songs

    return value


def _validate_energy(
    raw: Any, warnings: List[str], errors: List[str]
) -> Optional[float]:
    """Validate ``target_energy``: numeric, clamped to [0.0, 1.0]."""
    if raw is None:
        errors.append("target_energy is required.")
        return None
    if isinstance(raw, bool):
        errors.append("target_energy must be a number, not a boolean.")
        return None

    value: Optional[float] = None
    if isinstance(raw, (int, float)):
        value = float(raw)
    elif isinstance(raw, str):
        try:
            value = float(raw.strip())
            warnings.append(f"target_energy was a string ('{raw}'); using {value}.")
        except ValueError:
            errors.append(f"target_energy must be numeric, got '{raw}'.")
            return None
    else:
        errors.append(
            f"target_energy must be numeric, got type {type(raw).__name__}."
        )
        return None

    if value < 0.0:
        warnings.append(f"target_energy {value} is below 0.0; clamping to 0.0.")
        value = 0.0
    elif value > 1.0:
        warnings.append(f"target_energy {value} is above 1.0; clamping to 1.0.")
        value = 1.0
    return value


def _validate_nonempty_string(
    raw: Any, field_name: str, warnings: List[str], errors: List[str]
) -> Optional[str]:
    """Validate a required, non-empty string; trim surrounding whitespace."""
    if raw is None:
        errors.append(f"{field_name} is required.")
        return None
    if not isinstance(raw, str):
        errors.append(
            f"{field_name} must be a string, got type {type(raw).__name__}."
        )
        return None

    trimmed = raw.strip()
    if trimmed == "":
        errors.append(f"{field_name} must not be empty.")
        return None
    if trimmed != raw:
        warnings.append(
            f"{field_name} had surrounding whitespace; trimmed to '{trimmed}'."
        )
    return trimmed


def _validate_bool(
    raw: Any, field_name: str, warnings: List[str], errors: List[str]
) -> Optional[bool]:
    """Coerce a value to bool, accepting common string/numeric spellings."""
    if raw is None:
        errors.append(f"{field_name} is required.")
        return None
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, (int, float)):
        value = bool(raw)
        warnings.append(f"{field_name} was numeric ({raw}); using {value}.")
        return value
    if isinstance(raw, str):
        text = raw.strip().lower()
        if text in _TRUE_STRINGS:
            warnings.append(f"{field_name} was a string ('{raw}'); using True.")
            return True
        if text in _FALSE_STRINGS:
            warnings.append(f"{field_name} was a string ('{raw}'); using False.")
            return False
        errors.append(f"{field_name} must be a boolean, got '{raw}'.")
        return None
    errors.append(
        f"{field_name} must be a boolean, got type {type(raw).__name__}."
    )
    return None


def validate_input(
    profile: Any, k: Any, available_songs: Optional[int] = None
) -> ValidationResult:
    """Validate a raw user profile and requested count.

    Args:
        profile: a mapping expected to contain ``favorite_genre``,
            ``favorite_mood``, ``target_energy``, and ``likes_acoustic``.
        k: the requested number of recommendations.
        available_songs: optional count of songs available, used to safely
            reduce ``k`` when it is too large.

    Returns:
        A ``ValidationResult``. Never raises for bad input; problems are
        reported as errors/warnings instead.
    """
    warnings: List[str] = []
    errors: List[str] = []

    if profile is None:
        profile = {}
    elif not isinstance(profile, dict):
        errors.append(f"profile must be a dict, got type {type(profile).__name__}.")
        profile = {}

    genre = _validate_nonempty_string(
        profile.get("favorite_genre"), "favorite_genre", warnings, errors
    )
    mood = _validate_nonempty_string(
        profile.get("favorite_mood"), "favorite_mood", warnings, errors
    )
    energy = _validate_energy(profile.get("target_energy"), warnings, errors)
    likes_acoustic = _validate_bool(
        profile.get("likes_acoustic"), "likes_acoustic", warnings, errors
    )
    cleaned_k = _validate_k(k, available_songs, warnings, errors)

    cleaned_profile = {
        "favorite_genre": genre,
        "favorite_mood": mood,
        "target_energy": energy,
        "likes_acoustic": likes_acoustic,
    }

    return ValidationResult(
        cleaned_profile=cleaned_profile,
        cleaned_k=cleaned_k,
        warnings=warnings,
        errors=errors,
    )
