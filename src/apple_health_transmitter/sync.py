from __future__ import annotations

from apple_health_transmitter.destination import Destination
from apple_health_transmitter.models import ActivitySummary, HealthRecord, Workout
from apple_health_transmitter.parser import parse_export

BATCH_SIZE = 5000


def sync(zip_path: str, destination: Destination) -> dict[str, int]:
    """Run an incremental sync from an Apple Health export to a destination.

    Returns a dict of counts: {"records": N, "workouts": N, "activity_summaries": N}
    """
    destination.initialize()

    since = destination.get_last_synced_at()
    elements = parse_export(zip_path, since=since)

    counts = {"records": 0, "workouts": 0, "activity_summaries": 0}
    max_end_date: str | None = None

    record_batch: list[HealthRecord] = []
    workout_batch: list[Workout] = []
    summary_batch: list[ActivitySummary] = []

    for element in elements:
        if isinstance(element, HealthRecord):
            record_batch.append(element)
            max_end_date = _max_date(max_end_date, element.end_date)
            if len(record_batch) >= BATCH_SIZE:
                counts["records"] += destination.write_records(record_batch)
                record_batch.clear()

        elif isinstance(element, Workout):
            workout_batch.append(element)
            max_end_date = _max_date(max_end_date, element.end_date)
            if len(workout_batch) >= BATCH_SIZE:
                counts["workouts"] += destination.write_workouts(workout_batch)
                workout_batch.clear()

        elif isinstance(element, ActivitySummary):
            summary_batch.append(element)
            if len(summary_batch) >= BATCH_SIZE:
                counts["activity_summaries"] += destination.write_activity_summaries(summary_batch)
                summary_batch.clear()

    # Flush remaining
    if record_batch:
        counts["records"] += destination.write_records(record_batch)
    if workout_batch:
        counts["workouts"] += destination.write_workouts(workout_batch)
    if summary_batch:
        counts["activity_summaries"] += destination.write_activity_summaries(summary_batch)

    if max_end_date:
        destination.set_last_synced_at(max_end_date)

    return counts


def _max_date(current: str | None, candidate: str) -> str:
    if current is None:
        return candidate
    return max(current, candidate)
