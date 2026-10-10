"""The ``migrate-trace`` command."""

from typing import Any, Dict, Optional

import click

from causaliq_analysis.validation import (
    parse_sample_size,
    parse_seed_cli,
    single_value_callback,
)

__all__ = ["migrate_trace_cmd"]


@click.command(name="migrate-trace")
@click.option(
    "-n",
    "--network",
    multiple=True,
    callback=single_value_callback,
    required=True,
    help="Network name to process",
)
@click.option(
    "-s",
    "--series",
    multiple=True,
    callback=single_value_callback,
    required=True,
    help="Series path (e.g., TABU/SAMPLE/BASE)",
)
@click.option(
    "-r",
    "--root-dir",
    "root_dir",
    multiple=True,
    callback=single_value_callback,
    default=("experiments",),
    type=click.Path(exists=True),
    help="Root directory containing experiment traces",
)
@click.option(
    "-N",
    "--sample-size",
    "sample_size",
    multiple=True,
    callback=single_value_callback,
    default=(),
    help="Filter by sample size (e.g., 10k, 100k, or integer). "
    "Omit to include all sample sizes.",
)
@click.option(
    "-S",
    "--seed",
    multiple=True,
    callback=single_value_callback,
    default=("",),
    help="Seed value or range (e.g., '5' or '0-24'). Empty means all seeds.",
)
@click.option(
    "-o",
    "--output",
    multiple=True,
    callback=single_value_callback,
    default=(),
    type=click.Path(),
    help="Output directory for GraphML files. "
    "Defaults to migrated/<series>/<network>.",
)
def migrate_trace_cmd(
    network: str,
    series: str,
    root_dir: str,
    sample_size: Optional[str],
    seed: str,
    output: Optional[str],
) -> None:
    """
    Migrate legacy Trace pickle files to GraphML format.

    Converts Trace files containing learnt graphs into portable GraphML format
    with accompanying metadata JSON files.

    Example:
        causaliq-analysis migrate-trace -n asia -s TABU/SAMPLE/BASE
                            -r experiments -N 10k -S 0-1 -o migrated/asia
    """
    request = _migrate_request(
        network, series, root_dir, sample_size, seed, output
    )
    _run_migrate(request)


def _migrate_request(
    network: str,
    series: str,
    root_dir: str,
    sample_size: Optional[str],
    seed: str,
    output: Optional[str],
) -> Dict[str, Any]:
    """Build the migration request from the command options.

    Args:
        network: Network name to process.
        series: Series path.
        root_dir: Root directory containing experiment traces.
        sample_size: Optional sample size filter.
        seed: Seed value or range.
        output: Optional output directory.

    Returns:
        Dictionary of migration arguments.
    """
    # Build partial_id from series and network
    partial_id = f"{series}/{network}"

    # Parse optional sample_size
    sample_size_int = None
    if sample_size is not None:
        sample_size_int = parse_sample_size(sample_size)

    # Parse seed
    seed_tuple = parse_seed_cli(seed)

    # Determine output directory
    if not output:
        output = f"migrated/{partial_id}"

    return {
        "partial_id": partial_id,
        "root_dir": root_dir,
        "sample_size": sample_size_int,
        "seed": seed_tuple if seed_tuple else None,
        "output": output,
    }


def _run_migrate(request: Dict[str, Any]) -> None:
    """Run migration and write the results to disk.

    Args:
        request: Migration request built from the command options.

    Raises:
        click.ClickException: If migration or writing fails.
    """
    from causaliq_analysis.migrate import (
        run_migrate_trace,
        write_migrate_result,
    )

    try:
        # Generate GraphML and metadata content
        result = run_migrate_trace(
            partial_id=request["partial_id"],
            root_dir=request["root_dir"],
            sample_size=request["sample_size"],
            seed=request["seed"],
            log_fn=click.echo,
        )

        # Write to files
        write_migrate_result(result, request["output"], log_fn=click.echo)

        _echo_migration_result(result, request["output"])
    except ValueError as e:
        raise click.ClickException(str(e))
    except Exception as e:
        raise click.ClickException(f"Migration failed: {e}")


def _echo_migration_result(result: Any, output: str) -> None:
    """Print the migration completion summary.

    Args:
        result: Migration result returned by the migrator.
        output: Output directory the graphs were written to.
    """
    click.echo(
        f"Migration complete: {result.num_graphs} graphs "
        f"written to {output}"
    )
    if result.skipped:
        click.echo(f"Skipped {result.skipped} traces (no result graph)")
