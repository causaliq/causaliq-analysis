# CausalIQ Analysis CLI

The command-line interface provides commands for analysing and visualising
learned causal graphs, including structural metrics, stability assessment,
significance tests, and publication-ready tables and charts.

Each command is a `click` command implemented in its own module under
`causaliq_analysis.cli.commands`. `cli/commands/__init__.py` lists the command
objects in `COMMANDS` and registers them on the group, so adding a command
means adding one module plus one registry entry.

## Entry point

::: causaliq_analysis.cli
    options:
        show_root_heading: true
        show_source: false
        heading_level: 3

## Command registry

::: causaliq_analysis.cli.commands
    options:
        show_root_heading: true
        show_source: false
        heading_level: 3

## Commands

- [Migrate Trace](cli/migrate_trace.md)
- [Merge Graphs](cli/merge_graphs.md)
- [Evaluate Graph](cli/evaluate_graph.md)
- [Best Graph](cli/best_graph.md)
- [Summarise](cli/summarise.md)
- [Plot](cli/plot.md)

## Shared helpers

`causaliq_analysis.cli.common` holds the internal metadata flattening,
nested-value lookup and summary-table helpers shared by the command modules.
They are implementation details; the public API is the `click` group and the
commands listed above.