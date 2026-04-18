from __future__ import annotations

import logging

from fastapi import Request

logger = logging.getLogger(__name__)


def resolve_caller(request: Request) -> str:
    api_key = request.headers.get("x-medkb-key")
    if api_key:
        return f"apikey:{api_key[:8]}"

    cf_jwt = request.headers.get("cf-access-jwt-assertion")
    if cf_jwt:
        return f"cf-jwt:{cf_jwt[:8]}"

    return "anonymous"
