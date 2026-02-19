from apple_health_transmitter.models import ActivitySummary, HealthRecord, Workout
from apple_health_transmitter.parser import parse_export


def test_parse_yields_tracked_records(sample_zip_path: str) -> None:
    elements = list(parse_export(sample_zip_path))
    records = [e for e in elements if isinstance(e, HealthRecord)]

    # 4 tracked records (steps x2, heart rate, resting HR, sleep) — body mass is filtered out
    assert len(records) == 5
    types = {r.type for r in records}
    assert "HKQuantityTypeIdentifierBodyMass" not in types
    assert "HKQuantityTypeIdentifierStepCount" in types
    assert "HKQuantityTypeIdentifierHeartRate" in types
    assert "HKQuantityTypeIdentifierRestingHeartRate" in types
    assert "HKCategoryTypeIdentifierSleepAnalysis" in types


def test_parse_yields_workouts(sample_zip_path: str) -> None:
    elements = list(parse_export(sample_zip_path))
    workouts = [e for e in elements if isinstance(e, Workout)]

    assert len(workouts) == 1
    w = workouts[0]
    assert w.workout_activity_type == "HKWorkoutActivityTypeRunning"
    assert w.duration == 32.5
    assert w.total_distance == 5.2
    assert len(w.statistics) == 2


def test_parse_workout_statistics(sample_zip_path: str) -> None:
    elements = list(parse_export(sample_zip_path))
    workouts = [e for e in elements if isinstance(e, Workout)]
    stats = workouts[0].statistics

    hr_stat = next(s for s in stats if s.type == "HKQuantityTypeIdentifierHeartRate")
    assert hr_stat.average == 155.0
    assert hr_stat.minimum == 120.0
    assert hr_stat.maximum == 182.0

    energy_stat = next(s for s in stats if s.type == "HKQuantityTypeIdentifierActiveEnergyBurned")
    assert energy_stat.sum == 320.0


def test_parse_yields_activity_summaries(sample_zip_path: str) -> None:
    elements = list(parse_export(sample_zip_path))
    summaries = [e for e in elements if isinstance(e, ActivitySummary)]

    assert len(summaries) == 2
    dates = {s.date_components for s in summaries}
    assert dates == {"2025-01-14", "2025-01-15"}


def test_parse_since_filters_old_records(sample_zip_path: str) -> None:
    # The older step count record has endDate 2025-01-10 07:58:00 -0500 = 2025-01-10T12:58:00+00:00
    # Setting since to after that should exclude it
    since = "2025-01-14T00:00:00+00:00"
    elements = list(parse_export(sample_zip_path, since=since))
    records = [e for e in elements if isinstance(e, HealthRecord)]

    # The Jan 10 step record should be excluded
    for r in records:
        assert r.start_date >= since or r.end_date > since


def test_parse_since_filters_activity_summaries(sample_zip_path: str) -> None:
    since = "2025-01-15T00:00:00+00:00"
    elements = list(parse_export(sample_zip_path, since=since))
    summaries = [e for e in elements if isinstance(e, ActivitySummary)]

    # Only 2025-01-15 should remain (2025-01-14 <= since[:10])
    assert len(summaries) == 1
    assert summaries[0].date_components == "2025-01-15"


def test_parse_sleep_record_value(sample_zip_path: str) -> None:
    elements = list(parse_export(sample_zip_path))
    records = [e for e in elements if isinstance(e, HealthRecord)]
    sleep = [r for r in records if r.type == "HKCategoryTypeIdentifierSleepAnalysis"]

    assert len(sleep) == 1
    assert sleep[0].value == "HKCategoryValueSleepAnalysisAsleepCore"
