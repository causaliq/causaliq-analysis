"""
Migration utilities for converting legacy Trace objects to graphs.

This module provides functions to extract graphs and metadata from legacy
structure learning Trace objects, enabling migration to the modern GraphML
interchange format used by causaliq workflows.

Key functions:
- get_trace_metadata: Extract key metadata from a Trace
- trace_to_dag: Extract the result graph as a DAG
- trace_to_pdag: Convert the result graph to a PDAG (CPDAG)
- trace_to_graphml: Convert the result graph to GraphML string
- run_migrate_trace: Core migration logic for CLI and workflow action
"""

import json
from dataclasses import dataclass
from enum import Enum
from io import StringIO
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from causaliq_core.graph import DAG, PDAG, dag_to_pdag
from causaliq_core.graph.io import graphml

from causaliq_analysis.trace import Trace

# Metadata fields to extract from Trace.context
_METADATA_FIELDS = [
    "id",
    "algorithm",
    "params",
    "N",
    "score",
    "in",
    "software_version",
]

# Variable name corrections for known typos in source datasets.
# These corrections are applied during trace migration to ensure
# consistency across the CausalIQ ecosystem.
# Note: HTshotOnTarget was misspelt in the original source (Constantinou 2018).
# Note: DIA_HadDiahorrea was misspelt in the original source.
_VARIABLE_NAME_CORRECTIONS: Dict[str, str] = {
    "HTshotOnTarget": "HTshotsOnTarget",
    "DIA_HadDiahorrea": "DIA_HadDiarrhoea",
}


def _apply_name_corrections(
    graph: Any,
    corrections: Dict[str, str] = _VARIABLE_NAME_CORRECTIONS,
) -> Any:
    """Apply variable name corrections to a graph.

    Creates a copy of the graph with corrected variable names. Only
    applies corrections for nodes that exist in the graph and have
    entries in the corrections mapping.

    Args:
        graph: DAG or PDAG graph object with a rename() method.
        corrections: Mapping of incorrect names to corrected names.

    Returns:
        Graph with corrected names (original if no corrections needed).
    """
    # Build full name map (required by SDG.rename)
    nodes_to_correct = set(graph.nodes) & set(corrections.keys())
    if not nodes_to_correct:
        return graph  # No corrections needed

    # Create full map: identity for unchanged nodes, correction for others
    name_map = {n: corrections.get(n, n) for n in graph.nodes}
    graph.rename(name_map)
    return graph


def _json_serialise(obj: Any) -> Any:
    """Custom JSON serialiser for metadata objects.

    Handles common non-JSON-serializable types found in trace metadata,
    converting them to meaningful string representations.

    Args:
        obj: Object to serialise.

    Returns:
        JSON-serializable representation of the object.
    """
    # Handle Enum types
    if isinstance(obj, Enum):
        return obj.name

    # Handle Prefer-style objects with args tuple (e.g., Prefer('none'))
    if hasattr(obj, "args") and isinstance(obj.args, tuple) and obj.args:
        return obj.args[0]

    # Handle objects with a 'name' attribute (common pattern)
    if hasattr(obj, "name") and isinstance(obj.name, str):
        return obj.name

    # Handle objects with a 'value' attribute
    if hasattr(obj, "value"):
        return obj.value

    # Fallback to string representation
    return str(obj)


def get_trace_metadata(trace: Trace) -> Dict[str, Any]:
    """Extract key metadata from a Trace object.

    Extracts the important metadata fields from a Trace's context,
    suitable for inclusion when migrating to workflow cache.

    Args:
        trace: The Trace object to extract metadata from.

    Returns:
        Dictionary containing extracted metadata fields:
        - id: Trace identifier
        - algorithm: Structure learning algorithm (e.g., "TABU", "HC")
        - params: Algorithm parameters dictionary
        - N: Sample size used for learning
        - score: Final score achieved
        - in: Input network name (if present)
        - software_version: Version of software that created trace

    Raises:
        TypeError: If trace is not a Trace object.

    Example:
        >>> trace = Trace.read("TABU/STD/asia", "experiments")["N1000"]
        >>> metadata = get_trace_metadata(trace)
        >>> metadata["algorithm"]
        'TABU'
        >>> metadata["N"]
        1000
    """
    if not isinstance(trace, Trace):
        raise TypeError("get_trace_metadata() requires a Trace object")
    result: Dict[str, Any] = {}
    for field in _METADATA_FIELDS:
        if field in trace.context:
            result[field] = _metadata_value(field, trace.context[field])
    return result


def _metadata_value(field: str, value: Any) -> Any:
    """Return a metadata value, serialising param dictionaries.

    Args:
        field: Metadata field name.
        value: Raw value from the trace context.

    Returns:
        The value, with param dictionaries serialised to plain values.
    """
    if field == "params" and isinstance(value, dict):
        return {k: _json_serialise(v) for k, v in value.items()}
    return value


