from __future__ import annotations

import os
import sqlite3
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure HEALTH_API_KEY is not set unless a test explicitly sets it."""
    monkeypatch.delenv("HEALTH_API_KEY", raising=False)


@pytest.fixture()
def client(tmp_path: object, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Create a TestClient backed by a temporary SQLite database.

    We monkeypatch ``HEALTH_DB_PATH`` so the lifespan creates the DB in *tmp_path*.
    We also patch ``sqlite3.connect`` so the connection allows cross-thread usage
    (the FastAPI sync endpoints run in a thread-pool while the lifespan creates the
    connection on the main async thread).
    """
    db_path = str(tmp_path) + "/health_test.db"  # type: ignore[operator]
    monkeypatch.setenv("HEALTH_DB_PATH", db_path)

    _original_connect = sqlite3.connect

    def _connect_allow_threads(*args: object, **kwargs: object) -> sqlite3.Connection:
        kwargs["check_same_thread"] = False  # type: ignore[assignment]
        return _original_connect(*args, **kwargs)  # type: ignore[arg-type]

    # We need to reimport the app each time so the module-level global
    # ``_destination`` is freshly created by the lifespan for the new DB path.
    # However, since the module caches ``app`` at import time, we simply
    # patch sqlite3.connect before entering the TestClient lifespan.
    import apple_health_transmitter.api as api_mod

    with patch("sqlite3.connect", side_effect=_connect_allow_threads):
        # Reset the module-level destination so the lifespan re-creates it.
        api_mod._destination = None
        tc = TestClient(api_mod.app)
        with tc:
            yield tc


# ---------------------------------------------------------------------------
# Sample payloads
# ---------------------------------------------------------------------------

SAMPLE_RECORDS = {
    "items": [
        {
            "type": "HKQuantityTypeIdentifierStepCount",
            "source_name": "iPhone",
            "start_date": "2025-01-15T12:00:00+00:00",
            "end_date": "2025-01-15T12:58:00+00:00",
            "value": "1234",
            "unit": "count",
        },
        {
            "type": "HKQuantityTypeIdentifierHeartRate",
            "source_name": "Apple Watch",
            "start_date": "2025-01-15T13:00:00+00:00",
            "end_date": "2025-01-15T13:01:00+00:00",
            "value": "72",
            "unit": "count/min",
        },
    ]
}

SAMPLE_WORKOUTS = {
    "items": [
        {
            "workout_activity_type": "HKWorkoutActivityTypeRunning",
            "source_name": "Apple Watch",
            "start_date": "2025-01-15T11:00:00+00:00",
            "end_date": "2025-01-15T11:32:30+00:00",
            "duration": 32.5,
            "duration_unit": "min",
            "total_distance": 5.2,
            "total_distance_unit": "km",
            "total_energy_burned": 320.0,
            "total_energy_burned_unit": "kcal",
            "statistics": [
                {
                    "type": "HKQuantityTypeIdentifierHeartRate",
                    "start_date": "2025-01-15T11:00:00+00:00",
                    "end_date": "2025-01-15T11:32:30+00:00",
                    "average": 155.0,
                    "minimum": 120.0,
                    "maximum": 182.0,
                    "unit": "count/min",
                },
            ],
        }
    ]
}

SAMPLE_ACTIVITY_SUMMARIES = {
    "items": [
        {
            "date_components": "2025-01-15",
            "active_energy_burned": 520.0,
            "active_energy_burned_goal": 600.0,
            "active_energy_burned_unit": "kcal",
            "apple_exercise_time": 35.0,
            "apple_exercise_time_goal": 30.0,
            "apple_stand_hours": 10.0,
            "apple_stand_hours_goal": 12.0,
        }
    ]
}


# ---------------------------------------------------------------------------
# 1. POST /api/v1/records - insert health records
# ---------------------------------------------------------------------------


def test_post_records_inserts_and_returns_count(client: TestClient) -> None:
    response = client.post("/api/v1/records", json=SAMPLE_RECORDS)
    assert response.status_code == 200
    data = response.json()
    assert data["inserted"] == 2


# ---------------------------------------------------------------------------
# 2. POST /api/v1/records - deduplication
# ---------------------------------------------------------------------------


