from unittest.mock import MagicMock

from worker import claim_next_job_sync


def test_claim_returns_none_and_uses_for_update_without_skip_locked():
    fake_db = MagicMock()
    fake_result = MagicMock()
    fake_result.fetchone.return_value = None
    fake_db.execute.return_value = fake_result

    job = claim_next_job_sync(fake_db)

    assert job is None
    # The claim SELECT is the first (and only) execute call when fetchone is None
    sql = fake_db.execute.call_args[0][0].text
    assert "FOR UPDATE" in sql
    assert "SKIP LOCKED" not in sql
    # Only claimable scopes should appear in the filter
    assert "project_bundle" in sql
    assert "drive_sync" in sql
