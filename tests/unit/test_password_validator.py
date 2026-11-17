import pytest
from django.core.exceptions import ValidationError

from apps.users.validators import StrongPasswordValidator


def test_strong_password_validator_success():
    validator = StrongPasswordValidator(min_length=8)
    # Valid strong password with upper, lower, number, special char
    validator.validate("Admin@StayCraft2026!")
    validator.validate("P@ssw0rdSecure!")


def test_strong_password_validator_too_short():
    validator = StrongPasswordValidator(min_length=8)
    with pytest.raises(ValidationError) as exc:
        validator.validate("P@1a")
    assert "at least 8 characters" in str(exc.value)


def test_strong_password_validator_no_uppercase():
    validator = StrongPasswordValidator(min_length=8)
    with pytest.raises(ValidationError) as exc:
        validator.validate("password@123")
    assert "uppercase" in str(exc.value)


def test_strong_password_validator_no_lowercase():
    validator = StrongPasswordValidator(min_length=8)
    with pytest.raises(ValidationError) as exc:
        validator.validate("PASSWORD@123")
    assert "lowercase" in str(exc.value)


def test_strong_password_validator_no_number():
    validator = StrongPasswordValidator(min_length=8)
    with pytest.raises(ValidationError) as exc:
        validator.validate("Password@Special")
    assert "numeric digit" in str(exc.value)


def test_strong_password_validator_no_special():
    validator = StrongPasswordValidator(min_length=8)
    with pytest.raises(ValidationError) as exc:
        validator.validate("Password12345")
    assert "special character" in str(exc.value)
