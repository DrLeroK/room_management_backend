"""
Security validators for file uploads and data integrity.
"""

import os

from django.core.exceptions import ValidationError

ALLOWED_IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp", ".pdf"]
MAX_UPLOAD_SIZE_BYTES = 5 * 1024 * 1024  # 5 Megabytes


def validate_file_upload(file_obj, max_size_bytes=MAX_UPLOAD_SIZE_BYTES, allowed_extensions=None):
    """
    Validates uploaded file size and extension to prevent malicious uploads and DoS.
    """
    if allowed_extensions is None:
        allowed_extensions = ALLOWED_IMAGE_EXTENSIONS

    if not file_obj:
        return

    # 1. Size Validation
    if file_obj.size > max_size_bytes:
        max_mb = max_size_bytes / (1024 * 1024)
        raise ValidationError(f"File size exceeds the allowable limit of {max_mb:.1f}MB.")

    # 2. Extension Whitelist
    ext = os.path.splitext(file_obj.name)[1].lower()
    if ext not in allowed_extensions:
        allowed_str = ", ".join(allowed_extensions)
        raise ValidationError(f"Unsupported file format '{ext}'. Allowed formats: {allowed_str}")


def normalize_ethiopian_phone(phone_str: str) -> str:
    """
    Normalizes Ethiopian phone numbers to international standard +251XXXXXXXXX.
    Supports formats:
      - 09XXXXXXXX or 07XXXXXXXX (10 digits) -> +2519XXXXXXXX or +2517XXXXXXXX
      - 9XXXXXXXX or 7XXXXXXXX (9 digits) -> +2519XXXXXXXX or +2517XXXXXXXX
      - 2519XXXXXXXX or 2517XXXXXXXX (12 digits) -> +2519XXXXXXXX or +2517XXXXXXXX
      - +2519XXXXXXXX or +2517XXXXXXXX (13 digits) -> preserved as is
    """
    if not phone_str:
        return ""

    import re

    cleaned = re.sub(r"[\s\-\(\)\.]", "", str(phone_str).strip())

    if re.match(r"^0[97]\d{8}$", cleaned):
        return f"+251{cleaned[1:]}"
    if re.match(r"^[97]\d{8}$", cleaned):
        return f"+251{cleaned}"
    if re.match(r"^251[97]\d{8}$", cleaned):
        return f"+{cleaned}"
    if re.match(r"^\+251[97]\d{8}$", cleaned):
        return cleaned

    return cleaned
