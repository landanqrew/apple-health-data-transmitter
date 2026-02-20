import os

import click

from apple_health_transmitter.destinations.sqlite import SQLiteDestination
from apple_health_transmitter.sync import sync


@click.group()
def main() -> None:
    """Apple Health Data Transmitter — replicate health data to a data store."""


@main.command()
@click.argument("export_zip", type=click.Path(exists=True))
@click.option(
    "--db",
    default="health.db",
    show_default=True,
    help="Path to SQLite database file.",
)
@click.option(
    "--full-sync",
    is_flag=True,
    default=False,
    help="Ignore watermark and process all records.",
)
def load(export_zip: str, db: str, full_sync: bool) -> None:
    """Load Apple Health export data into SQLite."""
    destination = SQLiteDestination(db_path=db)

    try:
        if full_sync:
            destination.initialize()
            destination.set_last_synced_at("")

        counts = sync(export_zip, destination)

        click.echo(f"Records inserted:            {counts['records']}")
        click.echo(f"Workouts inserted:           {counts['workouts']}")
        click.echo(f"Activity summaries inserted: {counts['activity_summaries']}")
    finally:
        destination.close()


@main.command()
@click.option("--host", default="0.0.0.0", show_default=True, help="Bind address.")
@click.option("--port", default=8000, show_default=True, help="Bind port.")
@click.option(
    "--db",
    default="health.db",
    show_default=True,
    help="Path to SQLite database file.",
)
def serve(host: str, port: int, db: str) -> None:
    """Start the API server to receive health data from the iOS app."""
    import uvicorn

    os.environ.setdefault("HEALTH_DB_PATH", db)
    uvicorn.run("apple_health_transmitter.api:app", host=host, port=port)
