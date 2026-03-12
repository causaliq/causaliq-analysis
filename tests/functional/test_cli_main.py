"""Functional tests for main CLI entry points.

These tests verify the main CLI group and entry point work correctly.
"""

from click.testing import CliRunner

from causaliq_analysis.cli import cli


# Main CLI with no arguments shows available commands.
def test_cli_no_args_shows_commands():
    """Test CLI with no arguments shows available commands."""
    runner = CliRunner()
    result = runner.invoke(cli, [])
    # Click groups return exit code 0 or 2 depending on click version
    assert result.exit_code in (0, 2)
    assert "Commands:" in result.output
    assert "migrate-trace" in result.output


# Main function invokes CLI correctly.
def test_main_function(monkeypatch):
    """Test main() entry point invokes CLI."""
    called = {}

    def fake_cli(*args, **kwargs):
        called["cli"] = True

    monkeypatch.setattr("causaliq_analysis.cli.cli", fake_cli)
    from causaliq_analysis.cli import main

    main()
    assert called.get("cli") is True
