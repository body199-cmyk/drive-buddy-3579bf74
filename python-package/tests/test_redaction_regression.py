"""Regression matrix for every secret shape accepted by redaction.py.

Fixtures are synthetic test strings. ZIP scanning deliberately scans generated
runtime exports, not notebooks or prose documentation: those contain examples
of patterns and are not user-generated secrets.
"""
from __future__ import annotations

import pytest
from teledrive.redaction import PLACEHOLDER, redact, scan_for_secrets

@pytest.mark.parametrize("secret", [
    "api_id=123456", "api_hash: 'a1b2c3!'", "phone=+971501234567",
    "password='s3cret!'", "code=123456", "phone_code_hash='a1b2c3!'",
    "Bearer abc.def-123", "token='abc123!xyz'", "access_token=abc123!xyz",
    "refresh_token: abc123!xyz", "Authorization: Bearer abc.def-123",
    "1" + "A" * 90, "ya29.a0AfH6SMB123456", "1//0gLongOauthToken123",
    "/tmp/account.session", "/tmp/my-token-backup.json",
    "person@example.com", "https://t.me/+AbCdEf123", "folder_id=1AbCdEfGhi",
])
def test_sensitive_shapes_are_redacted(secret):
    result = redact(secret)
    assert PLACEHOLDER in result
    assert scan_for_secrets(secret)

@pytest.mark.parametrize("safe", [
    "def verify(code: str):", "send(code=code)", "code='CODE_REQUESTED'",
    "Documentation names a file token-guide.json without a path.",
    "The markdown identifier api_hash has no assigned value.",
])
def test_safe_source_and_documentation_shapes_are_not_false_positives(safe):
    assert redact(safe) == safe
    assert scan_for_secrets(safe) == []
