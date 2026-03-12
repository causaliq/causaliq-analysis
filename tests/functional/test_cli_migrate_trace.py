"""Functional tests for migrate-trace CLI command.

These tests verify the migrate-trace command works correctly
using the CliRunner and mocked dependencies.
"""

from causaliq_analysis.cli import cli


# Test migrate_trace command success.
def test_migrate_trace_success(cli_runner, tmp_path, monkeypatch):
    """Test migrate_trace command succeeds with valid parameters."""
    from causaliq_analysis.migrate import MigratedGraph, MigrateTraceResult

    # Mock run_migrate_trace to return test data
    def mock_run_migrate_trace(
        partial_id, root_dir, sample_size, seeds, log_fn
    ):
        if log_fn:
            log_fn("Loading traces...")
            log_fn("Found 2 matching traces")
            log_fn("Migration complete: 2 graphs generated")
        return MigrateTraceResult(
            graphs=[
                MigratedGraph(
                    trace_id="N1000",
                    graphml='<?xml version="1.0"?><graphml></graphml>',
                    metadata={"N": 1000, "algorithm": "TABU"},
                ),
            ],
            skipped=0,
        )

    def mock_write_migrate_result(result, output_dir, log_fn):
        if log_fn:
            log_fn("Writing graphs...")
        return [f"{output_dir}/N1000.graphml"]

    monkeypatch.setattr(
        "causaliq_analysis.migrate.run_migrate_trace", mock_run_migrate_trace
    )
    monkeypatch.setattr(
        "causaliq_analysis.migrate.write_migrate_result",
        mock_write_migrate_result,
    )

    root_dir = tmp_path / "experiments"
    root_dir.mkdir()
    output_dir = tmp_path / "output"

    result = cli_runner.invoke(
        cli,
        [
            "migrate-trace",
            "--network=asia",
            "--series=TABU/STD",
            f"--root-dir={root_dir}",
            f"--output={output_dir}",
        ],
    )

    assert result.exit_code == 0
    assert "Migration complete" in result.output


# Test migrate_trace command with sample_size filter.
def test_migrate_trace_with_sample_size(cli_runner, tmp_path, monkeypatch):
    """Test migrate_trace command with --N sample size filter."""
    from causaliq_analysis.migrate import MigratedGraph, MigrateTraceResult

    def mock_run_migrate_trace(
        partial_id, root_dir, sample_size, seeds, log_fn
    ):
        # Verify sample_size was parsed correctly
        assert sample_size == 1000
        return MigrateTraceResult(
            graphs=[
                MigratedGraph(
                    trace_id="N1000",
                    graphml='<?xml version="1.0"?><graphml></graphml>',
                    metadata={"N": 1000},
                ),
            ],
            skipped=0,
        )

    def mock_write_migrate_result(result, output_dir, log_fn):
        return [f"{output_dir}/N1000.graphml"]

    monkeypatch.setattr(
        "causaliq_analysis.migrate.run_migrate_trace", mock_run_migrate_trace
    )
    monkeypatch.setattr(
        "causaliq_analysis.migrate.write_migrate_result",
        mock_write_migrate_result,
    )

    root_dir = tmp_path / "experiments"
    root_dir.mkdir()

    result = cli_runner.invoke(
        cli,
        [
            "migrate-trace",
            "--network=asia",
            "--series=TABU/STD",
            f"--root-dir={root_dir}",
            "--N=1k",  # Use sample_size parameter
        ],
    )

    assert result.exit_code == 0


# Test migrate_trace command with skipped traces.
def test_migrate_trace_with_skipped(cli_runner, tmp_path, monkeypatch):
    """Test migrate_trace shows skipped count when some traces skipped."""
    from causaliq_analysis.migrate import MigratedGraph, MigrateTraceResult

    def mock_run_migrate_trace(
        partial_id, root_dir, sample_size, seeds, log_fn
    ):
        return MigrateTraceResult(
            graphs=[
                MigratedGraph(
                    trace_id="N1000",
                    graphml='<?xml version="1.0"?><graphml></graphml>',
                    metadata={"N": 1000},
                ),
            ],
            skipped=2,
        )

    def mock_write_migrate_result(result, output_dir, log_fn):
        return [f"{output_dir}/N1000.graphml"]

    monkeypatch.setattr(
        "causaliq_analysis.migrate.run_migrate_trace", mock_run_migrate_trace
    )
    monkeypatch.setattr(
        "causaliq_analysis.migrate.write_migrate_result",
        mock_write_migrate_result,
    )

    root_dir = tmp_path / "experiments"
    root_dir.mkdir()

    result = cli_runner.invoke(
        cli,
        [
            "migrate-trace",
            "--network=asia",
            "--series=TABU/STD",
            f"--root-dir={root_dir}",
        ],
    )

    assert result.exit_code == 0
    assert "Skipped 2 traces" in result.output


# Test migrate_trace command ValueError handling.
def test_migrate_trace_value_error(cli_runner, tmp_path, monkeypatch):
    """Test migrate_trace handles ValueError from run_migrate_trace."""

    def mock_run_migrate_trace(
        partial_id, root_dir, sample_size, seeds, log_fn
    ):
        raise ValueError("No traces found for pattern")

    monkeypatch.setattr(
        "causaliq_analysis.migrate.run_migrate_trace", mock_run_migrate_trace
    )

    root_dir = tmp_path / "experiments"
    root_dir.mkdir()

    result = cli_runner.invoke(
        cli,
        [
            "migrate-trace",
            "--network=asia",
            "--series=TABU/STD",
            f"--root-dir={root_dir}",
        ],
    )

    assert result.exit_code != 0
    assert "No traces found" in result.output


# Test migrate_trace command general exception handling.
def test_migrate_trace_general_error(cli_runner, tmp_path, monkeypatch):
    """Test migrate_trace handles general exceptions."""

    def mock_run_migrate_trace(
        partial_id, root_dir, sample_size, seeds, log_fn
    ):
        raise RuntimeError("Unexpected failure")

    monkeypatch.setattr(
        "causaliq_analysis.migrate.run_migrate_trace", mock_run_migrate_trace
    )

    root_dir = tmp_path / "experiments"
    root_dir.mkdir()

    result = cli_runner.invoke(
        cli,
        [
            "migrate-trace",
            "--network=asia",
            "--series=TABU/STD",
            f"--root-dir={root_dir}",
        ],
    )

    assert result.exit_code != 0
    assert "Migration failed" in result.output
