"""Google Drive service account client factory.

Imports of the google-api-python-client stack are deferred into the
factory function so this module can be imported in environments that
don't yet have the packages installed (e.g. during a unit-test collect
pass on a host without the container built).
"""
from __future__ import annotations

import os

SCOPES = ["https://www.googleapis.com/auth/drive"]


def build_drive_client():
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not creds_path:
        raise RuntimeError(
            "GOOGLE_APPLICATION_CREDENTIALS not set — Drive sync unavailable"
        )
    if not os.path.exists(creds_path):
        raise RuntimeError(
            f"GOOGLE_APPLICATION_CREDENTIALS points at missing file: {creds_path}"
        )

    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    creds = service_account.Credentials.from_service_account_file(
        creds_path, scopes=SCOPES
    )
    return build("drive", "v3", credentials=creds, cache_discovery=False)
