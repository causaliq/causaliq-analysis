"""Command-line interface for causaliq-analysis."""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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


@cli.command(name="evaluate-graph")
@click.option(
    "--graph",
    "-g",
    required=True,
    type=click.Path(exists=True),
    help="Path to learned graph (GraphML format).",
)
@click.option(
    "--reference",
    "-r",
    required=True,
    type=click.Path(exists=True),
    help="Path to ground truth/reference graph (GraphML format).",
)
@click.option(
    "--output",
    "-o",
    default=None,
    type=click.Path(),
    help="Output file path for metrics (JSON format). "
    "If omitted, prints to stdout.",
)
@click.option(
    "--bayesys",
    "-b",
    default=None,
    type=click.Choice(["v1.3", "v1.5", "v1.5+"]),
    help="Include Bayesys metrics with specified version. "
    "Most common is 'v1.5+' for latest.",
)
@click.option(
    "--format",
    "-f",
    "output_format",
    default="json",
    type=click.Choice(["json", "table"]),
    help="Output format: 'json' (default) or 'table' for human-readable.",
)
def evaluate_graph_cmd(
    graph: str,
    reference: str,
    output: Optional[str],
    bayesys: Optional[str],
    output_format: str,
) -> None:
    """
    Evaluate a learned graph against a ground truth reference.

    Computes structural accuracy metrics including precision, recall, F1,
    and SHD (Structural Hamming Distance). Optionally includes Bayesys
    metrics (DDM, BSF) for compatibility with published benchmarks.

    Metric naming convention:
    - Standard metrics: precision, recall, f1, shd
    - Bayesys metrics: precision_b, recall_b, f1_b, shd_b, ddm, bsf

    Example:
        causaliq-analysis evaluate-graph -g learned.graphml \\
            -r ground_truth.graphml

        causaliq-analysis evaluate-graph -g learned.graphml \\
            -r ground_truth.graphml --bayesys=v1.5+ -o metrics.json

        causaliq-analysis evaluate-graph -g learned.graphml \\
            -r ground_truth.graphml --format=table
    """
    import json
    from typing import Dict, Union

    from causaliq_core.graph.io import graphml

    from causaliq_analysis.metrics import pdag_compare

    # Read learned graph
    try:
        learned_graph = graphml.read(graph)
    except Exception as e:
        raise click.ClickException(f"Failed to read learned graph: {e}")

    # Read reference graph
    try:
        reference_graph = graphml.read(reference)
    except Exception as e:
        raise click.ClickException(f"Failed to read reference graph: {e}")

    # Compute metrics
    try:
        raw_metrics = pdag_compare(learned_graph, reference_graph, bayesys)
    except ValueError as e:
        raise click.ClickException(f"Comparison failed: {e}")
    except TypeError as e:
        raise click.ClickException(f"Invalid graph type: {e}")

    # Convert to standardised naming convention
    metrics: Dict[str, Union[int, float, None]] = {
        "precision": raw_metrics.get("p"),
        "recall": raw_metrics.get("r"),
        "f1": raw_metrics.get("f1"),
        "shd": raw_metrics.get("shd"),
    }

    # Add Bayesys metrics if requested
    if bayesys:
        metrics.update(
            {
                "precision_b": raw_metrics.get("p-b"),
                "recall_b": raw_metrics.get("r-b"),
                "f1_b": raw_metrics.get("f1-b"),
                "shd_b": raw_metrics.get("shd-b"),
                "ddm": raw_metrics.get("ddm"),
                "bsf": raw_metrics.get("bsf"),
            }
        )

    # Output results
    if output_format == "table":
        click.echo("Structural Evaluation Metrics")
        click.echo("=" * 40)
        for key, value in metrics.items():
            if value is not None:
                if isinstance(value, float):
                    click.echo(f"{key:15s}: {value:.4f}")
                else:
                    click.echo(f"{key:15s}: {value}")
    else:
        # JSON format
        json_output = json.dumps(metrics, indent=2)
        if output:
            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(json_output)
            click.echo(f"Metrics written to {output_path}")
        else:
            click.echo(json_output)