def test_post_records_deduplication(client: TestClient) -> None:
    # First insert
    r1 = client.post("/api/v1/records", json=SAMPLE_RECORDS)
    assert r1.status_code == 200
    assert r1.json()["inserted"] == 2

    # Second insert of same data should be deduplicated
    r2 = client.post("/api/v1/records", json=SAMPLE_RECORDS)
    assert r2.status_code == 200
    assert r2.json()["inserted"] == 0


# ---------------------------------------------------------------------------
# 3. POST /api/v1/workouts - insert workouts with statistics
# ---------------------------------------------------------------------------


def test_post_workouts_with_statistics(client: TestClient) -> None:
    response = client.post("/api/v1/workouts", json=SAMPLE_WORKOUTS)
    assert response.status_code == 200
    data = response.json()
    assert data["inserted"] == 1


# ---------------------------------------------------------------------------
# 4. POST /api/v1/activity-summaries - insert activity summaries
# ---------------------------------------------------------------------------


def test_post_activity_summaries(client: TestClient) -> None:
    response = client.post("/api/v1/activity-summaries", json=SAMPLE_ACTIVITY_SUMMARIES)
    assert response.status_code == 200
    data = response.json()
    assert data["inserted"] == 1


# ---------------------------------------------------------------------------
# 5. GET /api/v1/sync-status - returns null initially
# ---------------------------------------------------------------------------


def test_get_sync_status_initially_null(client: TestClient) -> None:
    response = client.get("/api/v1/sync-status")
    assert response.status_code == 200
    data = response.json()
    assert data["last_synced_at"] is None


# ---------------------------------------------------------------------------
# 6. POST /api/v1/sync-status - update and verify
# ---------------------------------------------------------------------------


def test_update_and_get_sync_status(client: TestClient) -> None:
    timestamp = "2025-01-20T08:00:00+00:00"

    # Update
    post_resp = client.post(
        "/api/v1/sync-status",
        json={"last_synced_at": timestamp},
    )
    assert post_resp.status_code == 200
    assert post_resp.json()["last_synced_at"] == timestamp

    # Verify via GET
    get_resp = client.get("/api/v1/sync-status")
    assert get_resp.status_code == 200
    assert get_resp.json()["last_synced_at"] == timestamp


# ---------------------------------------------------------------------------
# 7. API key auth - missing / wrong key returns 401
# ---------------------------------------------------------------------------


