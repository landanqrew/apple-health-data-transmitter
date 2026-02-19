from apple_health_transmitter.destinations.sqlite import SQLiteDestination
from apple_health_transmitter.sync import sync


def test_full_sync(sample_zip_path: str) -> None:
    dest = SQLiteDestination(db_path=":memory:")
    counts = sync(sample_zip_path, dest)

    assert counts["records"] == 5  # steps x2, HR, resting HR, sleep
    assert counts["workouts"] == 1
    assert counts["activity_summaries"] == 2

    assert dest.get_last_synced_at() is not None
    dest.close()


def test_incremental_sync_inserts_nothing_on_rerun(sample_zip_path: str) -> None:
    dest = SQLiteDestination(db_path=":memory:")

    # First sync
    sync(sample_zip_path, dest)

    # Second sync with same data — should insert nothing
    counts = sync(sample_zip_path, dest)

    assert counts["records"] == 0
    assert counts["workouts"] == 0
    assert counts["activity_summaries"] == 0
    dest.close()


def test_sync_sets_watermark(sample_zip_path: str) -> None:
    dest = SQLiteDestination(db_path=":memory:")
    sync(sample_zip_path, dest)

    watermark = dest.get_last_synced_at()
    assert watermark is not None
    # The latest end_date in the fixture is 2025-01-15 (various times)
    assert "2025-01-15" in watermark
    dest.close()


def test_workout_statistics_persisted(sample_zip_path: str) -> None:
    dest = SQLiteDestination(db_path=":memory:")
    sync(sample_zip_path, dest)

    assert dest._conn is not None
    cursor = dest._conn.execute("SELECT COUNT(*) FROM workout_statistics")
    assert cursor.fetchone()[0] == 2  # HR stats + energy stats
    dest.close()
