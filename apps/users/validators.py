import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class StrongPasswordValidator:
    """
    Validates that the password meets enterprise complexity rules:
    - At least 8 characters long
    - Contains at least one uppercase letter (A-Z)
    - Contains at least one lowercase letter (a-z)
    - Contains at least one numerical digit (0-9)
    - Contains at least one special character (!@#$%^&* etc.)
    """

    def __init__(self, min_length=8):
        self.min_length = min_length

    def validate(self, password, user=None):
        if len(password) < self.min_length:
            raise ValidationError(
                _(f"Password must be at least {self.min_length} characters long."),
                code="password_too_short",
            )

        if not re.search(r"[A-Z]", password):
            raise ValidationError(
                _("Password must contain at least one uppercase letter (A-Z)."),
                code="password_no_upper",
            )

        if not re.search(r"[a-z]", password):
            raise ValidationError(
                _("Password must contain at least one lowercase letter (a-z)."),
                code="password_no_lower",
            )

        if not re.search(r"[0-9]", password):
            raise ValidationError(
                _("Password must contain at least one numeric digit (0-9)."),
                code="password_no_digit",
            )

        if not re.search(r'[!@#$%^&*(),.?":{}|<>\-_+=\[\]\\/~`]', password):
            raise ValidationError(
                _("Password must contain at least one special character (!@#$%^&* etc.)."),
                code="password_no_special",
            )

    def get_help_text(self):
        return _(
            f"Your password must contain at least {self.min_length} characters, including uppercase, lowercase, numbers, and special characters."
        )
