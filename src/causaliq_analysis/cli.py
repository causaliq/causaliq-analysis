"""Command-line interface for causaliq-analysis."""

from typing import Optional

import click

from . import __version__
from .validation import parse_sample_size, parse_seeds_cli


@click.group(name="causaliq-analysis")
@click.version_option(version=__version__)
def cli() -> None:
    """
    CausalIQ Analysis CLI - Tools for analysing and visualising causal graphs.
    """
    pass


@cli.command(name="migrate_trace")
@click.option("--network", required=True, help="Network name to process")
@click.option(
    "--series", required=True, help="Series path (e.g., TABU/SAMPLE/BASE)"
)
@click.option(
    "--root-dir",
    "root_dir",
    default="experiments",
    type=click.Path(exists=True),
    help="Root directory containing experiment traces",
)
@click.option(
    "--N",
    "sample_size",
    default=None,
    help="Filter by sample size (e.g., 10k, 100k, or integer). "
    "Omit to include all sample sizes.",
)
@click.option(
    "--seeds",
    default="",
    help="Comma-separated seed values (e.g., '0,1,2'). Empty means all seeds.",
)
@click.option(
    "--output",
    default=None,
    type=click.Path(),
    help="Output directory for GraphML files. "
    "Defaults to migrated/<series>/<network>.",
)
def migrate_trace_cmd(
    network: str,
    series: str,
    root_dir: str,
    sample_size: Optional[str],
    seeds: str,
    output: Optional[str],
) -> None:
    """
    Migrate legacy Trace pickle files to GraphML format.

    Converts Trace files containing learnt graphs into portable GraphML format
    with accompanying metadata JSON files.

    Example:
        cqalys migrate_trace --network=asia --series=TABU/SAMPLE/BASE
                             --root-dir=experiments --N=10k --seeds=0,1
                             --output=migrated/asia
    """
    from causaliq_analysis.migrate import (
        run_migrate_trace,
        write_migrate_result,
    )

    # Build partial_id from series and network
    partial_id = f"{series}/{network}"

    # Parse optional sample_size
    sample_size_int = None
    if sample_size is not None:
        sample_size_int = parse_sample_size(sample_size)

    # Parse seeds
    seed_tuple = parse_seeds_cli(seeds)

    # Determine output directory
    if not output:
        output = f"migrated/{partial_id}"

    try:
        # Generate GraphML and metadata content
        result = run_migrate_trace(
            partial_id=partial_id,
            root_dir=root_dir,
            sample_size=sample_size_int,
            seeds=seed_tuple if seed_tuple else None,
            log_fn=click.echo,
        )

        # Write to files
        write_migrate_result(result, output, log_fn=click.echo)

        click.echo(
            f"Migration complete: {result.num_graphs} graphs "
            f"written to {output}"
        )
        if result.skipped:
            click.echo(f"Skipped {result.skipped} traces (no result graph)")
    except ValueError as e:
        raise click.ClickException(str(e))
    except Exception as e:
        raise click.ClickException(f"Migration failed: {e}")


def main() -> None:
    """Entry point for the CLI."""
    cli(prog_name="causaliq-analysis (cqalys)")


if __name__ == "__main__":  # pragma: no cover
    main()
