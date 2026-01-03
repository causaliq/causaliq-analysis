"""Command-line interface for causaliq-analysis."""

from pathlib import Path

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


@cli.command(name="graph-average")
@click.option("--network", required=True, help="Network name to process")
@click.option(
    "--N",
    "sample_size",
    required=True,
    help="Sample size (e.g., 10k, 100k, or integer)",
)
@click.option(
    "--seeds",
    default="",
    help="Comma-separated seed values (e.g., '0,1,2'). Empty means all seeds.",
)
@click.option(
    "--basis",
    type=click.Choice(["dag", "pdag"], case_sensitive=False),
    default="dag",
    help="Whether to use DAG or PDAG representation",
)
@click.option(
    "--output", required=True, type=click.Path(), help="Output CSV file path"
)
@click.option(
    "--series", required=True, help="Series path (e.g., TABU/SAMPLE/BASE)"
)
@click.option(
    "--root-dir",
    "root_dir",
    required=True,
    type=click.Path(exists=True),
    help="Root directory containing experiment traces",
)
def graph_average_cmd(
    network: str,
    sample_size: str,
    seeds: str,
    basis: str,
    output: str,
    series: str,
    root_dir: str,
) -> None:
    """
    Compute edge probabilities by averaging graphs across multiple experiments.

    Example:
        cqalys graph-average --network=asia --N=10k --seeds=0,1
                             --basis=pdag --output=average.csv
                             --series=TABU/SAMPLE/BASE --root-dir=experiments
    """
    from causaliq_analysis.graph import _validate_average_params, average
    from causaliq_analysis.trace import Trace

    # Parse sample size (handle formats like "10k", "100k", or plain integers)
    sample_size_int = parse_sample_size(sample_size)

    # Parse seeds
    seed_tuple = parse_seeds_cli(seeds)

    # Parse basis
    pdag = basis.lower() == "pdag"

    # Validate parameters using common validation
    try:
        _validate_average_params(sample_size_int, pdag, seed_tuple)
    except (TypeError, ValueError) as e:
        raise click.ClickException(str(e))

    # Read traces
    partial_id = f"{series}/{network}"
    try:
        traces = Trace.read(partial_id=partial_id, root_dir=root_dir)
        if traces is None:
            raise click.ClickException(
                f"No traces found for {partial_id} in {root_dir}"
            )
    except Exception as e:
        raise click.ClickException(f"Failed to read traces: {e}")

    # Filter traces to count how many will actually be used
    # (Same logic as in the average() function)
    matching_traces = {}
    for trace_id, trace in traces.items():
        # Check if trace has the right sample size
        if "N" not in trace.context or trace.context["N"] != sample_size_int:
            continue

        # Extract seed from trace ID (assuming format like "network_N1000_42")
        # If seeds tuple is empty, include all traces with matching sample size
        if len(seed_tuple) == 0:
            matching_traces[trace_id] = trace
        else:
            # Try to extract seed from trace_id
            parts = trace_id.split("_")
            for part in parts:
                try:
                    seed = int(part)
                    if seed in seed_tuple:
                        matching_traces[trace_id] = trace
                        break
                except ValueError:
                    continue

    if not matching_traces:
        raise click.ClickException(
            f"No traces found matching sample_size={sample_size_int} "
            f"and seeds={seed_tuple}"
        )

    # Compute average
    try:
        df = average(
            traces=traces,
            sample_size=sample_size_int,
            pdag=pdag,
            seeds=seed_tuple,
        )
    except Exception as e:
        raise click.ClickException(f"Failed to compute average: {e}")

    # Write output
    try:
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output, index=False)
        click.echo(f"Edge probabilities written to {output}")
        click.echo(f"Averaged {len(matching_traces)} graphs")
    except Exception as e:
        raise click.ClickException(f"Failed to write output: {e}")


def main() -> None:
    """Entry point for the CLI."""
    cli(prog_name="causaliq-analysis (cqalys)")


if __name__ == "__main__":  # pragma: no cover
    main()
