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
