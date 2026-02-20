from __future__ import annotations

import sqlite3

from apple_health_transmitter.models import ActivitySummary, HealthRecord, Workout
from apple_health_transmitter.schema import ALL_DDL


class SQLiteDestination:
    """SQLite implementation of the Destination protocol."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._conn: sqlite3.Connection | None = None

    def initialize(self) -> None:
        if self._conn is None:
            self._conn = sqlite3.connect(self._db_path)
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
        for ddl in ALL_DDL:
            self._conn.executescript(ddl)

    def get_last_synced_at(self) -> str | None:
        assert self._conn is not None
        cursor = self._conn.execute(
            "SELECT value FROM sync_metadata WHERE key = ?",
            ("last_synced_at",),
        )
        row = cursor.fetchone()
        return row[0] if row else None

    def write_records(self, records: list[HealthRecord]) -> int:
        assert self._conn is not None
        before = self._conn.total_changes
        self._conn.executemany(
            """INSERT OR IGNORE INTO records
               (type, source_name, source_version, unit, value, device,
                creation_date, start_date, end_date)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                (
                    r.type,
                    r.source_name,
                    r.source_version,
                    r.unit,
                    r.value,
                    r.device,
                    r.creation_date,
                    r.start_date,
                    r.end_date,
                )
                for r in records
            ],
        )
        self._conn.commit()
        return self._conn.total_changes - before

    def write_workouts(self, workouts: list[Workout]) -> int:
        assert self._conn is not None
        count = 0
        for w in workouts:
            before = self._conn.total_changes
            self._conn.execute(
                """INSERT OR IGNORE INTO workouts
                   (workout_activity_type, duration, duration_unit,
                    total_distance, total_distance_unit,
                    total_energy_burned, total_energy_burned_unit,
                    source_name, source_version, device,
                    creation_date, start_date, end_date)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    w.workout_activity_type,
                    w.duration,
                    w.duration_unit,
                    w.total_distance,
                    w.total_distance_unit,
                    w.total_energy_burned,
                    w.total_energy_burned_unit,
                    w.source_name,
                    w.source_version,
                    w.device,
                    w.creation_date,
                    w.start_date,
                    w.end_date,
                ),
            )
            inserted = self._conn.total_changes - before
            if inserted > 0:
                count += 1
                workout_id = self._conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                for stat in w.statistics:
                    self._conn.execute(
                        """INSERT OR IGNORE INTO workout_statistics
                           (workout_id, type, unit, start_date, end_date,
                            average, minimum, maximum, sum)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            workout_id,
                            stat.type,
                            stat.unit,
                            stat.start_date,
                            stat.end_date,
                            stat.average,
                            stat.minimum,
                            stat.maximum,
                            stat.sum,
                        ),
                    )
        self._conn.commit()
        return count

    def write_activity_summaries(self, summaries: list[ActivitySummary]) -> int:
        assert self._conn is not None
        before = self._conn.total_changes
        self._conn.executemany(
            """INSERT OR IGNORE INTO activity_summaries
               (date_components, active_energy_burned, active_energy_burned_goal,
                active_energy_burned_unit, apple_exercise_time,
                apple_exercise_time_goal, apple_stand_hours,
                apple_stand_hours_goal)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                (
                    s.date_components,
                    s.active_energy_burned,
                    s.active_energy_burned_goal,
                    s.active_energy_burned_unit,
                    s.apple_exercise_time,
                    s.apple_exercise_time_goal,
                    s.apple_stand_hours,
                    s.apple_stand_hours_goal,
                )
                for s in summaries
            ],
        )
        self._conn.commit()
        return self._conn.total_changes - before

    def set_last_synced_at(self, timestamp: str) -> None:
        assert self._conn is not None
        self._conn.execute(
            """INSERT INTO sync_metadata (key, value)
               VALUES ('last_synced_at', ?)
               ON CONFLICT(key) DO UPDATE SET value = excluded.value""",
            (timestamp,),
        )
        self._conn.commit()

    # ------------------------------------------------------------------
    # Query helpers (used by the dashboard / GET endpoints)
    # ------------------------------------------------------------------

    def _row_factory(self) -> None:
        """Enable dict-like rows on the connection."""
        assert self._conn is not None
        self._conn.row_factory = sqlite3.Row

    def query_records(
        self,
        *,
        record_type: str | None = None,
        start_after: str | None = None,
        start_before: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        assert self._conn is not None
        self._row_factory()
        clauses: list[str] = []
        params: list[str | int] = []
        if record_type:
            clauses.append("type = ?")
            params.append(record_type)
        if start_after:
            clauses.append("start_date >= ?")
            params.append(start_after)
        if start_before:
            clauses.append("start_date <= ?")
            params.append(start_before)
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = f"SELECT * FROM records{where} ORDER BY start_date DESC LIMIT ? OFFSET ?"
        params += [limit, offset]
        rows = self._conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def query_workouts(
        self,
        *,
        activity_type: str | None = None,
        start_after: str | None = None,
        start_before: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        assert self._conn is not None
        self._row_factory()
        clauses: list[str] = []
        params: list[str | int] = []
        if activity_type:
            clauses.append("workout_activity_type = ?")
            params.append(activity_type)
        if start_after:
            clauses.append("start_date >= ?")
            params.append(start_after)
        if start_before:
            clauses.append("start_date <= ?")
            params.append(start_before)
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = f"SELECT * FROM workouts{where} ORDER BY start_date DESC LIMIT ? OFFSET ?"
        params += [limit, offset]
        rows = self._conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def query_activity_summaries(
        self,
        *,
        start_after: str | None = None,
        start_before: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        assert self._conn is not None
        self._row_factory()
        clauses: list[str] = []
        params: list[str | int] = []
        if start_after:
            clauses.append("date_components >= ?")
            params.append(start_after)
        if start_before:
            clauses.append("date_components <= ?")
            params.append(start_before)
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = f"SELECT * FROM activity_summaries{where} ORDER BY date_components DESC LIMIT ? OFFSET ?"
        params += [limit, offset]
        rows = self._conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def query_stats(self) -> dict:
        """Return aggregate counts and distinct types for the dashboard overview."""
        assert self._conn is not None
        self._row_factory()

        record_count = self._conn.execute("SELECT COUNT(*) AS cnt FROM records").fetchone()["cnt"]
        workout_count = self._conn.execute("SELECT COUNT(*) AS cnt FROM workouts").fetchone()["cnt"]
        summary_count = self._conn.execute("SELECT COUNT(*) AS cnt FROM activity_summaries").fetchone()["cnt"]

        record_types = [
            r["type"]
            for r in self._conn.execute(
                "SELECT DISTINCT type FROM records ORDER BY type"
            ).fetchall()
        ]
        workout_types = [
            r["workout_activity_type"]
            for r in self._conn.execute(
                "SELECT DISTINCT workout_activity_type FROM workouts ORDER BY workout_activity_type"
            ).fetchall()
        ]

        # daily record counts for chart (last 30 days with data)
        daily_records = [
            dict(r)
            for r in self._conn.execute(
                """SELECT date(start_date) AS day, COUNT(*) AS cnt
                   FROM records
                   GROUP BY day ORDER BY day DESC LIMIT 30"""
            ).fetchall()
        ]

        return {
            "record_count": record_count,
            "workout_count": workout_count,
            "activity_summary_count": summary_count,
            "record_types": record_types,
            "workout_types": workout_types,
            "daily_records": daily_records,
            "last_synced_at": self.get_last_synced_at(),
        }

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None
