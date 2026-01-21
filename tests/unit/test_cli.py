"""Unit tests for CLI"""

from click.testing import CliRunner
from pandas import DataFrame
from pytest import fixture

from causaliq_analysis.cli import (
    _interpret_correlation,
    _report_entropy_correlations,
    cli,
)


@fixture
def runner():
    return CliRunner()


# ============================================================================
# Tests for _interpret_correlation
# ============================================================================


def test_interpret_correlation_strong():
    """Correlation >= 0.6 and < 0.8 is 'strong'."""
    assert _interpret_correlation(0.6) == "strong"
    assert _interpret_correlation(0.79) == "strong"
    assert _interpret_correlation(-0.6) == "strong"
    assert _interpret_correlation(-0.79) == "strong"


def test_interpret_correlation_moderate():
    """Correlation >= 0.4 and < 0.6 is 'moderate'."""
    assert _interpret_correlation(0.4) == "moderate"
    assert _interpret_correlation(0.59) == "moderate"
    assert _interpret_correlation(-0.4) == "moderate"
    assert _interpret_correlation(-0.59) == "moderate"


def test_interpret_correlation_weak():
    """Correlation >= 0.2 and < 0.4 is 'weak'."""
    assert _interpret_correlation(0.2) == "weak"
    assert _interpret_correlation(0.39) == "weak"
    assert _interpret_correlation(-0.2) == "weak"
    assert _interpret_correlation(-0.39) == "weak"


def test_interpret_correlation_negligible():
    """Correlation < 0.2 is 'negligible'."""
    assert _interpret_correlation(0.0) == "negligible"
    assert _interpret_correlation(0.19) == "negligible"
    assert _interpret_correlation(-0.19) == "negligible"


# ============================================================================
# Tests for _report_entropy_correlations
# ============================================================================


def test_report_entropy_correlations_h_exist_and_exist_ok_no_variance(capsys):
    """Both h_exist and exist_ok have zero variance."""
    df = DataFrame(
        {
            "h_exist": [1.0, 1.0, 1.0],
            "exist_ok": [True, True, True],
            "h_orient": [0.5, 0.6, 0.7],
            "orient_ok": [True, False, True],
        }
    )
    _report_entropy_correlations(df)
    captured = capsys.readouterr()
    assert (
        "cannot compute (no variance in h_exist or exist_ok)" in captured.out
    )


def test_report_entropy_correlations_h_exist_no_variance(capsys):
    """Only h_exist has zero variance."""
    df = DataFrame(
        {
            "h_exist": [1.0, 1.0, 1.0],
            "exist_ok": [True, False, True],
            "h_orient": [0.5, 0.6, 0.7],
            "orient_ok": [True, False, True],
        }
    )
    _report_entropy_correlations(df)
    captured = capsys.readouterr()
    assert "cannot compute (h_exist variance = 0)" in captured.out


def test_report_entropy_correlations_exist_ok_no_variance(capsys):
    """Only exist_ok has zero variance."""
    df = DataFrame(
        {
            "h_exist": [0.5, 0.6, 0.7],
            "exist_ok": [True, True, True],
            "h_orient": [0.5, 0.6, 0.7],
            "orient_ok": [True, False, True],
        }
    )
    _report_entropy_correlations(df)
    captured = capsys.readouterr()
    assert "cannot compute (exist_ok variance= 0)" in captured.out


def test_report_entropy_correlations_h_orient_and_orient_ok_no_variance(
    capsys,
):
    """Both h_orient and orient_ok have zero variance."""
    df = DataFrame(
        {
            "h_exist": [0.5, 0.6, 0.7],
            "exist_ok": [True, False, True],
            "h_orient": [1.0, 1.0, 1.0],
            "orient_ok": [True, True, True],
        }
    )
    _report_entropy_correlations(df)
    captured = capsys.readouterr()
    assert (
        "cannot compute (no variance in h_orient or orient_ok)" in captured.out
    )


def test_report_entropy_correlations_h_orient_no_variance(capsys):
    """Only h_orient has zero variance."""
    df = DataFrame(
        {
            "h_exist": [0.5, 0.6, 0.7],
            "exist_ok": [True, False, True],
            "h_orient": [1.0, 1.0, 1.0],
            "orient_ok": [True, False, True],
        }
    )
    _report_entropy_correlations(df)
    captured = capsys.readouterr()
    assert "cannot compute (no variance in h_orient)" in captured.out


def test_report_entropy_correlations_orient_ok_no_variance(capsys):
    """Only orient_ok has zero variance."""
    df = DataFrame(
        {
            "h_exist": [0.5, 0.6, 0.7],
            "exist_ok": [True, False, True],
            "h_orient": [0.5, 0.6, 0.7],
            "orient_ok": [True, True, True],
        }
    )
    _report_entropy_correlations(df)
    captured = capsys.readouterr()
    assert "cannot compute (no variance in orient_ok)" in captured.out


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
