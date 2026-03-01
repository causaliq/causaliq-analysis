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


@cli.command(name="merge-graphs")
@click.option(
    "--input",
    "-i",
    "inputs",
    multiple=True,
    required=True,
    type=click.Path(exists=True),
    help="Input file (.graphml or .db). Can be specified multiple times.",
)
@click.option(
    "--output",
    "-o",
    required=True,
    type=click.Path(),
    help="Output file path for merged PDG (GraphML format).",
)
@click.option(
    "--filter",
    "-f",
    "filter_expr",
    default=None,
    help="Filter expression for cache entries (Python syntax). "
    "Example: \"network == 'asia' and sample_size > 500\"",
)
@click.option(
    "--weights",
    "-w",
    default=None,
    type=click.Path(exists=True),
    help="JSON file specifying metadata-driven weights. "
    "Only applies to .db cache inputs.",
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
    filter_expr: Optional[str],
    weights: Optional[str],
    cpdag: bool,
) -> None:
    """
    Merge multiple graphs into a single PDG with edge probabilities.

    Reads GraphML files (.graphml) and/or WorkflowCache databases (.db)
    and combines them into a Probabilistic Dependency Graph (PDG) using
    weighted averaging of edge probabilities.

    Input type is auto-detected by file extension:
    - .graphml: Read as GraphML file (filter/weights not applicable)
    - .db: Read graphml objects from cache entries (filter/weights apply)

    Example:
        causaliq-analysis merge-graphs -i graph1.graphml -i graph2.graphml \\
            -o merged.graphml

        causaliq-analysis merge-graphs -i results.db \\
            -f "network == 'asia' and sample_size > 500" \\
            -o merged.graphml

        causaliq-analysis merge-graphs -i results.db -w weights.json \\
            -o merged.graphml --cpdag
    """
    import json
    from io import StringIO
    from typing import Any, Dict

    from causaliq_core.graph.io import graphml
    from causaliq_core.utils import (
        FilterExpressionError,
        WeightSpecError,
        compute_weight,
        evaluate_filter,
        validate_weight_spec,
    )

    from causaliq_analysis.merge import merge_graphs

    graphs: list = []
    graph_metadata: List[Dict[str, Any]] = []
    has_cache_input = False

    for input_path in inputs:
        path_lower = input_path.lower()

        if path_lower.endswith(".db"):
            has_cache_input = True
            # Read from WorkflowCache
            try:
                from causaliq_workflow.cache import WorkflowCache

                with WorkflowCache(input_path) as cache:
                    entries = cache.list_entries()
                    click.echo(
                        f"Reading {len(entries)} entries from {input_path}"
                    )

                    filtered_count = 0
                    for entry_info in entries:
                        matrix_values = entry_info.get("matrix_values", {})
                        entry = cache.get(matrix_values)

                        if entry is None:
                            continue

                        # Get metadata for filtering and weighting
                        meta = dict(entry.metadata)

                        # Apply filter if specified
                        if filter_expr:
                            try:
                                if not evaluate_filter(filter_expr, meta):
                                    filtered_count += 1
                                    continue
                            except FilterExpressionError as e:
                                raise click.ClickException(
                                    f"Invalid filter expression: {e}"
                                )

                        # Find all graphml objects in this entry
                        found_graphs = 0
                        for obj_name in entry.object_names():
                            obj = entry.get_object(obj_name)
                            if obj is None or obj.type != "graphml":
                                continue

                            try:
                                graph = graphml.read(StringIO(obj.content))
                                graphs.append(graph)
                                graph_metadata.append(meta)
                                found_graphs += 1
                            except Exception as e:
                                raise click.ClickException(
                                    f"Failed to parse graph '{obj_name}' "
                                    f"from {matrix_values}: {e}"
                                )

                        if found_graphs == 0:
                            click.echo(
                                f"  Skipping {matrix_values}: "
                                f"no graphml objects"
                            )

                    if filter_expr and filtered_count > 0:
                        click.echo(f"  Filtered out {filtered_count} entries")

            except ImportError:
                raise click.ClickException(
                    "causaliq-workflow is required for .db cache files. "
                    "Install with: pip install causaliq-workflow"
                )
            except FileNotFoundError:
                raise click.ClickException(
                    f"Cache file not found: {input_path}"
                )
            except Exception as e:
                if "ClickException" in type(e).__name__:
                    raise
                raise click.ClickException(
                    f"Failed to read from cache '{input_path}': {e}"
                )
        else:
            # Read as GraphML file (no metadata available)
            try:
                graph = graphml.read(input_path)
                graphs.append(graph)
                graph_metadata.append({})  # Empty metadata for file inputs
            except Exception as e:
                raise click.ClickException(f"Failed to read {input_path}: {e}")

    if not graphs:
        raise click.ClickException("No graphs found to merge")

    # Compute weights from metadata if JSON file specified
    weights_list: Optional[List[float]] = None
    if weights:
        if not has_cache_input:
            raise click.ClickException(
                "Metadata-driven weights (--weights) require .db cache input"
            )

        try:
            with open(weights, "r", encoding="utf-8") as f:
                weight_spec = json.load(f)

            validate_weight_spec(weight_spec)

            # Compute raw weights
            raw_weights = [
                compute_weight(meta, weight_spec) for meta in graph_metadata
            ]

            # Normalise to sum to 1.0
            total = sum(raw_weights)
            if total > 0:
                weights_list = [w / total for w in raw_weights]
            else:
                weights_list = [1.0 / len(graphs)] * len(graphs)

            click.echo(f"Applied metadata-driven weights from {weights}")

        except json.JSONDecodeError as e:
            raise click.ClickException(f"Invalid weights JSON file: {e}")
        except WeightSpecError as e:
            raise click.ClickException(f"Invalid weight specification: {e}")
        except Exception as e:
            raise click.ClickException(f"Failed to load weights file: {e}")

    # Merge graphs
    try:
        merged = merge_graphs(graphs, weights=weights_list, cpdag=cpdag)
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
