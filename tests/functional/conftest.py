"""Shared fixtures for functional CLI tests."""

from click.testing import CliRunner
from pytest import fixture


@fixture
def cli_runner():
    """Provide a CLI runner for testing."""
    return CliRunner()
