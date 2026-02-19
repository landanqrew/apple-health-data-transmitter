import pytest

from apple_health_transmitter.destinations.sqlite import SQLiteDestination
from apple_health_transmitter.models import (
    ActivitySummary,
    HealthRecord,
    Workout,
    WorkoutStatistic,
)


@pytest.fixture
def dest() -> SQLiteDestination:
    d = SQLiteDestination(db_path=":memory:")
    d.initialize()
    return d


def test_initialize_creates_tables(dest: SQLiteDestination) -> None:
    assert dest._conn is not None
    cursor = dest._conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = {row[0] for row in cursor.fetchall()}
    expected = {"records", "workouts", "workout_statistics", "activity_summaries", "sync_metadata"}
    assert tables >= expected


def test_write_records(dest: SQLiteDestination) -> None:
    records = [
        HealthRecord(
            type="HKQuantityTypeIdentifierStepCount",
            source_name="iPhone",
            start_date="2025-01-15T12:00:00+00:00",
            end_date="2025-01-15T12:58:00+00:00",
            value="1234",
            unit="count",
        ),
    ]
    count = dest.write_records(records)
    assert count == 1

    assert dest._conn is not None
    cursor = dest._conn.execute("SELECT type, value FROM records")
    row = cursor.fetchone()
    assert row == ("HKQuantityTypeIdentifierStepCount", "1234")


def test_write_records_dedup(dest: SQLiteDestination) -> None:
    records = [
        HealthRecord(
            type="HKQuantityTypeIdentifierStepCount",
            source_name="iPhone",
            start_date="2025-01-15T12:00:00+00:00",
            end_date="2025-01-15T12:58:00+00:00",
            value="1234",
            unit="count",
        ),
    ]
    dest.write_records(records)
    count = dest.write_records(records)
    assert count == 0

    assert dest._conn is not None
    cursor = dest._conn.execute("SELECT COUNT(*) FROM records")
    assert cursor.fetchone()[0] == 1


def test_write_workouts_with_statistics(dest: SQLiteDestination) -> None:
    workouts = [
        Workout(
            workout_activity_type="HKWorkoutActivityTypeRunning",
            source_name="Apple Watch",
            start_date="2025-01-15T11:00:00+00:00",
            end_date="2025-01-15T11:32:30+00:00",
            duration=32.5,
            duration_unit="min",
            statistics=(
                WorkoutStatistic(
                    type="HKQuantityTypeIdentifierHeartRate",
                    start_date="2025-01-15T11:00:00+00:00",
                    end_date="2025-01-15T11:32:30+00:00",
                    average=155.0,
                    minimum=120.0,
                    maximum=182.0,
                    unit="count/min",
                ),
            ),
        ),
    ]
    count = dest.write_workouts(workouts)
    assert count == 1

    assert dest._conn is not None
    cursor = dest._conn.execute("SELECT COUNT(*) FROM workout_statistics")
    assert cursor.fetchone()[0] == 1

    cursor = dest._conn.execute("SELECT average, minimum, maximum FROM workout_statistics")
    row = cursor.fetchone()
    assert row == (155.0, 120.0, 182.0)


def test_write_activity_summaries(dest: SQLiteDestination) -> None:
    summaries = [
        ActivitySummary(
            date_components="2025-01-15",
            active_energy_burned=520.0,
            active_energy_burned_goal=600.0,
            active_energy_burned_unit="kcal",
            apple_exercise_time=35.0,
            apple_exercise_time_goal=30.0,
            apple_stand_hours=10.0,
            apple_stand_hours_goal=12.0,
        ),
    ]
    count = dest.write_activity_summaries(summaries)
    assert count == 1


def test_sync_metadata_roundtrip(dest: SQLiteDestination) -> None:
    assert dest.get_last_synced_at() is None

    dest.set_last_synced_at("2025-01-15T12:58:00+00:00")
    assert dest.get_last_synced_at() == "2025-01-15T12:58:00+00:00"

    dest.set_last_synced_at("2025-01-20T08:00:00+00:00")
    assert dest.get_last_synced_at() == "2025-01-20T08:00:00+00:00"
