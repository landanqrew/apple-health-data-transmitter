# apple-health-data-transmitter

CLI tool for replicating Apple Health export data to a persisted data source.

## Setup

```bash
uv sync
```

## Usage

Export your health data from the Health app on your iPhone (Profile > Export All Health Data), then:

```bash
# Load into SQLite (creates health.db in current directory)
apple-health-transmitter load ~/Downloads/export.zip

# Custom database path
apple-health-transmitter load ~/Downloads/export.zip --db ~/data/health.db

# Re-running with a newer export only inserts new records (incremental sync)
apple-health-transmitter load ~/Downloads/export_feb.zip

# Full re-sync (resets watermark, reprocesses all records)
apple-health-transmitter load ~/Downloads/export.zip --full-sync
```

## Tracked Data Types

- Steps, distance, exercise time
- Heart rate, resting heart rate, HRV, VO2 max
- Sleep analysis
- Active and basal energy burned
- Workouts (with per-workout statistics)
- Daily activity summaries (rings)

## Development

```bash
uv sync --extra dev
uv run pytest
uv run ruff check src/ tests/
```

## Architecture

The destination is defined as a `Protocol` (`src/apple_health_transmitter/destination.py`), making it straightforward to add new backends (BigQuery, Supabase, etc.) without modifying existing code.
