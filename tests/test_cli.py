from click.testing import CliRunner

from apple_health_transmitter.cli import main


def test_load_command(sample_zip_path: str, tmp_path: str) -> None:
    runner = CliRunner()
    db_path = str(tmp_path) + "/test.db" if isinstance(tmp_path, str) else str(tmp_path / "test.db")
    result = runner.invoke(main, ["load", sample_zip_path, "--db", db_path])

    assert result.exit_code == 0
    assert "Records inserted:" in result.output
    assert "Workouts inserted:" in result.output
    assert "Activity summaries inserted:" in result.output


def test_load_missing_file() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["load", "/nonexistent/file.zip"])

    assert result.exit_code != 0


def test_load_full_sync(sample_zip_path: str, tmp_path: str) -> None:
    runner = CliRunner()
    db_path = str(tmp_path) + "/test.db" if isinstance(tmp_path, str) else str(tmp_path / "test.db")

    # First load
    runner.invoke(main, ["load", sample_zip_path, "--db", db_path])

    # Full sync should re-process but not duplicate
    result = runner.invoke(main, ["load", sample_zip_path, "--db", db_path, "--full-sync"])
    assert result.exit_code == 0
