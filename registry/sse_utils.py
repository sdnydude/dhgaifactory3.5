"""Shared SSE formatting for streaming endpoints (talkback, logs-chat)."""
import json


def sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"