def trace_to_dag(trace: Trace) -> DAG:
    """Extract the result graph from a Trace as a DAG.

    Returns the learnt graph from the trace. The graph must be a DAG;
    if it is a PDAG, use trace_to_pdag instead or extend_pdag first.

    Args:
        trace: The Trace object containing the learnt graph.

    Returns:
        The learnt graph as a DAG object.

    Raises:
        TypeError: If trace is not a Trace object.
        ValueError: If trace has no result graph.
        TypeError: If result is not a DAG (e.g., is a PDAG).

    Example:
        >>> trace = Trace.read("TABU/STD/asia", "experiments")["N1000"]
        >>> dag = trace_to_dag(trace)
        >>> len(dag.nodes)
        8
    """
    if not isinstance(trace, Trace):
        raise TypeError("trace_to_dag() requires a Trace object")

    if trace.result is None:
        raise ValueError("Trace has no result graph")

    if not isinstance(trace.result, DAG):
        raise TypeError(
            f"Trace result is not a DAG, got {type(trace.result).__name__}"
        )

    return trace.result


def trace_to_pdag(trace: Trace) -> PDAG:
    """Convert the result graph from a Trace to a PDAG (CPDAG).

    If the trace result is a DAG, it is converted to its CPDAG
    (represented as PDAG). If already a PDAG, returns as-is.

    Args:
        trace: The Trace object containing the learnt graph.

    Returns:
        The learnt graph as a PDAG object (CPDAG representation).

    Raises:
        TypeError: If trace is not a Trace object.
        ValueError: If trace has no result graph.

    Example:
        >>> trace = Trace.read("TABU/STD/asia", "experiments")["N1000"]
        >>> pdag = trace_to_pdag(trace)
        >>> pdag.is_partially_directed
        True
    """
    if not isinstance(trace, Trace):
        raise TypeError("trace_to_pdag() requires a Trace object")

    if trace.result is None:
        raise ValueError("Trace has no result graph")

    # If already a PDAG (but not a DAG), return as-is
    # Note: DAG is a subclass of PDAG, so check DAG first
    if isinstance(trace.result, DAG):
        return dag_to_pdag(trace.result)
    elif isinstance(trace.result, PDAG):
        return trace.result
    else:
        raise TypeError(
            f"Trace result is not a DAG or PDAG, "
            f"got {type(trace.result).__name__}"
        )


def _get_network_name(trace: Trace) -> str:
    """Extract network name from trace metadata.

    Attempts to extract the network name from trace context, falling back
    to "G" if not available.

    Args:
        trace: The Trace object.

    Returns:
        Network name string.
    """
    # Try to get from 'in' field (e.g., "experiments/bn/asia.dsc" -> "asia")
    in_path = trace.context.get("in")
    if in_path:
        return str(Path(in_path).stem)

    # Try to get from 'id' field (e.g., "TABU/STD/asia/N1000" -> "asia")
    trace_id = trace.context.get("id")
    if trace_id:
        parts = str(trace_id).split("/")
        if len(parts) >= 2:
            # Network name is second-to-last part (before N1000_0 etc)
            return parts[-2]

    return "G"


def trace_to_graphml(trace: Trace, graph_id: Optional[str] = None) -> str:
    """Convert the result graph from a Trace to GraphML string.

    Converts the learnt graph from a Trace to GraphML format, suitable
    for storage in workflow caches or interchange with other tools.
    The graph is exported as-is, preserving directed and undirected edges.
    Known variable name typos are corrected during conversion.

    Args:
        trace: The Trace object containing the learnt graph.
        graph_id: Optional ID for the graph element. If None, extracts
            network name from trace metadata.

    Returns:
        GraphML XML string representing the graph.

    Raises:
        TypeError: If trace is not a Trace object.
        ValueError: If trace has no result graph.

    Example:
        >>> trace = Trace.read("TABU/STD/asia", "experiments")["N1000"]
        >>> graphml_str = trace_to_graphml(trace)
        >>> '<graphml' in graphml_str
        True
    """
    if not isinstance(trace, Trace):
        raise TypeError("trace_to_graphml() requires a Trace object")

    if trace.result is None:
        raise ValueError("Trace has no result graph")

    # Determine graph ID
    if graph_id is None:
        graph_id = _get_network_name(trace)

    # Apply variable name corrections (e.g., typos in source datasets)
    graph = _apply_name_corrections(trace.result)

    # Write to StringIO buffer
    buffer = StringIO()
    graphml.write(graph, buffer, graph_id=graph_id)
    return buffer.getvalue()


