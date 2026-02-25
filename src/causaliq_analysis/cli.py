"""Command-line interface for causaliq-analysis."""

from pathlib import Path
from typing import List, Optional, Tuple

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


@cli.command(name="migrate-trace")
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


def _parse_weights(weights_str: Optional[str]) -> Optional[List[float]]:
    """Parse comma-separated weights string.

    Args:
        weights_str: Comma-separated weights (e.g., '0.5,0.3,0.2').

    Returns:
        List of float weights, or None if input is None/empty.

    Raises:
        click.ClickException: If weights cannot be parsed.
    """
    if not weights_str:
        return None
    try:
        weights = [float(w.strip()) for w in weights_str.split(",")]
        return weights
    except ValueError as e:
        raise click.ClickException(f"Invalid weights format: {e}")


@cli.command(name="merge-graph")
@click.argument(
    "inputs",
    nargs=-1,
    required=True,
    type=click.Path(exists=True),
)
@click.option(
    "--output",
    "-o",
    required=True,
    type=click.Path(),
    help="Output file path for merged PDG (GraphML format).",
)
@click.option(
    "--weights",
    "-w",
    default=None,
    help="Comma-separated weights for each input graph. "
    "Must sum to 1.0. Default: uniform weights.",
)
@click.option(
    "--cpdag",
    is_flag=True,
    default=False,
    help="Convert DAGs to CPDAGs before merging. "
    "Averages over equivalence classes rather than specific orientations.",
)
def merge_graphs_cmd(
    inputs: Tuple[str, ...],
    output: str,
    weights: Optional[str],
    cpdag: bool,
) -> None:
    """
    Merge multiple graphs into a single PDG with edge probabilities.

    Reads GraphML files and combines them into a Probabilistic Dependency
    Graph (PDG) using weighted averaging of edge probabilities.

    INPUTS: One or more GraphML files to merge.

    Example:
        causaliq-analysis merge-graph graph1.graphml graph2.graphml \\
            -o merged.graphml

        causaliq-analysis merge-graph *.graphml -o out.graphml -w 0.5,0.3,0.2
    """
    from causaliq_core.graph.io import graphml

    from causaliq_analysis.merge import merge_graphs

    # Parse weights
    weights_list = _parse_weights(weights)

    # Validate weights count matches inputs
    if weights_list is not None and len(weights_list) != len(inputs):
        raise click.ClickException(
            f"Number of weights ({len(weights_list)}) must match "
            f"number of input files ({len(inputs)})"
        )

    # Read input graphs
    graphs = []
    for input_path in inputs:
        try:
            graph = graphml.read(input_path)
            graphs.append(graph)
        except Exception as e:
            raise click.ClickException(f"Failed to read {input_path}: {e}")

    if not graphs:  # pragma: no cover - Click validates INPUTS is non-empty
        raise click.ClickException("No input graphs provided")

    # Merge graphs (graphml.read returns Union[SDG, PDAG, DAG] but
    # merge_graphs handles DAG/PDAG/PDG - SDGs are rare in practice)
    try:
        merged = merge_graphs(
            graphs, weights=weights_list, cpdag=cpdag  # type: ignore[arg-type]
        )
    except (TypeError, ValueError) as e:
        raise click.ClickException(f"Merge failed: {e}")

    # Ensure output directory exists
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write merged PDG
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            graphml.write_pdg(merged, f)
        click.echo(f"Merged {len(graphs)} graphs to {output_path}")
    except Exception as e:
        raise click.ClickException(f"Failed to write output: {e}")


def main() -> None:
    """Entry point for the CLI."""
    cli(prog_name="causaliq-analysis (cqalys)")


if __name__ == "__main__":  # pragma: no cover
    main()
