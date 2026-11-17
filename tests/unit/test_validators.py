"""
Unit tests for file upload security validator.
"""

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.core.validators import MAX_UPLOAD_SIZE_BYTES, validate_file_upload


@pytest.mark.unit
class TestFileUploadValidator:
    def test_valid_image_upload_passes(self):
        file = SimpleUploadedFile("receipt.jpg", b"dummy image data", content_type="image/jpeg")
        # Should not raise
        validate_file_upload(file)

    def test_valid_pdf_upload_passes(self):
        file = SimpleUploadedFile("invoice.pdf", b"%PDF-1.4 dummy pdf data", content_type="application/pdf")
        # Should not raise
        validate_file_upload(file)

    def test_disallowed_extension_fails(self):
        file = SimpleUploadedFile(
            "exploit.exe", b"malicious executable payload", content_type="application/x-msdownload"
        )
        with pytest.raises(ValidationError) as exc:
            validate_file_upload(file)
        assert "Unsupported file format" in str(exc.value)

    def test_disallowed_script_extension_fails(self):
        file = SimpleUploadedFile("webshell.php", b"<?php phpinfo(); ?>", content_type="text/plain")
        with pytest.raises(ValidationError) as exc:
            validate_file_upload(file)
        assert "Unsupported file format" in str(exc.value)

    def test_oversized_file_fails(self):
        large_size = MAX_UPLOAD_SIZE_BYTES + 1024
        file = SimpleUploadedFile("huge_receipt.png", b"0" * 100)
        file.size = large_size
        with pytest.raises(ValidationError) as exc:
            validate_file_upload(file)
        assert "exceeds the allowable limit" in str(exc.value)
