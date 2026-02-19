from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class HealthRecord:
    type: str
    source_name: str
    start_date: str
    end_date: str
    value: str | None = None
    unit: str | None = None
    source_version: str | None = None
    device: str | None = None
    creation_date: str | None = None


@dataclass(frozen=True, slots=True)
class WorkoutStatistic:
    type: str
    start_date: str
    end_date: str
    unit: str | None = None
    average: float | None = None
    minimum: float | None = None
    maximum: float | None = None
    sum: float | None = None


@dataclass(frozen=True, slots=True)
class Workout:
    workout_activity_type: str
    source_name: str
    start_date: str
    end_date: str
    duration: float | None = None
    duration_unit: str | None = None
    total_distance: float | None = None
    total_distance_unit: str | None = None
    total_energy_burned: float | None = None
    total_energy_burned_unit: str | None = None
    source_version: str | None = None
    device: str | None = None
    creation_date: str | None = None
    statistics: tuple[WorkoutStatistic, ...] = ()


@dataclass(frozen=True, slots=True)
class ActivitySummary:
    date_components: str
    active_energy_burned: float | None = None
    active_energy_burned_goal: float | None = None
    active_energy_burned_unit: str | None = None
    apple_exercise_time: float | None = None
    apple_exercise_time_goal: float | None = None
    apple_stand_hours: float | None = None
    apple_stand_hours_goal: float | None = None
