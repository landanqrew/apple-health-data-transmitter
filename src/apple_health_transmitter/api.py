from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from apple_health_transmitter.destinations.sqlite import SQLiteDestination
from apple_health_transmitter.models import (
    ActivitySummary,
    HealthRecord,
    Workout,
    WorkoutStatistic,
)

# ---------------------------------------------------------------------------
# Pydantic request / response models
# ---------------------------------------------------------------------------


class HealthRecordPayload(BaseModel):
    type: str
    source_name: str
    start_date: str
    end_date: str
    value: str | None = None
    unit: str | None = None
    source_version: str | None = None
    device: str | None = None
    creation_date: str | None = None


class WorkoutStatisticPayload(BaseModel):
    type: str
    start_date: str
    end_date: str
    unit: str | None = None
    average: float | None = None
    minimum: float | None = None
    maximum: float | None = None
    sum: float | None = None


class WorkoutPayload(BaseModel):
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
    statistics: list[WorkoutStatisticPayload] = []


class ActivitySummaryPayload(BaseModel):
    date_components: str
    active_energy_burned: float | None = None
    active_energy_burned_goal: float | None = None
    active_energy_burned_unit: str | None = None
    apple_exercise_time: float | None = None
    apple_exercise_time_goal: float | None = None
    apple_stand_hours: float | None = None
    apple_stand_hours_goal: float | None = None


class BatchRequest(BaseModel):
    items: list[dict[str, Any]]


class RecordsBatchRequest(BaseModel):
    items: list[HealthRecordPayload]


class WorkoutsBatchRequest(BaseModel):
    items: list[WorkoutPayload]


class ActivitySummariesBatchRequest(BaseModel):
    items: list[ActivitySummaryPayload]


class BatchResponse(BaseModel):
    inserted: int


class SyncStatusResponse(BaseModel):
    last_synced_at: str | None


class SyncStatusUpdateRequest(BaseModel):
    last_synced_at: str


# ---------------------------------------------------------------------------
# Conversion helpers
# ---------------------------------------------------------------------------


def _to_health_record(p: HealthRecordPayload) -> HealthRecord:
    return HealthRecord(
        type=p.type,
        source_name=p.source_name,
        start_date=p.start_date,
        end_date=p.end_date,
        value=p.value,
        unit=p.unit,
        source_version=p.source_version,
        device=p.device,
        creation_date=p.creation_date,
    )


def _to_workout(p: WorkoutPayload) -> Workout:
    stats = tuple(
        WorkoutStatistic(
            type=s.type,
            start_date=s.start_date,
            end_date=s.end_date,
            unit=s.unit,
            average=s.average,
            minimum=s.minimum,
            maximum=s.maximum,
            sum=s.sum,
        )
        for s in p.statistics
    )
    return Workout(
        workout_activity_type=p.workout_activity_type,
        source_name=p.source_name,
        start_date=p.start_date,
        end_date=p.end_date,
        duration=p.duration,
        duration_unit=p.duration_unit,
        total_distance=p.total_distance,
        total_distance_unit=p.total_distance_unit,
        total_energy_burned=p.total_energy_burned,
        total_energy_burned_unit=p.total_energy_burned_unit,
        source_version=p.source_version,
        device=p.device,
        creation_date=p.creation_date,
        statistics=stats,
    )


def _to_activity_summary(p: ActivitySummaryPayload) -> ActivitySummary:
    return ActivitySummary(
        date_components=p.date_components,
        active_energy_burned=p.active_energy_burned,
        active_energy_burned_goal=p.active_energy_burned_goal,
        active_energy_burned_unit=p.active_energy_burned_unit,
        apple_exercise_time=p.apple_exercise_time,
        apple_exercise_time_goal=p.apple_exercise_time_goal,
        apple_stand_hours=p.apple_stand_hours,
        apple_stand_hours_goal=p.apple_stand_hours_goal,
    )


# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

_destination: SQLiteDestination | None = None


def _get_db_path() -> str:
    return os.environ.get("HEALTH_DB_PATH", "health.db")


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[no-untyped-def]
    global _destination
    _destination = SQLiteDestination(db_path=_get_db_path())
    _destination.initialize()
    yield
    if _destination:
        _destination.close()
        _destination = None


app = FastAPI(title="Apple Health Data Transmitter API", version="0.1.0", lifespan=lifespan)


def _get_destination() -> SQLiteDestination:
    assert _destination is not None
    return _destination


# ---------------------------------------------------------------------------
# API key middleware
# ---------------------------------------------------------------------------


@app.middleware("http")
async def api_key_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
    api_key = os.environ.get("HEALTH_API_KEY")
    if api_key:
        provided = request.headers.get("X-API-Key", "")
        if provided != api_key:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or missing API key"},
            )
    response = await call_next(request)
    return response


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.post("/api/v1/records", response_model=BatchResponse)
def post_records(
    body: RecordsBatchRequest,
    dest: SQLiteDestination = Depends(_get_destination),
) -> BatchResponse:
    records = [_to_health_record(p) for p in body.items]
    inserted = dest.write_records(records)
    return BatchResponse(inserted=inserted)


@app.post("/api/v1/workouts", response_model=BatchResponse)
def post_workouts(
    body: WorkoutsBatchRequest,
    dest: SQLiteDestination = Depends(_get_destination),
) -> BatchResponse:
    workouts = [_to_workout(p) for p in body.items]
    inserted = dest.write_workouts(workouts)
    return BatchResponse(inserted=inserted)


@app.post("/api/v1/activity-summaries", response_model=BatchResponse)
def post_activity_summaries(
    body: ActivitySummariesBatchRequest,
    dest: SQLiteDestination = Depends(_get_destination),
) -> BatchResponse:
    summaries = [_to_activity_summary(p) for p in body.items]
    inserted = dest.write_activity_summaries(summaries)
    return BatchResponse(inserted=inserted)


@app.get("/api/v1/sync-status", response_model=SyncStatusResponse)
def get_sync_status(
    dest: SQLiteDestination = Depends(_get_destination),
) -> SyncStatusResponse:
    return SyncStatusResponse(last_synced_at=dest.get_last_synced_at())


@app.post("/api/v1/sync-status", response_model=SyncStatusResponse)
def update_sync_status(
    body: SyncStatusUpdateRequest,
    dest: SQLiteDestination = Depends(_get_destination),
) -> SyncStatusResponse:
    dest.set_last_synced_at(body.last_synced_at)
    return SyncStatusResponse(last_synced_at=body.last_synced_at)
