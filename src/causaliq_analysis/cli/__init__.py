"""Command-line interface for causaliq-analysis."""

import click

from causaliq_analysis import __version__
from causaliq_analysis.cli.commands import register_commands
from causaliq_analysis.cli.commands.evaluate_graph import SUPPORTED_METRICS
from causaliq_analysis.cli.common import (
    _flatten_metadata,
    _get_nested_value,
    _print_summary_table,
)

__all__ = [
    "SUPPORTED_METRICS",
    "cli",
    "main",
    "register_commands",
    "_flatten_metadata",
    "_get_nested_value",
    "_print_summary_table",
]


@click.group(name="causaliq-analysis")
@click.version_option(version=__version__)
def cli() -> None:
    """
    CausalIQ Analysis CLI - Tools for analysing and visualising causal graphs.
    """
    pass


# Register the individual commands on the group
register_commands(cli)


def main() -> None:
    """Entry point for the CLI."""
    cli(prog_name="causaliq-analysis (cqalys)")


if __name__ == "__main__":  # pragma: no cover
    main()
