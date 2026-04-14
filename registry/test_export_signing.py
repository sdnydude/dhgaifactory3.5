import os
import sys
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from export_signing import (
    PrintTokenPayload,
    sign_print_token,
    verify_print_token,
    PrintTokenInvalid,
    PrintTokenExpired,
)

SECRET = "a" * 64


def test_roundtrip_verifies() -> None:
    token = sign_print_token(
        PrintTokenPayload(
            subject="cme_document",
            resource_id="thread-abc",
            expires_at=int(time.time()) + 60,
        ),
        secret=SECRET,
    )
    payload = verify_print_token(token, secret=SECRET)
    assert payload.subject == "cme_document"
    assert payload.resource_id == "thread-abc"


def test_tampered_signature_rejected() -> None:
    token = sign_print_token(
        PrintTokenPayload(
            subject="cme_document",
            resource_id="thread-abc",
            expires_at=int(time.time()) + 60,
        ),
        secret=SECRET,
    )
    head, _, sig = token.rpartition(".")
    tampered = f"{head}.{'0' * len(sig)}"
    with pytest.raises(PrintTokenInvalid):
        verify_print_token(tampered, secret=SECRET)


def test_expired_rejected() -> None:
    token = sign_print_token(
        PrintTokenPayload(
            subject="cme_document",
            resource_id="thread-abc",
            expires_at=int(time.time()) - 1,
        ),
        secret=SECRET,
    )
    with pytest.raises(PrintTokenExpired):
        verify_print_token(token, secret=SECRET)


def test_wrong_secret_rejected() -> None:
    token = sign_print_token(
        PrintTokenPayload(
            subject="cme_document",
            resource_id="thread-abc",
            expires_at=int(time.time()) + 60,
        ),
        secret=SECRET,
    )
    with pytest.raises(PrintTokenInvalid):
        verify_print_token(token, secret="b" * 64)
