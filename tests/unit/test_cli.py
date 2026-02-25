"""Unit tests for CLI"""

from click.testing import CliRunner
from pytest import fixture

from causaliq_analysis.cli import cli


@fixture
def runner():
    return CliRunner()


# Version option prints version correctly.
def test_cli_version(runner):
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "version" in result.output.lower()


# Help option prints main CLI help with available commands.
def test_cli_help(runner):
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "causaliq-analysis" in result.output
    assert "Commands:" in result.output
    assert "migrate_trace" in result.output


# Migrate_trace command help displays correct usage and options.
def test_migrate_trace_help(runner):
    result = runner.invoke(cli, ["migrate_trace", "--help"])
    assert result.exit_code == 0
    assert "Migrate legacy Trace pickle files" in result.output
    assert "--network" in result.output
    assert "--series" in result.output
    assert "--root-dir" in result.output


# Migrate_trace command fails when required options are missing.
def test_migrate_trace_missing_options(runner):
    result = runner.invoke(cli, ["migrate_trace"])
    assert result.exit_code != 0
    assert "Missing option" in result.output
