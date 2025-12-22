"""Unit tests for CLI"""

from click.testing import CliRunner
from pytest import fixture

from causaliq_analysis.cli import cli


@fixture
def runner():
    return CliRunner()


# Check version printed correctly
def test_cli_version(runner):
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "version" in result.output.lower()


# check help printed correctly
def test_cli_help(runner):
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert (  # NOTE: the (cqalys) optional name absent when called this way
        "Usage: causaliq-analysis [OPTIONS] NAME" in result.output
    )
    assert "Simple CLI example." in result.output
    assert "NAME is the person to greet" in result.output
    assert "  --greet TEXT  Greeting to use" in result.output