def migrate_traces(
    traces: Dict[str, Trace],
) -> List[Tuple[str, str, Dict[str, Any]]]:
    """Migrate multiple traces to GraphML format with metadata.

    Processes a dictionary of traces (as returned by Trace.read) and
    returns a list of (trace_id, graphml_string, metadata) tuples.
    Graphs are exported as-is, preserving their original structure.

    Args:
        traces: Dictionary mapping trace IDs to Trace objects.

    Returns:
        List of tuples: (trace_id, graphml_string, metadata_dict).
        Traces without result graphs are skipped.

    Raises:
        TypeError: If traces is not a dictionary of Trace objects.

    Example:
        >>> traces = Trace.read("TABU/STD/asia", "experiments")
        >>> migrated = migrate_traces(traces)
        >>> len(migrated)
        1
        >>> trace_id, graphml_str, metadata = migrated[0]
    """
    if not isinstance(traces, dict):
        raise TypeError("migrate_traces() requires a dictionary of traces")

    results: List[Tuple[str, str, Dict[str, Any]]] = []

    for trace_id, trace in traces.items():
        if not isinstance(trace, Trace):
            raise TypeError(
                f"Value for key '{trace_id}' is not a Trace object"
            )

        # Skip traces without result graphs
        if trace.result is None:
            continue

        graphml_str = trace_to_graphml(trace)
        metadata = get_trace_metadata(trace)
        metadata["trace_id"] = trace_id

        results.append((trace_id, graphml_str, metadata))

    return results


@dataclass
class MigratedGraph:
    """A single migrated graph with its content.

    Attributes:
        trace_id: Original trace identifier.
        graphml: GraphML string content.
        metadata: Metadata dictionary.
    """

    trace_id: str
    graphml: str
    metadata: Dict[str, Any]


@dataclass
class MigrateTraceResult:
    """Result of migrate_trace operation.

    Attributes:
        graphs: List of migrated graphs with content.
        skipped: Number of traces skipped (no result graph).
    """

    graphs: List[MigratedGraph]
    skipped: int = 0

    @property
    def num_graphs(self) -> int:
        """Number of graphs migrated."""
        return len(self.graphs)


def filter_traces(
    traces: Dict[str, Trace],
    sample_size: Optional[int] = None,
    seed: Optional[Tuple[int, ...]] = None,
) -> Dict[str, Trace]:
    """Filter traces by sample size and seed.

    Args:
        traces: Dictionary of traces to filter.
        sample_size: If provided, only include traces with this N value.
        seed: If provided, only include traces with seed in this tuple.

    Returns:
        Filtered dictionary of traces.
    """
    filtered: Dict[str, Trace] = {}
    for trace_id, trace in traces.items():
        if not _matches_sample_size(trace, sample_size):
            continue
        if not _matches_seed(trace_id, seed):
            continue
        filtered[trace_id] = trace
    return filtered


def _matches_sample_size(trace: Trace, sample_size: Optional[int]) -> bool:
    """Return True when a trace satisfies the sample-size filter.

    Args:
        trace: Trace to test.
        sample_size: Required sample size, or None for no filter.

    Returns:
        True when the trace matches the filter.
    """
    if sample_size is None:
        return True
    return trace.context.get("N") == sample_size


def _matches_seed(trace_id: str, seed: Optional[Tuple[int, ...]]) -> bool:
    """Return True when a trace id contains an accepted seed.

    Args:
        trace_id: Trace identifier to search.
        seed: Seeds to accept, or None/empty for no filter.

    Returns:
        True when the trace matches the filter.
    """
    if not seed:
        return True
    return any(_matches_seed_part(part, seed) for part in trace_id.split("_"))


def _matches_seed_part(part: str, seed: Tuple[int, ...]) -> bool:
    """Return True when a trace id part parses to an accepted seed.

    Args:
        part: One underscore-delimited part of a trace id.
        seed: Seeds to accept.

    Returns:
        True when the part is an integer in the seed set.
    """
    try:
        return int(part) in seed
    except ValueError:
        return False


