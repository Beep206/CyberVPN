"""Shared password validation utilities (MED-001).

Provides consistent password strength validation across admin and mobile auth.
Requirements:
- Minimum 12 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one digit
- At least one special character
- Not in common password list
"""

import re

# Top 100 most common passwords (subset of 10K list)
# Full list can be loaded from file in production
COMMON_PASSWORDS: frozenset[str] = frozenset(
    {
        "123456",
        "password",
        "12345678",
        "qwerty",
        "123456789",
        "12345",
        "1234",
        "111111",
        "1234567",
        "dragon",
        "123123",
        "baseball",
        "iloveyou",
        "trustno1",
        "sunshine",
        "master",
        "welcome",
        "shadow",
        "ashley",
        "football",
        "jesus",
        "michael",
        "ninja",
        "mustang",
        "password1",
        "password123",
        "batman",
        "letmein",
        "qwerty123",
        "login",
        "admin",
        "abc123",
        "starwars",
        "solo",
        "princess",
        "monkey",
        "654321",
        "superman",
        "qazwsx",
        "zxcvbnm",
        "passw0rd",
        "qwerty1",
        "charlie",
        "donald",
        "hello",
        "password!",
        "welcome1",
        "computer",
        "jennifer",
        "jessica",
    }
)


class PasswordValidationError(ValueError):
    """Raised when password does not meet requirements."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors))


def validate_password_strength(password: str, *, raise_on_error: bool = True) -> str | list[str]:
    """Validate password meets security requirements.

    Requirements:
    - Minimum 12 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character
    - Not in common password list

    Args:
        password: The password to validate
        raise_on_error: If True, raises ValueError; if False, returns list of errors

    Returns:
        The password if valid (when raise_on_error=True)
        List of validation errors (when raise_on_error=False)

    Raises:
        ValueError: If password doesn't meet requirements and raise_on_error=True
    """
    errors: list[str] = []

    if len(password) < 12:
        errors.append("Password must be at least 12 characters")

    if not re.search(r"[A-Z]", password):
        errors.append("Password must contain at least one uppercase letter")

    if not re.search(r"[a-z]", password):
        errors.append("Password must contain at least one lowercase letter")

    if not re.search(r"\d", password):
        errors.append("Password must contain at least one digit")

    if not re.search(r"[!@#$%^&*(),.?\":{}|<>\-_=+\[\]\\;'/`~]", password):
        errors.append("Password must contain at least one special character")

    # Check against common passwords (case-insensitive)
    if password.lower() in COMMON_PASSWORDS:
        errors.append("Password is too common, please choose a different one")

    # Additional patterns to reject
    if re.match(r"^(.)\1+$", password):
        errors.append("Password cannot consist of a single repeated character")

    if re.match(r"^(012|123|234|345|456|567|678|789|890)+$", password):
        errors.append("Password cannot be a simple numeric sequence")

    if not raise_on_error:
        return errors

    if errors:
        raise PasswordValidationError(errors)

    return password


def check_password_strength(password: str) -> tuple[bool, list[str]]:
    """Check password strength without raising exception.

    Args:
        password: The password to check

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = validate_password_strength(password, raise_on_error=False)
    if isinstance(errors, list):
        return len(errors) == 0, errors
    return True, []
