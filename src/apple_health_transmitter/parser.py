from __future__ import annotations

import xml.etree.ElementTree as ET
import zipfile
from collections.abc import Iterator
from typing import IO

from apple_health_transmitter.date_utils import parse_apple_date
from apple_health_transmitter.models import (
    ActivitySummary,
    HealthRecord,
    Workout,
    WorkoutStatistic,
)

TRACKED_RECORD_TYPES: frozenset[str] = frozenset(
    {
        "HKQuantityTypeIdentifierStepCount",
        "HKQuantityTypeIdentifierHeartRate",
        "HKQuantityTypeIdentifierRestingHeartRate",
        "HKQuantityTypeIdentifierHeartRateVariabilitySDNN",
        "HKQuantityTypeIdentifierVO2Max",
        "HKCategoryTypeIdentifierSleepAnalysis",
        "HKQuantityTypeIdentifierActiveEnergyBurned",
        "HKQuantityTypeIdentifierBasalEnergyBurned",
        "HKQuantityTypeIdentifierDistanceWalkingRunning",
        "HKQuantityTypeIdentifierAppleExerciseTime",
    }
)

ParsedElement = HealthRecord | Workout | ActivitySummary


def open_export_xml(zip_path: str) -> IO[bytes]:
    """Open export.xml from inside the zip without extracting to disk."""
    zf = zipfile.ZipFile(zip_path, "r")
    xml_names = [n for n in zf.namelist() if n.endswith("export.xml")]
    if not xml_names:
        raise FileNotFoundError("No export.xml found in zip")
    return zf.open(xml_names[0])


def parse_export(zip_path: str, since: str | None = None) -> Iterator[ParsedElement]:
    """Stream-parse Apple Health export.xml from a zip file.

    Yields HealthRecord, Workout, or ActivitySummary objects.
    If `since` is provided (ISO-8601 string), only yields elements
    with end_date > since (for incremental sync).
    """
    xml_file = open_export_xml(zip_path)
    context = ET.iterparse(xml_file, events=("start", "end"))

    in_workout = False
    workout_stats: list[WorkoutStatistic] = []

    for event, elem in context:
        if event == "start":
            if elem.tag == "Workout":
                in_workout = True
                workout_stats = []
            continue

        # event == "end"
        tag = elem.tag

        if tag == "WorkoutStatistics" and in_workout:
            workout_stats.append(_parse_workout_statistic(elem))
            elem.clear()

        elif tag == "Record":
            record = _parse_record(elem, since)
            elem.clear()
            if record is not None:
                yield record

        elif tag == "Workout":
            workout = _parse_workout(elem, since, tuple(workout_stats))
            in_workout = False
            workout_stats = []
            elem.clear()
            if workout is not None:
                yield workout

        elif tag == "ActivitySummary":
            summary = _parse_activity_summary(elem, since)
            elem.clear()
            if summary is not None:
                yield summary

        else:
            if not in_workout:
                elem.clear()

    xml_file.close()


def _parse_record(elem: ET.Element, since: str | None) -> HealthRecord | None:
    attrib = elem.attrib
    record_type = attrib.get("type", "")

    if record_type not in TRACKED_RECORD_TYPES:
        return None

    end_date = parse_apple_date(attrib["endDate"])
    if since and end_date <= since:
        return None

    creation_date_raw = attrib.get("creationDate")
    creation_date = parse_apple_date(creation_date_raw) if creation_date_raw else None

    return HealthRecord(
        type=record_type,
        source_name=attrib["sourceName"],
        start_date=parse_apple_date(attrib["startDate"]),
        end_date=end_date,
        value=attrib.get("value"),
        unit=attrib.get("unit"),
        source_version=attrib.get("sourceVersion"),
        device=attrib.get("device"),
        creation_date=creation_date,
    )


def _parse_workout(
    elem: ET.Element, since: str | None, statistics: tuple[WorkoutStatistic, ...]
) -> Workout | None:
    attrib = elem.attrib
    end_date = parse_apple_date(attrib["endDate"])

    if since and end_date <= since:
        return None

    creation_date_raw = attrib.get("creationDate")
    creation_date = parse_apple_date(creation_date_raw) if creation_date_raw else None

    return Workout(
        workout_activity_type=attrib["workoutActivityType"],
        source_name=attrib["sourceName"],
        start_date=parse_apple_date(attrib["startDate"]),
        end_date=end_date,
        duration=_safe_float(attrib.get("duration")),
        duration_unit=attrib.get("durationUnit"),
        total_distance=_safe_float(attrib.get("totalDistance")),
        total_distance_unit=attrib.get("totalDistanceUnit"),
        total_energy_burned=_safe_float(attrib.get("totalEnergyBurned")),
        total_energy_burned_unit=attrib.get("totalEnergyBurnedUnit"),
        source_version=attrib.get("sourceVersion"),
        device=attrib.get("device"),
        creation_date=creation_date,
        statistics=statistics,
    )


def _parse_workout_statistic(elem: ET.Element) -> WorkoutStatistic:
    attrib = elem.attrib
    return WorkoutStatistic(
        type=attrib["type"],
        start_date=parse_apple_date(attrib["startDate"]),
        end_date=parse_apple_date(attrib["endDate"]),
        unit=attrib.get("unit"),
        average=_safe_float(attrib.get("average")),
        minimum=_safe_float(attrib.get("minimum")),
        maximum=_safe_float(attrib.get("maximum")),
        sum=_safe_float(attrib.get("sum")),
    )


def _parse_activity_summary(elem: ET.Element, since: str | None) -> ActivitySummary | None:
    attrib = elem.attrib
    date_components = attrib.get("dateComponents", "")

    if not date_components:
        return None

    if since and date_components < since[:10]:
        return None

    return ActivitySummary(
        date_components=date_components,
        active_energy_burned=_safe_float(attrib.get("activeEnergyBurned")),
        active_energy_burned_goal=_safe_float(attrib.get("activeEnergyBurnedGoal")),
        active_energy_burned_unit=attrib.get("activeEnergyBurnedUnit"),
        apple_exercise_time=_safe_float(attrib.get("appleExerciseTime")),
        apple_exercise_time_goal=_safe_float(attrib.get("appleExerciseTimeGoal")),
        apple_stand_hours=_safe_float(attrib.get("appleStandHours")),
        apple_stand_hours_goal=_safe_float(attrib.get("appleStandHoursGoal")),
    )


def _safe_float(val: str | None) -> float | None:
    if val is None:
        return None
    try:
        return float(val)
    except ValueError:
        return None