def run_migrate_trace(
    partial_id: str,
    root_dir: str,
    sample_size: Optional[int] = None,
    seed: Optional[Tuple[int, ...]] = None,
    log_fn: Optional[Callable[[str], None]] = None,
) -> MigrateTraceResult:
    """Core migration logic shared by CLI and workflow action.

    Reads traces from pickle files, optionally filters by sample size
    and seed, and generates GraphML + metadata content for each trace.
    Graphs are exported as-is, preserving their original structure.

    Args:
        partial_id: Trace ID pattern (e.g., "TABU/STD/asia").
        root_dir: Root directory containing trace files.
        sample_size: If provided, only migrate traces with this N value.
        seed: If provided, only migrate traces with seed in this tuple.
        log_fn: Optional callback for logging messages.

    Returns:
        MigrateTraceResult with generated content.

    Raises:
        ValueError: If no traces found or no traces match filters.

    Example:
        >>> result = run_migrate_trace(
        ...     partial_id="TABU/STD/asia",
        ...     root_dir="experiments",
        ...     sample_size=1000,
        ... )
        >>> result.num_graphs
        10
    """

    _log = _make_logger(log_fn)
    _log(f"Loading traces from {partial_id}...")
    traces = Trace.read(partial_id=partial_id, root_dir=root_dir)
    if traces is None:
        raise ValueError(f"No traces found for {partial_id} in {root_dir}")
    filtered_traces = filter_traces(traces, sample_size, seed)
    if not filtered_traces:
        _log(
            f"No traces match filters: "
            f"sample_size={sample_size}, seed={seed} "
            f"- skipping"
        )
        return MigrateTraceResult(graphs=[], skipped=0)
    _log(f"Found {len(filtered_traces)} matching traces")
    result = _build_migrate_result(filtered_traces, _log)
    _log(f"Migration complete: {len(result.graphs)} graphs generated")
    return result


def _no_log(message: str) -> None:
    """Discard a log message when no callback is supplied."""


def _make_logger(
    log_fn: Optional[Callable[[str], None]],
) -> Callable[[str], None]:
    """Return a logging callable that is a no-op when none is supplied.

    Args:
        log_fn: Optional logging callback.

    Returns:
        A callable that logs when log_fn is provided, else does nothing.
    """
    if log_fn is None:
        return _no_log
    return log_fn


def _build_migrate_result(
    filtered_traces: Dict[str, Trace],
    log_fn: Callable[[str], None],
) -> MigrateTraceResult:
    """Generate migrated graphs for each filtered trace.

    Args:
        filtered_traces: Traces to migrate.
        log_fn: Logging callback.

    Returns:
        Migration result with the generated graphs.
    """
    graphs: List[MigratedGraph] = []
    skipped = 0
    for trace_id, trace in filtered_traces.items():
        migrated = _migrate_single_trace(trace_id, trace, log_fn)
        if migrated is None:
            skipped += 1
            continue
        graphs.append(migrated)
        log_fn(f"Generated content for {trace_id}")
    return MigrateTraceResult(graphs=graphs, skipped=skipped)


def _migrate_single_trace(
    trace_id: str,
    trace: Trace,
    log_fn: Callable[[str], None],
) -> Optional[MigratedGraph]:
    """Generate the migrated graph for one trace, or None to skip it.

    Args:
        trace_id: Trace identifier.
        trace: Trace to migrate.
        log_fn: Logging callback.

    Returns:
        The migrated graph, or None when the trace has no result graph.
    """
    if trace.result is None:
        log_fn(f"Skipping {trace_id}: no result graph")
        return None
    metadata = get_trace_metadata(trace)
    metadata["trace_id"] = trace_id
    metadata["graph_type"] = type(trace.result).__name__
    return MigratedGraph(
        trace_id=trace_id,
        graphml=trace_to_graphml(trace),
        metadata=metadata,
    )


def write_migrate_result(
    result: MigrateTraceResult,
    output_dir: str,
    log_fn: Optional[Callable[[str], None]] = None,
) -> List[str]:
    """Write migration result to files in output directory.

    Used by CLI to write GraphML and metadata files to disk.

    Args:
        result: Migration result containing generated content.
        output_dir: Directory to write output files.
        log_fn: Optional callback for logging messages.

    Returns:
        List of written file paths.

    Example:
        >>> result = run_migrate_trace("TABU/STD/asia", "experiments")
        >>> files = write_migrate_result(result, "output/asia")
        >>> len(files)
        10
    """

    _log = _make_logger(log_fn)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    output_files: List[str] = []
    for graph in result.graphs:
        graphml_file = _write_graph_files(graph, output_path)
        output_files.append(str(graphml_file))
        _log(f"Wrote {graph.trace_id} -> {graphml_file}")
    _log(f"Wrote {len(output_files)} files to {output_dir}")
    return output_files


def _write_graph_files(graph: MigratedGraph, output_path: Path) -> Path:
    """Write the GraphML and metadata files for one migrated graph.

    Args:
        graph: Migrated graph to write.
        output_path: Directory to write into.

    Returns:
        Path of the written GraphML file.
    """
    safe_id = graph.trace_id.replace("/", "_").replace("\\", "_")
    graphml_file = output_path / f"{safe_id}.graphml"
    graphml_file.write_text(graph.graphml, encoding="utf-8")
    metadata_file = output_path / f"{safe_id}.metadata.json"
    metadata_file.write_text(
        json.dumps(graph.metadata, indent=2, default=_json_serialise),
        encoding="utf-8",
    )
    return graphml_file
