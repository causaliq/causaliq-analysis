"""The ``evaluate-graph`` command."""

import json
from pathlib import Path
from typing import Any, Dict, Optional, Set, Tuple

import click
from causaliq_core.graph import DAG, PDAG, PDG, convert

from causaliq_analysis import graph_io, metrics
from causaliq_analysis.metrics import EDGE_METRICS

__all__ = ["SUPPORTED_METRICS", "evaluate_graph_cmd"]

# Supported metrics for evaluate-graph command
SUPPORTED_METRICS = frozenset(
    {
        "f1",
        "shd",
        "precision",
        "recall",
        "edge",
        "equiv.f1",
        "equiv.shd",
        "equiv.edge",
    }
)

# Metric groups used to decide which comparisons are needed
_DIRECT_METRICS = frozenset({"f1", "shd", "precision", "recall", "edge"})
_EQUIV_METRICS = frozenset({"equiv.f1", "equiv.shd", "equiv.edge"})


@click.command(name="evaluate-graph")
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
    "edge, equiv.f1, equiv.shd, equiv.edge. Can specify multiple.",
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
    class comparison (comparing CPDAGs). Graphs may be deterministic
    (DAG/PDAG/CPDAG) or PDGs whose edge probabilities are compared
    fractionally; equivalence class metrics are unavailable for PDGs.

    Supported metrics:
    - f1: F1 score from direct graph comparison
    - shd: Structural Hamming Distance from direct comparison
    - precision: Precision from direct comparison
    - recall: Recall from direct comparison
    - edge: Low-level edge counts from direct comparison (arc_matched,
      arc_reversed, edge_not_arc, arc_not_edge, edge_matched, arc_extra,
      edge_extra, arc_missing, edge_missing, missing_matched). Counts
      are fractional when either graph is a PDG.
    - equiv.f1: F1 score comparing equivalence classes (CPDAGs)
    - equiv.shd: SHD comparing equivalence classes (CPDAGs)
    - equiv.edge: Low-level edge counts comparing equivalence classes
      (CPDAGs)

    Example:
        causaliq-analysis evaluate-graph -i learned.graphml \\
            -r ground_truth.graphml -m f1 -m shd

        causaliq-analysis evaluate-graph -i learned.graphml \\
            -r ground_truth.graphml -m equiv.f1 -m equiv.shd

        causaliq-analysis evaluate-graph -i learned.graphml \\
            -r ground_truth.graphml -m edge -m equiv.edge

        causaliq-analysis evaluate-graph -i learned.graphml \\
            -r ground_truth.graphml -m f1 --format=table
    """
    metrics_to_compute = _validate_metrics(metrics_requested)
    learned_graph, reference_graph = _load_graphs(input_graph, reference)

    metrics_result: Dict[str, Any] = {}
    if _needs_direct(metrics_to_compute):
        metrics_result.update(
            _direct_metrics(
                _compare_graphs(learned_graph, reference_graph),
                metrics_to_compute,
            )
        )
    if _needs_equiv(metrics_to_compute):
        metrics_result.update(
            _equiv_metrics(learned_graph, reference_graph, metrics_to_compute)
        )

    _emit_metrics(metrics_result, output, output_format)


def _read_graph_file(path: str) -> Any:
    """Read graph from file, auto-detecting PDG and other formats.

    Args:
        path: Path to the graph file.

    Returns:
        Parsed graph (SDG/PDAG/DAG) or PDG.
    """
    return graph_io.read_graph_or_pdg_file(path)


def _to_cpdag(g: Any) -> PDAG:
    """Convert a graph to its CPDAG (equivalence class).

    Args:
        g: Graph to convert.

    Returns:
        The graph's CPDAG.

    Raises:
        ValueError: If a PDAG is not extendable to a CPDAG.
        TypeError: If the graph type cannot be converted.
    """
    if isinstance(g, DAG):
        return convert.dag_to_pdag(g)
    elif isinstance(g, PDAG):
        cpdag = convert.pdag_to_cpdag(g)
        if cpdag is None:
            raise ValueError("PDAG is not extendable to a CPDAG")
        return cpdag
    else:
        raise TypeError(f"Cannot convert {type(g).__name__} to CPDAG")


def _validate_metrics(metrics_requested: Tuple[str, ...]) -> Set[str]:
    """Validate requested metric names and return them as a set.

    Args:
        metrics_requested: Metric names passed on the command line.

    Returns:
        Set of requested metric names.

    Raises:
        click.ClickException: If any metric is not supported.
    """
    invalid = set(metrics_requested) - SUPPORTED_METRICS
    if invalid:
        raise click.ClickException(
            f"Invalid metric(s): {', '.join(sorted(invalid))}. "
            f"Supported: {', '.join(sorted(SUPPORTED_METRICS))}"
        )
    return set(metrics_requested)


def _load_graphs(input_graph: str, reference: str) -> Tuple[Any, Any]:
    """Read the learned and reference graphs.

    Args:
        input_graph: Path to the learned graph.
        reference: Path to the reference graph.

    Returns:
        Tuple of (learned graph, reference graph).

    Raises:
        click.ClickException: If either graph cannot be read.
    """
    try:
        learned_graph = _read_graph_file(input_graph)
    except Exception as e:
        raise click.ClickException(f"Failed to read learned graph: {e}")

    try:
        reference_graph = _read_graph_file(reference)
    except Exception as e:
        raise click.ClickException(f"Failed to read reference graph: {e}")

    return learned_graph, reference_graph


def _needs_direct(metrics_to_compute: Set[str]) -> bool:
    """Return True when direct comparison metrics are requested.

    Args:
        metrics_to_compute: Requested metric names.

    Returns:
        True when at least one direct metric is requested.
    """
    return bool(_DIRECT_METRICS & metrics_to_compute)


def _needs_equiv(metrics_to_compute: Set[str]) -> bool:
    """Return True when equivalence-class metrics are requested.

    Args:
        metrics_to_compute: Requested metric names.

    Returns:
        True when at least one equivalence-class metric is requested.
    """
    return bool(_EQUIV_METRICS & metrics_to_compute)


def _compare_graphs(
    learned_graph: Any,
    reference_graph: Any,
) -> Dict[str, Any]:
    """Compare two graphs, choosing the PDG or deterministic path.

    Args:
        learned_graph: Learned graph to evaluate.
        reference_graph: Reference graph.

    Returns:
        Raw comparison metrics.

    Raises:
        click.ClickException: If the comparison fails.
    """
    try:
        if isinstance(learned_graph, PDG) or isinstance(reference_graph, PDG):
            return metrics.pdg_compare(learned_graph, reference_graph)
        return metrics.pdag_compare(learned_graph, reference_graph)
    except ValueError as e:
        raise click.ClickException(f"Comparison failed: {e}")
    except TypeError as e:
        raise click.ClickException(f"Invalid graph type: {e}")


def _direct_metrics(
    raw_metrics: Dict[str, Any],
    metrics_to_compute: Set[str],
) -> Dict[str, Any]:
    """Select the requested direct comparison metrics.

    Args:
        raw_metrics: Raw comparison metrics.
        metrics_to_compute: Requested metric names.

    Returns:
        Mapping of requested direct metrics in insertion order.
    """
    metrics_out: Dict[str, Any] = {}
    if "f1" in metrics_to_compute:
        metrics_out["f1"] = raw_metrics.get("f1")
    if "shd" in metrics_to_compute:
        metrics_out["shd"] = raw_metrics.get("shd")
    if "precision" in metrics_to_compute:
        metrics_out["precision"] = raw_metrics.get("p")
    if "recall" in metrics_to_compute:
        metrics_out["recall"] = raw_metrics.get("r")
    if "edge" in metrics_to_compute:
        for name in EDGE_METRICS:
            metrics_out[name] = raw_metrics.get(name)
    return metrics_out


def _equiv_metrics(
    learned_graph: Any,
    reference_graph: Any,
    metrics_to_compute: Set[str],
) -> Dict[str, Any]:
    """Compute the requested equivalence-class metrics.

    Args:
        learned_graph: Learned graph to evaluate.
        reference_graph: Reference graph.
        metrics_to_compute: Requested metric names.

    Returns:
        Mapping of requested equivalence-class metrics.
    """
    try:
        learned_cpdag = _to_cpdag(learned_graph)
        reference_cpdag = _to_cpdag(reference_graph)
        equiv_metrics = metrics.pdag_compare(learned_cpdag, reference_cpdag)
    except (ValueError, TypeError) as e:
        click.echo(
            f"Warning: skipping equiv metrics ({e})",
            err=True,
        )
        return {}

    return _equiv_metric_subset(equiv_metrics, metrics_to_compute)


def _equiv_metric_subset(
    equiv_metrics: Dict[str, Any],
    metrics_to_compute: Set[str],
) -> Dict[str, Any]:
    """Select the requested equivalence-class metrics.

    Args:
        equiv_metrics: Raw equivalence-class metrics.
        metrics_to_compute: Requested metric names.

    Returns:
        Mapping of requested equivalence metrics in insertion order.
    """
    out: Dict[str, Any] = {}
    if "equiv.f1" in metrics_to_compute:
        out["equiv.f1"] = equiv_metrics.get("f1")
    if "equiv.shd" in metrics_to_compute:
        out["equiv.shd"] = equiv_metrics.get("shd")
    if "equiv.edge" in metrics_to_compute:
        for name in EDGE_METRICS:
            out[f"equiv.{name}"] = equiv_metrics.get(name)
    return out


def _emit_metrics(
    metrics_result: Dict[str, Any],
    output: Optional[str],
    output_format: str,
) -> None:
    """Write the computed metrics in the requested format.

    Args:
        metrics_result: Computed metrics.
        output: Output file path, or None to print to stdout.
        output_format: Either 'table' or 'json'.
    """
    if output_format == "table":
        _print_metrics_table(metrics_result)
    else:
        _write_metrics_json(metrics_result, output)


def _print_metrics_table(metrics_result: Dict[str, Any]) -> None:
    """Print metrics as a formatted table.

    Args:
        metrics_result: Computed metrics.
    """
    click.echo("\nStructural Evaluation Metrics")
    click.echo("-" * 40)
    for metric_name, value in sorted(metrics_result.items()):
        if isinstance(value, float):
            click.echo(f"{metric_name:<22} {value:.4f}")
        else:
            click.echo(f"{metric_name:<22} {value}")
    click.echo("-" * 40)


def _write_metrics_json(
    metrics_result: Dict[str, Any],
    output: Optional[str],
) -> None:
    """Write metrics as JSON either to a file or to stdout.

    Args:
        metrics_result: Computed metrics.
        output: Output file path, or None to print to stdout.
    """
    json_output = json.dumps(metrics_result)
    if output:
        _write_metrics_file(Path(output), json_output)
    else:
        click.echo(json_output)


def _write_metrics_file(output_path: Path, json_output: str) -> None:
    """Write JSON metrics to a file.

    Args:
        output_path: Destination file path.
        json_output: Serialised metrics JSON.

    Raises:
        click.ClickException: If the file cannot be written.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        output_path.write_text(json_output, encoding="utf-8")
        click.echo(f"Metrics written to {output_path}")
    except Exception as e:
        raise click.ClickException(f"Failed to write output: {e}")
