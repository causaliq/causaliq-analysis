"""Unit tests for CLI"""

from click.testing import CliRunner
from pytest import fixture

from causaliq_analysis.cli import cli


@fixture
def runner():
    return CliRunner()


# Version option prints version correctly
def test_cli_version(runner):
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "version" in result.output.lower()


# Help option prints main CLI help with available commands
def test_cli_help(runner):
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "causaliq-analysis" in result.output
    assert "Commands:" in result.output
    assert "graph-average" in result.output


# Graph-average command help displays correct usage and options
def test_graph_average_help(runner):
    result = runner.invoke(cli, ["graph-average", "--help"])
    assert result.exit_code == 0
    assert "Compute edge probabilities" in result.output
    assert "--network" in result.output
    assert "--N" in result.output
    assert "--seeds" in result.output
    assert "--basis" in result.output
    assert "--output" in result.output
    assert "--series" in result.output
    assert "--root-dir" in result.output


# Graph-average command fails when required options are missing
def test_graph_average_missing_options(runner):
    result = runner.invoke(cli, ["graph-average"])
    assert result.exit_code != 0
    assert "Missing option" in result.output


# Graph-average command fails with non-existent root directory
def test_graph_average_invalid_root_dir(runner):
    result = runner.invoke(
        cli,
        [
            "graph-average",
            "--network=asia",
            "--N=10k",
            "--series=TEST/SERIES",
            "--output=test.csv",
            "--root-dir=/non/existent/path",
        ],
    )
    assert result.exit_code != 0
