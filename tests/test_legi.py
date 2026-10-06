import base64
import hashlib

import pytest

from alinea.legi import check_integrity


def npm_integrity(payload: bytes) -> str:
    return "sha512-" + base64.b64encode(hashlib.sha512(payload).digest()).decode()


def test_check_integrity_accepts_matching_payload():
    check_integrity(b"code du travail", npm_integrity(b"code du travail"))


def test_check_integrity_rejects_tampered_payload():
    with pytest.raises(ValueError, match="checksum mismatch"):
        check_integrity(b"code du travail modifie", npm_integrity(b"code du travail"))
