from __future__ import annotations

from typing import Protocol

from apple_health_transmitter.models import (
    ActivitySummary,
    HealthRecord,
    Workout,
)


class Destination(Protocol):
    """Interface for health data backends."""

    def initialize(self) -> None:
        """Create tables/schema. Idempotent."""
        ...

    def get_last_synced_at(self) -> str | None:
        """Return the ISO-8601 datetime string of the last sync, or None."""
        ...

    def write_records(self, records: list[HealthRecord]) -> int:
        """Write a batch of health records. Return count inserted."""
        ...

    def write_workouts(self, workouts: list[Workout]) -> int:
        """Write a batch of workouts with nested statistics. Return count inserted."""
        ...

    def write_activity_summaries(self, summaries: list[ActivitySummary]) -> int:
        """Write a batch of activity summaries. Return count inserted."""
        ...

    def set_last_synced_at(self, timestamp: str) -> None:
        """Update the sync watermark."""
        ...

    def close(self) -> None:
        """Clean up connections."""
        ...