def test_api_key_missing_returns_401(
    tmp_path: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When HEALTH_API_KEY is set, requests without the header get 401."""
    db_path = str(tmp_path) + "/health_auth.db"  # type: ignore[operator]
    monkeypatch.setenv("HEALTH_DB_PATH", db_path)
    monkeypatch.setenv("HEALTH_API_KEY", "test-secret-key")

    _original_connect = sqlite3.connect

    def _connect_allow_threads(*args: object, **kwargs: object) -> sqlite3.Connection:
        kwargs["check_same_thread"] = False  # type: ignore[assignment]
        return _original_connect(*args, **kwargs)  # type: ignore[arg-type]

    import apple_health_transmitter.api as api_mod

    with patch("sqlite3.connect", side_effect=_connect_allow_threads):
        api_mod._destination = None
        with TestClient(api_mod.app) as tc:
            # No X-API-Key header
            r = tc.get("/api/v1/sync-status")
            assert r.status_code == 401
            assert r.json()["detail"] == "Invalid or missing API key"

            # Wrong key
            r = tc.get(
                "/api/v1/sync-status",
                headers={"X-API-Key": "wrong-key"},
            )
            assert r.status_code == 401


# ---------------------------------------------------------------------------
# 8. API key auth - correct key succeeds
# ---------------------------------------------------------------------------


def test_api_key_correct_key_succeeds(
    tmp_path: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When HEALTH_API_KEY is set and the correct key is provided, request succeeds."""
    db_path = str(tmp_path) + "/health_auth_ok.db"  # type: ignore[operator]
    monkeypatch.setenv("HEALTH_DB_PATH", db_path)
    monkeypatch.setenv("HEALTH_API_KEY", "test-secret-key")

    _original_connect = sqlite3.connect

    def _connect_allow_threads(*args: object, **kwargs: object) -> sqlite3.Connection:
        kwargs["check_same_thread"] = False  # type: ignore[assignment]
        return _original_connect(*args, **kwargs)  # type: ignore[arg-type]

    import apple_health_transmitter.api as api_mod

    with patch("sqlite3.connect", side_effect=_connect_allow_threads):
        api_mod._destination = None
        with TestClient(api_mod.app) as tc:
            r = tc.get(
                "/api/v1/sync-status",
                headers={"X-API-Key": "test-secret-key"},
            )
            assert r.status_code == 200
            assert r.json()["last_synced_at"] is None


# ---------------------------------------------------------------------------
# 9. GET /api/v1/stats - overview statistics
# ---------------------------------------------------------------------------


def test_get_stats_empty(client: TestClient) -> None:
    r = client.get("/api/v1/stats")
    assert r.status_code == 200
    data = r.json()
    assert data["record_count"] == 0
    assert data["workout_count"] == 0
    assert data["activity_summary_count"] == 0
    assert data["record_types"] == []
    assert data["workout_types"] == []


def test_get_stats_after_inserts(client: TestClient) -> None:
    client.post("/api/v1/records", json=SAMPLE_RECORDS)
    client.post("/api/v1/workouts", json=SAMPLE_WORKOUTS)
    client.post("/api/v1/activity-summaries", json=SAMPLE_ACTIVITY_SUMMARIES)

    r = client.get("/api/v1/stats")
    assert r.status_code == 200
    data = r.json()
    assert data["record_count"] == 2
    assert data["workout_count"] == 1
    assert data["activity_summary_count"] == 1
    assert set(data["record_types"]) == {
        "HKQuantityTypeIdentifierHeartRate",
        "HKQuantityTypeIdentifierStepCount",
    }
    assert data["workout_types"] == ["HKWorkoutActivityTypeRunning"]
    assert len(data["daily_records"]) == 1


# ---------------------------------------------------------------------------
# 10. GET /api/v1/records - query with filters and pagination
# ---------------------------------------------------------------------------


def test_get_records(client: TestClient) -> None:
    client.post("/api/v1/records", json=SAMPLE_RECORDS)

    # Fetch all
    r = client.get("/api/v1/records")
    assert r.status_code == 200
    assert len(r.json()) == 2

    # Filter by type
    r = client.get("/api/v1/records", params={"type": "HKQuantityTypeIdentifierStepCount"})
    rows = r.json()
    assert len(rows) == 1
    assert rows[0]["type"] == "HKQuantityTypeIdentifierStepCount"

    # Pagination
    r = client.get("/api/v1/records", params={"limit": 1, "offset": 0})
    assert len(r.json()) == 1
    r = client.get("/api/v1/records", params={"limit": 1, "offset": 1})
    assert len(r.json()) == 1
    r = client.get("/api/v1/records", params={"limit": 1, "offset": 2})
    assert len(r.json()) == 0


# ---------------------------------------------------------------------------
# 11. GET /api/v1/workouts - query with filters
# ---------------------------------------------------------------------------


def test_get_workouts(client: TestClient) -> None:
    client.post("/api/v1/workouts", json=SAMPLE_WORKOUTS)

    r = client.get("/api/v1/workouts")
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 1
    assert rows[0]["workout_activity_type"] == "HKWorkoutActivityTypeRunning"

    # Filter by type - no match
    r = client.get("/api/v1/workouts", params={"type": "HKWorkoutActivityTypeCycling"})
    assert len(r.json()) == 0


# ---------------------------------------------------------------------------
# 12. GET /api/v1/activity-summaries - query with filters
# ---------------------------------------------------------------------------


def test_get_activity_summaries(client: TestClient) -> None:
    client.post("/api/v1/activity-summaries", json=SAMPLE_ACTIVITY_SUMMARIES)

    r = client.get("/api/v1/activity-summaries")
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 1
    assert rows[0]["date_components"] == "2025-01-15"

    # Date range filter
    r = client.get("/api/v1/activity-summaries", params={"start_after": "2025-01-16"})
    assert len(r.json()) == 0

    r = client.get("/api/v1/activity-summaries", params={"start_before": "2025-01-14"})
    assert len(r.json()) == 0
