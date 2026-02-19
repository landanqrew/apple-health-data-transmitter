RECORDS_DDL = """
CREATE TABLE IF NOT EXISTS records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,
    source_name TEXT NOT NULL,
    source_version TEXT,
    unit TEXT,
    value TEXT,
    device TEXT,
    creation_date TEXT,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    UNIQUE(type, source_name, start_date, end_date, value)
);

CREATE INDEX IF NOT EXISTS idx_records_type ON records(type);
CREATE INDEX IF NOT EXISTS idx_records_start_date ON records(start_date);
CREATE INDEX IF NOT EXISTS idx_records_type_start ON records(type, start_date);
"""

WORKOUTS_DDL = """
CREATE TABLE IF NOT EXISTS workouts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workout_activity_type TEXT NOT NULL,
    duration REAL,
    duration_unit TEXT,
    total_distance REAL,
    total_distance_unit TEXT,
    total_energy_burned REAL,
    total_energy_burned_unit TEXT,
    source_name TEXT NOT NULL,
    source_version TEXT,
    device TEXT,
    creation_date TEXT,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    UNIQUE(workout_activity_type, source_name, start_date, end_date)
);

CREATE INDEX IF NOT EXISTS idx_workouts_type ON workouts(workout_activity_type);
CREATE INDEX IF NOT EXISTS idx_workouts_start_date ON workouts(start_date);
"""

WORKOUT_STATISTICS_DDL = """
CREATE TABLE IF NOT EXISTS workout_statistics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workout_id INTEGER NOT NULL REFERENCES workouts(id) ON DELETE CASCADE,
    type TEXT NOT NULL,
    unit TEXT,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    average REAL,
    minimum REAL,
    maximum REAL,
    sum REAL,
    UNIQUE(workout_id, type)
);
"""

ACTIVITY_SUMMARIES_DDL = """
CREATE TABLE IF NOT EXISTS activity_summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date_components TEXT NOT NULL,
    active_energy_burned REAL,
    active_energy_burned_goal REAL,
    active_energy_burned_unit TEXT,
    apple_exercise_time REAL,
    apple_exercise_time_goal REAL,
    apple_stand_hours REAL,
    apple_stand_hours_goal REAL,
    UNIQUE(date_components)
);
"""

SYNC_METADATA_DDL = """
CREATE TABLE IF NOT EXISTS sync_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

ALL_DDL = [
    RECORDS_DDL,
    WORKOUTS_DDL,
    WORKOUT_STATISTICS_DDL,
    ACTIVITY_SUMMARIES_DDL,
    SYNC_METADATA_DDL,
]
