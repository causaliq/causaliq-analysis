"""Command-line interface for causaliq-analysis."""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import click

from . import __version__
from .validation import (
    parse_sample_size,
    parse_seed_cli,
    single_value_callback,
)


@click.group(name="causaliq-analysis")
@click.version_option(version=__version__)
def cli() -> None:
    """
    CausalIQ Analysis CLI - Tools for analysing and visualising causal graphs.
    """
    pass


@cli.command(name="migrate-trace")
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

    # Parse seed
    seed_tuple = parse_seed_cli(seed)

    # Determine output directory
    if not output:
        output = f"migrated/{partial_id}"

    try:
        # Generate GraphML and metadata content
        result = run_migrate_trace(
            partial_id=partial_id,
            root_dir=root_dir,
            sample_size=sample_size_int,
            seed=seed_tuple if seed_tuple else None,
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
    multiple=True,
    callback=single_value_callback,
    required=True,
    type=click.Path(),
    help="Output directory for merged PDG. Creates folder with "
    "pdg.graphml and _meta.json files.",
)
@click.option(
    "--filter",
    "-f",
    "filter_expr",
    multiple=True,
    callback=single_value_callback,
    default=(),
    help="Filter expression for cache entries (Python syntax). "
    "Example: \"network == 'asia' and sample_size > 500\"",
)
@click.option(
    "--weights",
    "-w",
    multiple=True,
    callback=single_value_callback,
    default=(),
    type=click.Path(exists=True),
    help="JSON file specifying metadata-driven weights. "
    "Only applies to .db cache inputs.",
)
@click.option(
    "--object-type",
    "-t",
    "object_type",
    default=None,
    type=click.Choice(["dag", "cpdag", "pdg"]),
    help="Select graph object type: 'dag' (use DAGs), 'cpdag' "
    "(use DAGs converted to CPDAGs), 'pdg' (use PDGs). "
    "If not set, all graphml objects are used.",
)
@click.option(
    "--strategy",
    "-s",
    default="average",
    type=click.Choice(["average", "noisy_or", "max"]),
    help="Merge strategy: 'average' (weighted averaging, default), "
    "'noisy_or' (noisy-OR existence + weighted orientation), "
    "'max' (most confident source per edge).",
)
def merge_graphs_cmd(
    inputs: Tuple[str, ...],
    output: str,
    filter_expr: Optional[str],
    weights: Optional[str],
    object_type: Optional[str],
    strategy: str,
) -> None:
    """
    Merge multiple graphs into a single PDG with edge probabilities.

    Reads GraphML files (.graphml) and/or WorkflowCache databases (.db)
    and combines them into a Probabilistic Dependency Graph (PDG) using
    the specified merge strategy.

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
            -o merged.graphml --object-type=cpdag

        causaliq-analysis merge-graphs -i results.db \\
            --strategy noisy_or -o merged.graphml
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
    from causaliq_analysis.validation import validate_filter_expression

    # Derive cpdag flag and object filter from object_type
    cpdag = object_type == "cpdag"
    obj_filter = "dag" if object_type == "cpdag" else object_type

    # Pre-validate filter expression syntax
    if filter_expr:
        try:
            validate_filter_expression(filter_expr)
        except ValueError as e:
            raise click.ClickException(str(e))

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

                    # Pre-resolve random() in filter
                    resolved_filter = filter_expr
                    extra_names: Dict[str, Any] = {}
                    if filter_expr and "random(" in filter_expr:
                        from causaliq_core.utils import (
                            resolve_random_calls,
                        )

                        _meta = []
                        for _ei in entries:
                            _mv = _ei.get("matrix_values", {})
                            _fe = cache.get(_mv)
                            if _fe is not None:
                                _meta.append(dict(_fe.metadata))
                        resolved_filter, extra_names = resolve_random_calls(
                            filter_expr, _meta
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
                        if resolved_filter:
                            try:
                                if not evaluate_filter(
                                    resolved_filter,
                                    {**meta, **extra_names},
                                ):
                                    filtered_count += 1
                                    continue
                            except FilterExpressionError as e:
                                raise click.ClickException(
                                    f"Invalid filter expression: {e}"
                                )

                        # Find graphml objects in this entry
                        found_graphs = 0
                        for obj_type in entry.object_types():
                            if (
                                obj_filter is not None
                                and obj_type != obj_filter
                            ):
                                continue
                            obj = entry.get_object(obj_type)
                            if obj is None or obj.format != "graphml":
                                continue

                            try:
                                graph = graphml.read(StringIO(obj.content))
                                graphs.append(graph)
                                graph_metadata.append(meta)
                                found_graphs += 1
                            except Exception as e:
                                raise click.ClickException(
                                    f"Failed to parse graph '{obj_type}' "
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
        merged = merge_graphs(
            graphs,
            weights=weights_list,
            cpdag=cpdag,
            strategy=strategy,
        )
    except (TypeError, ValueError) as e:
        raise click.ClickException(f"Merge failed: {e}")

    # Create output directory
    output_dir = Path(output)
    output_dir.mkdir(parents=True, exist_ok=True)

    pdg_path = output_dir / "pdg.graphml"
    meta_path = output_dir / "_meta.json"

    # Write merged PDG
    try:
        with open(pdg_path, "w", encoding="utf-8") as f:
            graphml.write_pdg(merged, f)
    except Exception as e:
        raise click.ClickException(f"Failed to write PDG: {e}")

    # Write metadata
    meta_data: Dict[str, Any] = {
        "num_graphs": len(graphs),
        "object_type": object_type,
        "weights_file": weights if weights else None,
        "filter": filter_expr if filter_expr else None,
    }
    if weights_list:
        meta_data["weights_applied"] = weights_list

    try:
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta_data, f, indent=2)
    except Exception as e:
        raise click.ClickException(f"Failed to write metadata: {e}")

    click.echo(f"Merged {len(graphs)} graphs to {output_dir}")


# Supported metrics for evaluate-graph command
SUPPORTED_METRICS = frozenset(
    {"f1", "equiv.f1", "shd", "equiv.shd", "precision", "recall"}
)


@cli.command(name="evaluate-graph")
@click.option(
    "--input",
    "-i",
    "input_graph",
    required=True,
    type=click.Path(exists=True),
    help="Path to learned graph (.csv, .graphml, .tetrad, .xdsl, .dsc).",
)
@click.option(
    "--reference",
    "-r",
    required=True,
    type=click.Path(exists=True),
    help="Path to reference graph (.csv, .graphml, .tetrad, .xdsl, .dsc).",
)
@click.option(
    "--metric",
    "-m",
    "metrics_requested",
    multiple=True,
    required=True,
    help="Metric to compute. Supported: f1, shd, precision, recall, "
    "equiv.f1, equiv.shd. Can specify multiple.",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output file path for metrics JSON. If omitted, prints to stdout.",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["json", "table"]),
    default="json",
    help="Output format: json (default) or table.",
)
def evaluate_graph_cmd(
    input_graph: str,
    reference: str,
    metrics_requested: Tuple[str, ...],
    output: Optional[str],
    output_format: str,
) -> None:
    """
    Evaluate a learned graph against a ground truth reference.

    Computes structural accuracy metrics including F1 and SHD (Structural
    Hamming Distance). Supports both direct comparison and equivalence
    class comparison (comparing CPDAGs).

    Supported metrics:
    - f1: F1 score from direct graph comparison
    - shd: Structural Hamming Distance from direct comparison
    - precision: Precision from direct comparison
    - recall: Recall from direct comparison
    - equiv.f1: F1 score comparing equivalence classes (CPDAGs)
    - equiv.shd: SHD comparing equivalence classes (CPDAGs)

    Example:
        causaliq-analysis evaluate-graph -i learned.graphml \\
            -r ground_truth.graphml -m f1 -m shd

        causaliq-analysis evaluate-graph -i learned.graphml \\
            -r ground_truth.graphml -m equiv.f1 -m equiv.shd

        causaliq-analysis evaluate-graph -i learned.graphml \\
            -r ground_truth.graphml -m f1 --format=table
    """
    import json
    from typing import Any, Dict, Union

    from causaliq_core.bn.io import read_bn
    from causaliq_core.graph import DAG, PDAG
    from causaliq_core.graph.convert import dag_to_pdag, pdag_to_cpdag
    from causaliq_core.graph.io import read_graph

    from causaliq_analysis.metrics import pdag_compare

    def _read_graph_file(path: str) -> Any:
        """Read graph from file, auto-detecting format from suffix."""
        suffix = path.lower().split(".")[-1]
        if suffix in ("xdsl", "dsc"):
            return read_bn(path).dag
        else:
            return read_graph(path)

    def _to_cpdag(g: Any) -> PDAG:
        """Convert a graph to its CPDAG (equivalence class)."""
        if isinstance(g, DAG):
            return dag_to_pdag(g)
        elif isinstance(g, PDAG):
            cpdag = pdag_to_cpdag(g)
            if cpdag is None:
                raise ValueError("PDAG is not extendable to a CPDAG")
            return cpdag
        else:
            raise TypeError(f"Cannot convert {type(g).__name__} to CPDAG")

    # Validate requested metrics
    invalid = set(metrics_requested) - SUPPORTED_METRICS
    if invalid:
        raise click.ClickException(
            f"Invalid metric(s): {', '.join(sorted(invalid))}. "
            f"Supported: {', '.join(sorted(SUPPORTED_METRICS))}"
        )
    metrics_to_compute = set(metrics_requested)

    # Read learned graph
    try:
        learned_graph = _read_graph_file(input_graph)
    except Exception as e:
        raise click.ClickException(f"Failed to read learned graph: {e}")

    # Read reference graph
    try:
        reference_graph = _read_graph_file(reference)
    except Exception as e:
        raise click.ClickException(f"Failed to read reference graph: {e}")

    # Determine which comparisons are needed
    need_direct = bool(
        {"f1", "shd", "precision", "recall"} & metrics_to_compute
    )
    need_equiv = bool({"equiv.f1", "equiv.shd"} & metrics_to_compute)

    metrics: Dict[str, Union[int, float, None]] = {}

    # Compute direct metrics if needed
    if need_direct:
        try:
            raw_metrics = pdag_compare(learned_graph, reference_graph)
        except ValueError as e:
            raise click.ClickException(f"Comparison failed: {e}")
        except TypeError as e:
            raise click.ClickException(f"Invalid graph type: {e}")

        if "f1" in metrics_to_compute:
            metrics["f1"] = raw_metrics.get("f1")
        if "shd" in metrics_to_compute:
            metrics["shd"] = raw_metrics.get("shd")
        if "precision" in metrics_to_compute:
            metrics["precision"] = raw_metrics.get("p")
        if "recall" in metrics_to_compute:
            metrics["recall"] = raw_metrics.get("r")

    # Compute equivalence class metrics if needed
    if need_equiv:
        try:
            learned_cpdag = _to_cpdag(learned_graph)
            reference_cpdag = _to_cpdag(reference_graph)
            equiv_metrics = pdag_compare(learned_cpdag, reference_cpdag)
        except (ValueError, TypeError) as e:
            click.echo(
                f"Warning: skipping equiv metrics ({e})",
                err=True,
            )
            need_equiv = False

        if need_equiv:
            if "equiv.f1" in metrics_to_compute:
                metrics["equiv.f1"] = equiv_metrics.get("f1")
            if "equiv.shd" in metrics_to_compute:
                metrics["equiv.shd"] = equiv_metrics.get("shd")

    # Output results
    if output_format == "table":
        # Table format output
        click.echo("\nStructural Evaluation Metrics")
        click.echo("-" * 40)
        for metric_name, value in sorted(metrics.items()):
            if isinstance(value, float):
                click.echo(f"{metric_name:<20} {value:.4f}")
            else:
                click.echo(f"{metric_name:<20} {value}")
        click.echo("-" * 40)
    else:
        # JSON format output
        json_output = json.dumps(metrics)
        if output:
            # Write to file
            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                output_path.write_text(json_output, encoding="utf-8")
                click.echo(f"Metrics written to {output_path}")
            except Exception as e:
                raise click.ClickException(f"Failed to write output: {e}")
        else:
            # Print to stdout
            click.echo(json_output)


@cli.command(name="best-graph")
@click.option(
    "--input",
    "-i",
    required=True,
    type=click.Path(exists=True),
    help="Path to PDG file (GraphML format).",
)
@click.option(
    "--output",
    "-o",
    required=True,
    type=click.Path(),
    help="Output directory for DAG and metadata files.",
)
@click.option(
    "--threshold",
    "-t",
    default=0.0,
    type=float,
    help="Minimum edge probability threshold (default: 0.0).",
)
def best_graph_cmd(
    input: str,
    output: str,
    threshold: float,
) -> None:
    """
    Extract optimal DAG from a PDG using greedy algorithm.

    Reads a Probabilistic Dependency Graph (PDG) and extracts the best
    DAG by greedily selecting high-probability edges while avoiding
    cycles. Undirected probability is split equally between forward
    and backward directions.

    For direction ties, alphabetical ordering is used (source -> target
    where source < target).

    Creates output directory containing dag.graphml and _meta.json.

    Example:
        causaliq-analysis best-graph -i merged.graphml -o results/optimal

        causaliq-analysis best-graph -i merged.graphml -o results/optimal \\
            --threshold=0.5
    """
    import json

    from causaliq_analysis.workflow_action import AnalysisActionProvider

    # Execute action
    action = AnalysisActionProvider()
    try:
        status, metadata, objects = action.run(
            "best_graph",
            {"input": input, "threshold": threshold},
            mode="run",
        )
    except Exception as e:
        raise click.ClickException(str(e))

    if status != "success":
        raise click.ClickException(f"Action failed: {metadata}")

    # Find DAG object
    dag_obj = next((o for o in objects if o["type"] == "dag"), None)
    if dag_obj is None:
        raise click.ClickException("No DAG object returned by action")

    # Create output directory and write files
    output_dir = Path(output)
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        raise click.ClickException(f"Failed to create output directory: {e}")

    # Write DAG file
    dag_path = output_dir / "dag.graphml"
    try:
        dag_path.write_text(dag_obj["content"], encoding="utf-8")
    except Exception as e:
        raise click.ClickException(f"Failed to write output: {e}")

    # Write metadata file
    meta_path = output_dir / "_meta.json"
    meta_data = {
        "metadata": {"causaliq-analysis": {"best_graph": metadata}},
        "objects": {
            "dag": {
                "format": dag_obj["format"],
                "action": dag_obj["action"],
            }
        },
    }
    try:
        meta_path.write_text(json.dumps(meta_data, indent=2), encoding="utf-8")
    except Exception as e:
        raise click.ClickException(f"Failed to write metadata: {e}")

    click.echo(f"Optimal DAG written to {dag_path}")
    click.echo(f"Metadata written to {meta_path}")


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
    multiple=True,
    callback=single_value_callback,
    required=True,
    help="Output path: CSV file or '-' for terminal output.",
)
@click.option(
    "--filter",
    "-f",
    "filter_expr",
    multiple=True,
    callback=single_value_callback,
    default=(),
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

                    # Pre-resolve random() in filter
                    resolved_filter = filter_expr
                    extra_names: Dict[str, Any] = {}
                    if filter_expr and "random(" in filter_expr:
                        from causaliq_core.utils import (
                            resolve_random_calls,
                        )

                        _meta = []
                        for _ei in entries:
                            _fe = cache.get(_ei["matrix_values"])
                            if _fe is not None:
                                _meta.append(_flatten_metadata(_fe.metadata))
                        resolved_filter, extra_names = resolve_random_calls(
                            filter_expr, _meta
                        )

                    for entry_info in entries:
                        entry = cache.get(entry_info["matrix_values"])
                        if entry is None:  # pragma: no cover
                            continue

                        # Flatten metadata for access
                        flat_meta = _flatten_metadata(entry.metadata)

                        # Apply filter if specified
                        if resolved_filter:
                            try:
                                from causaliq_core.utils import evaluate_filter

                                if not evaluate_filter(
                                    resolved_filter,
                                    {**flat_meta, **extra_names},
                                ):
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

                # Pre-resolve random() in filter for JSON
                resolved_filter_j = filter_expr
                extra_names_j: Dict[str, Any] = {}
                if filter_expr and "random(" in filter_expr:
                    from causaliq_core.utils import (
                        resolve_random_calls,
                    )

                    _all = []
                    for _r in records:
                        if not isinstance(_r, dict):
                            continue
                        if "metadata" in _r and isinstance(
                            _r["metadata"], dict
                        ):
                            _all.append(_flatten_metadata(_r["metadata"]))
                        else:
                            _all.append(_r)
                    resolved_filter_j, extra_names_j = resolve_random_calls(
                        filter_expr, _all
                    )

                for record in records:
                    if not isinstance(record, dict):
                        continue

                    # Check if this is a _meta.json format (has metadata key
                    # with provider/action structure)
                    if "metadata" in record and isinstance(
                        record["metadata"], dict
                    ):
                        # Flatten metadata like we do for cache entries
                        search_data = _flatten_metadata(record["metadata"])
                    else:
                        search_data = record

                    # Apply filter if specified
                    if resolved_filter_j:
                        try:
                            from causaliq_core.utils import evaluate_filter

                            if not evaluate_filter(
                                resolved_filter_j,
                                {**search_data, **extra_names_j},
                            ):
                                continue
                        except Exception:
                            continue

                    # Extract metric values
                    for field in unique_fields:
                        value = _get_nested_value(search_data, field)
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