@cli.command(name="summarise")
@click.option(
    "--metric",
    "-m",
    "metrics",
    multiple=True,
    required=True,
    help="Metric specification: <field>.<stat> (e.g., f1.mean, shd.sd). "
    "Supported stats: mean, sd, count. Can specify multiple.",
)
@click.option(
    "--input",
    "-i",
    "input_files",
    multiple=True,
    required=True,
    type=click.Path(exists=True),
    help="Input file(s): JSON metrics or workflow cache (.db). "
    "Can specify multiple.",
)
@click.option(
    "--output",
    "-o",
    required=True,
    help="Output path: CSV file or '-' for terminal output.",
)
@click.option(
    "--filter",
    "-f",
    "filter_expr",
    default=None,
    help="Filter expression to select entries (e.g., 'status == completed').",
)
def summarise_cmd(
    metrics: Tuple[str, ...],
    input_files: Tuple[str, ...],
    output: str,
    filter_expr: Optional[str],
) -> None:
    """
    Summarise numerical metrics across experiments.

    Computes summary statistics (mean, SD, count) for numerical metrics
    extracted from JSON files or workflow cache (.db) entries. Produces
    publication-ready tabular output in CSV format.

    Metric specifications use the format <field>.<statistic>:
    - f1.mean - compute mean of 'f1' values
    - shd.sd - compute standard deviation of 'shd' values
    - precision.count - count non-null 'precision' values

    The field name follows a dotted path convention for nested metadata.
    For workflow caches, metrics are extracted from entry metadata
    (e.g., 'causaliq-analysis.evaluate_graph.f1' becomes 'f1').

    Example:
        causaliq-analysis summarise -m f1.mean -m f1.sd -m shd.mean \\
            -i results.json -o summary.csv

        causaliq-analysis summarise -m precision.mean -m recall.mean \\
            -i cache.db -o metrics_summary.csv

        causaliq-analysis summarise -m f1.mean -i cache.db \\
            -f "network == 'asia'" -o asia_summary.csv

        causaliq-analysis summarise -m f1.mean -m f1.sd -i cache.db -o -
    """
    import csv
    import json
    import statistics
    from typing import Any, Dict, List

    # Supported statistics
    SUPPORTED_STATS = {"mean", "sd", "count"}

    # Parse metric specifications
    parsed_metrics: List[Tuple[str, str]] = []
    for spec in metrics:
        if "." not in spec:
            raise click.ClickException(
                f"Invalid metric spec '{spec}': must be <field>.<stat>"
            )
        parts = spec.rsplit(".", 1)
        field, stat = parts[0], parts[1]
        if stat not in SUPPORTED_STATS:
            raise click.ClickException(
                f"Unknown statistic '{stat}' in '{spec}'. "
                f"Supported: {', '.join(sorted(SUPPORTED_STATS))}"
            )
        parsed_metrics.append((field, stat))

    # Extract unique fields for value collection
    unique_fields = list(dict.fromkeys(f for f, _ in parsed_metrics))

    # Collect values from all inputs
    all_values: Dict[str, List[float]] = {field: [] for field in unique_fields}

    for input_path in input_files:
        path_lower = input_path.lower()

        if path_lower.endswith(".db"):
            # Read from workflow cache
            try:
                from causaliq_workflow.cache import WorkflowCache
            except ImportError:  # pragma: no cover
                raise click.ClickException(
                    "causaliq-workflow required to read .db caches. "
                    "Install with: pip install causaliq-workflow"
                )

            try:
                with WorkflowCache(input_path) as cache:
                    entries = cache.list_entries()

                    for entry_info in entries:
                        entry = cache.get(entry_info["matrix_values"])
                        if entry is None:  # pragma: no cover
                            continue

                        # Flatten metadata for access
                        flat_meta = _flatten_metadata(entry.metadata)

                        # Apply filter if specified
                        if filter_expr:
                            try:
                                from causaliq_core.utils import evaluate_filter

                                if not evaluate_filter(filter_expr, flat_meta):
                                    continue
                            except Exception:
                                continue

                        # Extract metric values
                        for field in unique_fields:
                            value = _get_nested_value(flat_meta, field)
                            if value is not None and isinstance(
                                value, (int, float)
                            ):
                                all_values[field].append(float(value))

            except Exception as e:
                raise click.ClickException(
                    f"Failed to read cache '{input_path}': {e}"
                )

        elif path_lower.endswith(".json"):
            # Read from JSON file
            try:
                with open(input_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Handle single dict or list of dicts
                records: List[Any]
                if isinstance(data, dict):
                    records = [data]
                elif isinstance(data, list):
                    records = data
                else:
                    raise click.ClickException(
                        f"JSON file must contain object or array: {input_path}"
                    )

                for record in records:
                    if not isinstance(record, dict):
                        continue

                    # Apply filter if specified
                    if filter_expr:
                        try:
                            from causaliq_core.utils import evaluate_filter

                            if not evaluate_filter(filter_expr, record):
                                continue
                        except Exception:
                            continue

                    # Extract metric values
                    for field in unique_fields:
                        value = _get_nested_value(record, field)
                        if value is not None and isinstance(
                            value, (int, float)
                        ):
                            all_values[field].append(float(value))

            except json.JSONDecodeError as e:
                raise click.ClickException(
                    f"Invalid JSON file '{input_path}': {e}"
                )
            except Exception as e:
                raise click.ClickException(
                    f"Failed to read '{input_path}': {e}"
                )
        else:
            raise click.ClickException(
                f"Unsupported file type: {input_path}. "
                "Use .json or .db files."
            )

    # Compute summary statistics
    results: Dict[str, Any] = {}
    for field, stat in parsed_metrics:
        col_name = f"{field}.{stat}"
        values = all_values[field]

        if stat == "count":
            results[col_name] = len(values)
        elif stat == "mean":
            if values:
                results[col_name] = statistics.mean(values)
            else:
                results[col_name] = None
        elif stat == "sd":
            if len(values) >= 2:
                results[col_name] = statistics.stdev(values)
            else:
                results[col_name] = None

    # Write output
    if output == "-":
        # Terminal output - format as table
        _print_summary_table(results)
    else:
        # CSV file output
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(output_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                # Header row
                writer.writerow(results.keys())
                # Data row
                writer.writerow(results.values())
            click.echo(f"Summary written to {output_path}")
        except Exception as e:
            raise click.ClickException(f"Failed to write output: {e}")


def _print_summary_table(results: Dict[str, Any]) -> None:
    """Print summary results as a formatted table to terminal.

    Args:
        results: Dictionary of metric names to computed values.
    """
    if not results:
        click.echo("No results to display.")
        return

    # Format values for display
    def fmt_value(v: Any) -> str:
        if v is None:
            return "None"
        if isinstance(v, float):
            return f"{v:.4f}"
        return str(v)

    headers = list(results.keys())
    values = [fmt_value(v) for v in results.values()]

    # Calculate column widths
    widths = [max(len(h), len(v)) for h, v in zip(headers, values)]

    # Build format string
    header_line = "  ".join(h.ljust(w) for h, w in zip(headers, widths))
    value_line = "  ".join(v.ljust(w) for v, w in zip(values, widths))
    separator = "  ".join("-" * w for w in widths)

    click.echo(header_line)
    click.echo(separator)
    click.echo(value_line)


def _flatten_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Flatten nested metadata for field access.

    Flattens provider/action structure to simple field names.
    E.g., {'causaliq-analysis': {'eval': {'f1': 0.9}}} becomes {'f1': 0.9}.
    """
    flat: Dict[str, Any] = {}

    for provider_name, provider_data in metadata.items():
        if isinstance(provider_data, dict):
            for action_name, action_data in provider_data.items():
                if isinstance(action_data, dict):
                    for key, value in action_data.items():
                        # Use simple key if no conflict
                        if key not in flat:
                            flat[key] = value
                        # Also store qualified key
                        qual_key = f"{provider_name}.{action_name}.{key}"
                        flat[qual_key] = value
                else:
                    flat[f"{provider_name}.{action_name}"] = action_data
        else:
            flat[provider_name] = provider_data

    return flat


def _get_nested_value(data: Dict[str, Any], field: str) -> Any:
    """Get value from dict using dotted path notation.

    Args:
        data: Dictionary to search.
        field: Field name, optionally with dots for nested access.

    Returns:
        Value if found, None otherwise.
    """
    # First try direct key lookup
    if field in data:
        return data[field]

    # Try dotted path traversal
    parts = field.split(".")
    current = data
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current


def main() -> None:
    """Entry point for the CLI."""
    cli(prog_name="causaliq-analysis (cqalys)")


if __name__ == "__main__":  # pragma: no cover
    main()
