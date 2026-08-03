"""
Unit tests for the input validation layer (src/guardrails.py).

Covers the happy path plus edge cases for each field: k, target_energy,
favorite_genre, favorite_mood, likes_acoustic, and missing/malformed input.
The guardrails must never raise on bad input — they report errors instead.
"""

from src.guardrails import validate_input, ValidationResult


def valid_profile(**overrides) -> dict:
    profile = {
        "favorite_genre": "pop",
        "favorite_mood": "happy",
        "target_energy": 0.7,
        "likes_acoustic": True,
    }
    profile.update(overrides)
    return profile


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

def test_valid_input_is_valid_and_cleaned():
    result = validate_input(valid_profile(), k=5, available_songs=18)

    assert isinstance(result, ValidationResult)
    assert result.is_valid
    assert result.errors == []
    assert result.cleaned_k == 5
    assert result.cleaned_profile == {
        "favorite_genre": "pop",
        "favorite_mood": "happy",
        "target_energy": 0.7,
        "likes_acoustic": True,
    }


# ---------------------------------------------------------------------------
# k
# ---------------------------------------------------------------------------

def test_k_zero_is_error():
    result = validate_input(valid_profile(), k=0)
    assert not result.is_valid
    assert any("greater than 0" in e for e in result.errors)


def test_k_negative_is_error():
    result = validate_input(valid_profile(), k=-3)
    assert not result.is_valid


def test_k_none_is_error():
    result = validate_input(valid_profile(), k=None)
    assert not result.is_valid
    assert any("k is required" in e for e in result.errors)


def test_k_non_numeric_string_is_error():
    result = validate_input(valid_profile(), k="abc")
    assert not result.is_valid


def test_k_bool_is_rejected():
    result = validate_input(valid_profile(), k=True)
    assert not result.is_valid
    assert any("boolean" in e for e in result.errors)


def test_k_whole_float_is_coerced_with_warning():
    result = validate_input(valid_profile(), k=3.0)
    assert result.is_valid
    assert result.cleaned_k == 3
    assert result.warnings


def test_k_fractional_float_is_error():
    result = validate_input(valid_profile(), k=3.5)
    assert not result.is_valid


def test_k_digit_string_is_coerced():
    result = validate_input(valid_profile(), k="4")
    assert result.is_valid
    assert result.cleaned_k == 4


def test_k_larger_than_available_is_reduced_and_valid():
    result = validate_input(valid_profile(), k=100, available_songs=18)
    assert result.is_valid
    assert result.cleaned_k == 18
    assert any("reducing k" in w for w in result.warnings)


def test_k_within_available_is_unchanged():
    result = validate_input(valid_profile(), k=5, available_songs=18)
    assert result.cleaned_k == 5
    assert not any("reducing k" in w for w in result.warnings)


# ---------------------------------------------------------------------------
# target_energy
# ---------------------------------------------------------------------------

def test_energy_above_one_is_clamped():
    result = validate_input(valid_profile(target_energy=1.5), k=5)
    assert result.is_valid
    assert result.cleaned_profile["target_energy"] == 1.0
    assert result.warnings


def test_energy_below_zero_is_clamped():
    result = validate_input(valid_profile(target_energy=-0.2), k=5)
    assert result.is_valid
    assert result.cleaned_profile["target_energy"] == 0.0


def test_energy_string_is_coerced():
    result = validate_input(valid_profile(target_energy="0.5"), k=5)
    assert result.is_valid
    assert result.cleaned_profile["target_energy"] == 0.5


def test_energy_non_numeric_is_error():
    result = validate_input(valid_profile(target_energy="loud"), k=5)
    assert not result.is_valid


def test_energy_missing_is_error():
    profile = valid_profile()
    del profile["target_energy"]
    result = validate_input(profile, k=5)
    assert not result.is_valid
    assert any("target_energy is required" in e for e in result.errors)


def test_energy_bool_is_error():
    result = validate_input(valid_profile(target_energy=True), k=5)
    assert not result.is_valid


# ---------------------------------------------------------------------------
# favorite_genre / favorite_mood
# ---------------------------------------------------------------------------

def test_genre_whitespace_is_trimmed():
    result = validate_input(valid_profile(favorite_genre="  Pop  "), k=5)
    assert result.is_valid
    assert result.cleaned_profile["favorite_genre"] == "Pop"
    assert result.warnings


def test_genre_empty_is_error():
    result = validate_input(valid_profile(favorite_genre="   "), k=5)
    assert not result.is_valid


def test_genre_missing_is_error():
    profile = valid_profile()
    del profile["favorite_genre"]
    result = validate_input(profile, k=5)
    assert not result.is_valid


def test_genre_non_string_is_error():
    result = validate_input(valid_profile(favorite_genre=123), k=5)
    assert not result.is_valid


def test_mood_whitespace_is_trimmed():
    result = validate_input(valid_profile(favorite_mood=" chill "), k=5)
    assert result.is_valid
    assert result.cleaned_profile["favorite_mood"] == "chill"


def test_mood_empty_is_error():
    result = validate_input(valid_profile(favorite_mood=""), k=5)
    assert not result.is_valid


# ---------------------------------------------------------------------------
# likes_acoustic
# ---------------------------------------------------------------------------

def test_likes_acoustic_true_string_becomes_bool():
    result = validate_input(valid_profile(likes_acoustic="true"), k=5)
    assert result.is_valid
    assert result.cleaned_profile["likes_acoustic"] is True


def test_likes_acoustic_false_string_becomes_bool():
    result = validate_input(valid_profile(likes_acoustic="No"), k=5)
    assert result.is_valid
    assert result.cleaned_profile["likes_acoustic"] is False


def test_likes_acoustic_numeric_becomes_bool():
    result = validate_input(valid_profile(likes_acoustic=1), k=5)
    assert result.is_valid
    assert result.cleaned_profile["likes_acoustic"] is True


def test_likes_acoustic_unrecognized_string_is_error():
    result = validate_input(valid_profile(likes_acoustic="maybe"), k=5)
    assert not result.is_valid


def test_likes_acoustic_missing_is_error():
    profile = valid_profile()
    del profile["likes_acoustic"]
    result = validate_input(profile, k=5)
    assert not result.is_valid


# ---------------------------------------------------------------------------
# Missing / malformed profile as a whole
# ---------------------------------------------------------------------------

def test_none_profile_produces_errors_not_crash():
    result = validate_input(None, k=5)
    assert not result.is_valid
    # All four required fields should be reported.
    assert len(result.errors) >= 4


def test_non_dict_profile_is_error():
    result = validate_input("not a dict", k=5)
    assert not result.is_valid
    assert any("profile must be a dict" in e for e in result.errors)


def test_multiple_errors_accumulate():
    result = validate_input(
        {"favorite_genre": "", "favorite_mood": "", "target_energy": "x"},
        k=-1,
    )
    assert not result.is_valid
    # empty genre, empty mood, bad energy, missing likes_acoustic, bad k.
    assert len(result.errors) >= 4


def test_empty_dict_profile_reports_all_required():
    result = validate_input({}, k=5)
    assert not result.is_valid
    assert any("favorite_genre" in e for e in result.errors)
    assert any("favorite_mood" in e for e in result.errors)
    assert any("target_energy" in e for e in result.errors)
    assert any("likes_acoustic" in e for e in result.errors)
