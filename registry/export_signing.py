from __future__ import annotations

import base64
import hmac
import json
import time
from dataclasses import asdict, dataclass
from hashlib import sha256
from typing import Literal


Subject = Literal["cme_document", "cme_project_intake", "cme_quality", "cme_review_history"]


class PrintTokenInvalid(Exception):
    """Token signature did not verify or payload was malformed."""


class PrintTokenExpired(Exception):
    """Token was well-formed but past its expiry."""


@dataclass(frozen=True)
class PrintTokenPayload:
    subject: Subject
    resource_id: str
    expires_at: int  # unix seconds


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def sign_print_token(payload: PrintTokenPayload, *, secret: str) -> str:
    body = _b64url_encode(json.dumps(asdict(payload), separators=(",", ":")).encode("utf-8"))
    mac = hmac.new(secret.encode("utf-8"), body.encode("ascii"), sha256).digest()
    return f"{body}.{_b64url_encode(mac)}"


def verify_print_token(token: str, *, secret: str) -> PrintTokenPayload:
    try:
        body, sig = token.split(".", 1)
    except ValueError as exc:
        raise PrintTokenInvalid("malformed token") from exc

    expected = _b64url_encode(
        hmac.new(secret.encode("utf-8"), body.encode("ascii"), sha256).digest()
    )
    if not hmac.compare_digest(expected, sig):
        raise PrintTokenInvalid("bad signature")

    try:
        raw = json.loads(_b64url_decode(body).decode("utf-8"))
        payload = PrintTokenPayload(**raw)
    except Exception as exc:
        raise PrintTokenInvalid("bad payload") from exc

    if payload.expires_at <= int(time.time()):
        raise PrintTokenExpired("token expired")
    return payload
