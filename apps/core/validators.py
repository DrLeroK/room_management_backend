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
