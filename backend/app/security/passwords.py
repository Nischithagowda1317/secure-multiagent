from __future__ import annotations

import base64
import hashlib
import hmac


def verify_pbkdf2_sha256(password: str, encoded: str) -> bool:
    """Verify the synthetic dataset's Django-style PBKDF2-SHA256 hash."""
    try:
        algorithm, iterations_text, salt_b64, digest_b64 = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        iterations = int(iterations_text)
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(digest_b64)
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, iterations, dklen=len(expected)
        )
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError, base64.binascii.Error):
        return False
