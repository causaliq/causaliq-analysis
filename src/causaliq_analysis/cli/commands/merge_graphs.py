"""The ``merge-graphs`` command."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import click

from causaliq_analysis.validation import single_value_callback

__all__ = ["merge_graphs_cmd"]


@click.command(name="merge-graphs")
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
    cpdag, obj_filter = _object_filter(object_type)
    _validate_filter(filter_expr)

    graphs, graph_metadata, has_cache_input = _read_merge_inputs(
        inputs, filter_expr, obj_filter
    )
    if not graphs:
        raise click.ClickException("No graphs found to merge")

    weights_list = _resolve_weights(
        weights, has_cache_input, graph_metadata, len(graphs)
    )
    merged = _merge_graphs(graphs, weights_list, cpdag, strategy)
    _write_merge_output(
        output,
        merged,
        len(graphs),
        object_type,
        weights,
        filter_expr,
        weights_list,
    )


def _object_filter(
    object_type: Optional[str],
) -> Tuple[bool, Optional[str]]:
    """Derive the cpdag flag and object filter from the object type.

    Args:
        object_type: Requested graph object type.

    Returns:
        Tuple of (cpdag flag, object filter).
    """
    cpdag = object_type == "cpdag"
    obj_filter = "dag" if object_type == "cpdag" else object_type
    return cpdag, obj_filter


def _validate_filter(filter_expr: Optional[str]) -> None:
    """Pre-validate the filter expression syntax.

    Args:
        filter_expr: Optional filter expression.

    Raises:
        click.ClickException: If the filter expression is invalid.
    """
    if not filter_expr:
        return

    from causaliq_analysis.validation import validate_filter_expression

    try:
        validate_filter_expression(filter_expr)
    except ValueError as e:
        raise click.ClickException(str(e))


def _read_merge_inputs(
    inputs: Tuple[str, ...],
    filter_expr: Optional[str],
    obj_filter: Optional[str],
) -> Tuple[List[Any], List[Dict[str, Any]], bool]:
    """Read graphs and metadata from every merge input.

    Args:
        inputs: Input file paths.
        filter_expr: Optional cache filter expression.
        obj_filter: Optional object type filter.

    Returns:
        Tuple of (graphs, per-graph metadata, has cache input).
    """
    graphs: List[Any] = []
    graph_metadata: List[Dict[str, Any]] = []
    has_cache_input = False

    for input_path in inputs:
        if input_path.lower().endswith(".db"):
            has_cache_input = True
            _read_cache_input(
                input_path,
                filter_expr,
                obj_filter,
                graphs,
                graph_metadata,
            )
        else:
            _read_graphml_input(input_path, graphs, graph_metadata)

    return graphs, graph_metadata, has_cache_input


def _read_graphml_input(
    input_path: str,
    graphs: List[Any],
    graph_metadata: List[Dict[str, Any]],
) -> None:
    """Read a GraphML input file.

    Args:
        input_path: Input GraphML path.
        graphs: Graph list to append to.
        graph_metadata: Metadata list to append to.

    Raises:
        click.ClickException: If the input cannot be read.
    """
    from causaliq_core.graph.io import graphml

    try:
        graph = graphml.read(input_path)
        graphs.append(graph)
        graph_metadata.append({})  # Empty metadata for file inputs
    except Exception as e:
        raise click.ClickException(f"Failed to read {input_path}: {e}")


def _read_cache_input(
    input_path: str,
    filter_expr: Optional[str],
    obj_filter: Optional[str],
    graphs: List[Any],
    graph_metadata: List[Dict[str, Any]],
) -> None:
    """Read graphs from a workflow cache input file.

    Args:
        input_path: Input cache (.db) path.
        filter_expr: Optional filter expression.
        obj_filter: Optional object type filter.
        graphs: Graph list to append to.
        graph_metadata: Metadata list to append to.

    Raises:
        click.ClickException: If the cache cannot be read.
    """
    try:
        from causaliq_workflow.cache import WorkflowCache
    except ImportError:
        raise click.ClickException(
            "causaliq-workflow is required for .db cache files. "
            "Install with: pip install causaliq-workflow"
        )

    try:
        with WorkflowCache(input_path) as cache:
            _read_open_cache(
                cache,
                input_path,
                filter_expr,
                obj_filter,
                graphs,
                graph_metadata,
            )
    except FileNotFoundError:
        raise click.ClickException(f"Cache file not found: {input_path}")
    except Exception as e:
        if "ClickException" in type(e).__name__:
            raise
        raise click.ClickException(
            f"Failed to read from cache '{input_path}': {e}"
        )


def _read_open_cache(
    cache: Any,
    input_path: str,
    filter_expr: Optional[str],
    obj_filter: Optional[str],
    graphs: List[Any],
    graph_metadata: List[Dict[str, Any]],
) -> None:
    """Read graphs from every entry of an open workflow cache.

    Args:
        cache: Open workflow cache.
        input_path: Cache path, used in log messages.
        filter_expr: Optional filter expression.
        obj_filter: Optional object type filter.
        graphs: Graph list to append to.
        graph_metadata: Metadata list to append to.
    """
    entries = cache.list_entries()
    click.echo(f"Reading {len(entries)} entries from {input_path}")

    resolved_filter, extra_names = _resolve_cache_filter(
        entries, cache, filter_expr
    )
    filtered_count = 0
    for entry_info in entries:
        filtered_count += _read_cache_entry(
            entry_info,
            cache,
            resolved_filter,
            extra_names,
            obj_filter,
            graphs,
            graph_metadata,
        )

    if filter_expr and filtered_count > 0:
        click.echo(f"  Filtered out {filtered_count} entries")


def _read_cache_entry(
    entry_info: Dict[str, Any],
    cache: Any,
    resolved_filter: Optional[str],
    extra_names: Dict[str, Any],
    obj_filter: Optional[str],
    graphs: List[Any],
    graph_metadata: List[Dict[str, Any]],
) -> int:
    """Read graphs from a single cache entry.

    Args:
        entry_info: Entry info from the cache scan.
        cache: Open workflow cache.
        resolved_filter: Resolved filter expression.
        extra_names: Extra filter names from random() resolution.
        obj_filter: Optional object type filter.
        graphs: Graph list to append to.
        graph_metadata: Metadata list to append to.

    Returns:
        1 when the entry was filtered out, otherwise 0.
    """
    matrix_values = entry_info.get("matrix_values", {})
    entry = cache.get(matrix_values)
    if entry is None:
        return 0

    # Get metadata for filtering and weighting
    meta = dict(entry.metadata)
    if not _is_included(meta, resolved_filter, extra_names):
        return 1

    found_graphs = _append_entry_graphs(
        entry, matrix_values, meta, obj_filter, graphs, graph_metadata
    )
    if found_graphs == 0:
        click.echo(f"  Skipping {matrix_values}: no graphml objects")
    return 0


def _is_included(
    meta: Dict[str, Any],
    resolved_filter: Optional[str],
    extra_names: Dict[str, Any],
) -> bool:
    """Return True when a cache entry satisfies the resolved filter.

    Args:
        meta: Raw entry metadata.
        resolved_filter: Resolved filter expression.
        extra_names: Extra filter names from random() resolution.

    Returns:
        True when the entry should be processed.

    Raises:
        click.ClickException: If the filter evaluation fails.
    """
    if not resolved_filter:
        return True

    from causaliq_core.utils import (
        FilterExpressionError,
        evaluate_filter,
    )

    try:
        names = {**meta, **extra_names}
        return bool(evaluate_filter(resolved_filter, names))
    except FilterExpressionError as e:
        raise click.ClickException(f"Invalid filter expression: {e}")


def _append_entry_graphs(
    entry: Any,
    matrix_values: Dict[str, Any],
    meta: Dict[str, Any],
    obj_filter: Optional[str],
    graphs: List[Any],
    graph_metadata: List[Dict[str, Any]],
) -> int:
    """Append every matching GraphML object from an entry.

    Args:
        entry: Cache entry to scan.
        matrix_values: Entry matrix values, used in error messages.
        meta: Entry metadata to record per graph.
        obj_filter: Optional object type filter.
        graphs: Graph list to append to.
        graph_metadata: Metadata list to append to.

    Returns:
        Number of graphs found in the entry.
    """
    found = 0
    for obj_type in entry.object_types():
        obj = _graphml_object(entry, obj_type, obj_filter)
        if obj is None:
            continue
        graphs.append(_parse_cache_object(obj, obj_type, matrix_values))
        graph_metadata.append(meta)
        found += 1
    return found


def _graphml_object(
    entry: Any,
    obj_type: str,
    obj_filter: Optional[str],
) -> Any:
    """Return the entry's GraphML object for an object type, if any.

    Args:
        entry: Cache entry to inspect.
        obj_type: Object type name.
        obj_filter: Optional object type filter.

    Returns:
        The GraphML object, or None when it should be skipped.
    """
    if obj_filter is not None and obj_type != obj_filter:
        return None
    obj = entry.get_object(obj_type)
    if obj is None or obj.format != "graphml":
        return None
    return obj


def _parse_cache_object(
    obj: Any,
    obj_type: str,
    matrix_values: Dict[str, Any],
) -> Any:
    """Read one GraphML cache object into a graph.

    Args:
        obj: Cache object holding GraphML content.
        obj_type: Object type name.
        matrix_values: Entry matrix values, used in error messages.

    Returns:
        Parsed graph.

    Raises:
        click.ClickException: If the object cannot be parsed.
    """
    from io import StringIO

    from causaliq_core.graph.io import graphml

    try:
        return graphml.read(StringIO(obj.content))
    except Exception as e:
        raise click.ClickException(
            f"Failed to parse graph '{obj_type}' " f"from {matrix_values}: {e}"
        )


def _resolve_cache_filter(
    entries: List[Dict[str, Any]],
    cache: Any,
    filter_expr: Optional[str],
) -> Tuple[Optional[str], Dict[str, Any]]:
    """Pre-resolve random() calls in the cache filter expression.

    Args:
        entries: Cache entry infos to inspect.
        cache: Open workflow cache.
        filter_expr: Filter expression, possibly with random() calls.

    Returns:
        Tuple of (resolved filter expression, extra names).
    """
    if not filter_expr or "random(" not in filter_expr:
        return filter_expr, {}

    from causaliq_core.utils import resolve_random_calls

    metadata = []
    for entry_info in entries:
        entry = cache.get(entry_info.get("matrix_values", {}))
        if entry is not None:
            metadata.append(dict(entry.metadata))
    return resolve_random_calls(filter_expr, metadata)


def _resolve_weights(
    weights: Optional[str],
    has_cache_input: bool,
    graph_metadata: List[Dict[str, Any]],
    num_graphs: int,
) -> Optional[List[float]]:
    """Compute normalised graph weights from a weights file.

    Args:
        weights: Optional weights JSON file path.
        has_cache_input: Whether any input was a cache file.
        graph_metadata: Per-graph metadata.
        num_graphs: Number of graphs being merged.

    Returns:
        Normalised weights, or None when no weights file was given.

    Raises:
        click.ClickException: If the weights cannot be applied.
    """
    if not weights:
        return None
    if not has_cache_input:
        raise click.ClickException(
            "Metadata-driven weights (--weights) require .db cache input"
        )
    return _compute_weights(weights, graph_metadata, num_graphs)


def _compute_weights(
    weights: str,
    graph_metadata: List[Dict[str, Any]],
    num_graphs: int,
) -> List[float]:
    """Load a weights file and normalise the resulting weights.

    Args:
        weights: Weights JSON file path.
        graph_metadata: Per-graph metadata.
        num_graphs: Number of graphs being merged.

    Returns:
        Normalised weights.

    Raises:
        click.ClickException: If the weights file is invalid.
    """
    from causaliq_core.utils import (
        WeightSpecError,
        compute_weight,
        validate_weight_spec,
    )

    try:
        with open(weights, "r", encoding="utf-8") as f:
            weight_spec = json.load(f)

        validate_weight_spec(weight_spec)

        # Compute raw weights
        raw_weights = [
            compute_weight(meta, weight_spec) for meta in graph_metadata
        ]

        return _normalise_weights(raw_weights, num_graphs, weights)

    except json.JSONDecodeError as e:
        raise click.ClickException(f"Invalid weights JSON file: {e}")
    except WeightSpecError as e:
        raise click.ClickException(f"Invalid weight specification: {e}")
    except Exception as e:
        raise click.ClickException(f"Failed to load weights file: {e}")


def _normalise_weights(
    raw_weights: List[float],
    num_graphs: int,
    weights: str,
) -> List[float]:
    """Normalise raw weights so that they sum to 1.0.

    Args:
        raw_weights: Unnormalised weight per graph.
        num_graphs: Number of graphs being merged.
        weights: Weights file path, used in the log message.

    Returns:
        List of normalised weights.
    """
    total = sum(raw_weights)
    if total > 0:
        weights_list = [w / total for w in raw_weights]
    else:
        weights_list = [1.0 / num_graphs] * num_graphs

    click.echo(f"Applied metadata-driven weights from {weights}")
    return weights_list


def _merge_graphs(
    graphs: List[Any],
    weights_list: Optional[List[float]],
    cpdag: bool,
    strategy: str,
) -> Any:
    """Merge graphs into a single PDG.

    Args:
        graphs: Graphs to merge.
        weights_list: Optional per-graph weights.
        cpdag: Whether to merge CPDAGs.
        strategy: Merge strategy.

    Returns:
        Merged PDG.

    Raises:
        click.ClickException: If merging fails.
    """
    from causaliq_analysis.merge import merge_graphs

    try:
        return merge_graphs(
            graphs,
            weights=weights_list,
            cpdag=cpdag,
            strategy=strategy,
        )
    except (TypeError, ValueError) as e:
        raise click.ClickException(f"Merge failed: {e}")


def _write_merge_output(
    output: str,
    merged: Any,
    num_graphs: int,
    object_type: Optional[str],
    weights: Optional[str],
    filter_expr: Optional[str],
    weights_list: Optional[List[float]],
) -> None:
    """Write the merged PDG and its metadata to the output directory.

    Args:
        output: Output directory path.
        merged: Merged PDG.
        num_graphs: Number of merged graphs.
        object_type: Requested graph object type.
        weights: Weights file path, if any.
        filter_expr: Filter expression, if any.
        weights_list: Applied weights, if any.
    """
    output_dir = Path(output)
    output_dir.mkdir(parents=True, exist_ok=True)

    _write_pdg(output_dir, merged)
    _write_merge_metadata(
        output_dir,
        num_graphs,
        object_type,
        weights,
        filter_expr,
        weights_list,
    )

    click.echo(f"Merged {num_graphs} graphs to {output_dir}")


def _write_pdg(output_dir: Path, merged: Any) -> None:
    """Write the merged PDG to a GraphML file.

    Args:
        output_dir: Output directory.
        merged: Merged PDG.

    Raises:
        click.ClickException: If the PDG cannot be written.
    """
    from causaliq_core.graph.io import graphml

    pdg_path = output_dir / "pdg.graphml"
    try:
        with open(pdg_path, "w", encoding="utf-8") as f:
            graphml.write_pdg(merged, f)
    except Exception as e:
        raise click.ClickException(f"Failed to write PDG: {e}")


def _write_merge_metadata(
    output_dir: Path,
    num_graphs: int,
    object_type: Optional[str],
    weights: Optional[str],
    filter_expr: Optional[str],
    weights_list: Optional[List[float]],
) -> None:
    """Write merge metadata to a JSON file.

    Args:
        output_dir: Output directory.
        num_graphs: Number of merged graphs.
        object_type: Requested graph object type.
        weights: Weights file path, if any.
        filter_expr: Filter expression, if any.
        weights_list: Applied weights, if any.

    Raises:
        click.ClickException: If the metadata cannot be written.
    """
    meta_path = output_dir / "_meta.json"

    # Write metadata
    meta_data: Dict[str, Any] = {
        "num_graphs": num_graphs,
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
