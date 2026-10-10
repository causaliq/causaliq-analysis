"""Command registry for the causaliq-analysis CLI.

Each command lives in its own module in this sub-package. ``COMMANDS``
lists the command objects in registration order and ``register_commands``
adds them to the ``click`` group, so adding a command means adding one
module plus one entry here.
"""

from typing import Tuple

import click

from causaliq_analysis.cli.commands.best_graph import best_graph_cmd
from causaliq_analysis.cli.commands.evaluate_graph import (
    evaluate_graph_cmd,
)
from causaliq_analysis.cli.commands.merge_graphs import merge_graphs_cmd
from causaliq_analysis.cli.commands.migrate_trace import migrate_trace_cmd
from causaliq_analysis.cli.commands.plot import plot_cmd
from causaliq_analysis.cli.commands.summarise import summarise_cmd

__all__ = ["COMMANDS", "register_commands"]

# Registry of CLI commands
COMMANDS: Tuple[click.Command, ...] = (
    migrate_trace_cmd,
    merge_graphs_cmd,
    evaluate_graph_cmd,
    best_graph_cmd,
    summarise_cmd,
    plot_cmd,
)


def register_commands(group: click.Group) -> None:
    """Register every command on the CLI group.

    Args:
        group: Click group to register the commands on.
    """
    for command in COMMANDS:
        group.add_command(command)
