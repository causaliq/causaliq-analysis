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
            result[field] = trace.context[field]

    return result


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

    # Write to StringIO buffer
    buffer = StringIO()
    graphml.write(trace.result, buffer, graph_id=graph_id)
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
    seeds: Optional[Tuple[int, ...]] = None,
) -> Dict[str, Trace]:
    """Filter traces by sample size and seeds.

    Args:
        traces: Dictionary of traces to filter.
        sample_size: If provided, only include traces with this N value.
        seeds: If provided, only include traces with seed in this tuple.

    Returns:
        Filtered dictionary of traces.
    """
    filtered: Dict[str, Trace] = {}

    for trace_id, trace in traces.items():
        # Filter by sample_size
        if sample_size is not None:
            trace_n = trace.context.get("N")
            if trace_n != sample_size:
                continue

        # Filter by seeds (extract seed from trace_id)
        if seeds:
            parts = trace_id.split("_")
            seed_found = False
            for part in parts:
                try:
                    seed = int(part)
                    if seed in seeds:
                        seed_found = True
                        break
                except ValueError:
                    continue
            if not seed_found:
                continue

        filtered[trace_id] = trace

    return filtered


def run_migrate_trace(
    partial_id: str,
    root_dir: str,
    sample_size: Optional[int] = None,
    seeds: Optional[Tuple[int, ...]] = None,
    log_fn: Optional[Callable[[str], None]] = None,
) -> MigrateTraceResult:
    """Core migration logic shared by CLI and workflow action.

    Reads traces from pickle files, optionally filters by sample size
    and seeds, and generates GraphML + metadata content for each trace.
    Graphs are exported as-is, preserving their original structure.

    Args:
        partial_id: Trace ID pattern (e.g., "TABU/STD/asia").
        root_dir: Root directory containing trace files.
        sample_size: If provided, only migrate traces with this N value.
        seeds: If provided, only migrate traces with seed in this tuple.
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

    def _log(msg: str) -> None:
        if log_fn:
            log_fn(msg)

    _log(f"Loading traces from {partial_id}...")

    # Load traces
    traces = Trace.read(partial_id=partial_id, root_dir=root_dir)
    if traces is None:
        raise ValueError(f"No traces found for {partial_id} in {root_dir}")

    # Filter traces
    filtered_traces = filter_traces(traces, sample_size, seeds)

    if not filtered_traces:
        raise ValueError(
            f"No traces match filters: sample_size={sample_size}, "
            f"seeds={seeds}"
        )

    _log(f"Found {len(filtered_traces)} matching traces")

    # Generate content for each trace
    graphs: List[MigratedGraph] = []
    skipped = 0

    for trace_id, trace in filtered_traces.items():
        if trace.result is None:
            _log(f"Skipping {trace_id}: no result graph")
            skipped += 1
            continue

        # Generate GraphML
        graphml_str = trace_to_graphml(trace)
        metadata = get_trace_metadata(trace)
        metadata["trace_id"] = trace_id
        metadata["graph_type"] = type(trace.result).__name__

        graphs.append(
            MigratedGraph(
                trace_id=trace_id,
                graphml=graphml_str,
                metadata=metadata,
            )
        )
        _log(f"Generated content for {trace_id}")

    _log(f"Migration complete: {len(graphs)} graphs generated")

    return MigrateTraceResult(graphs=graphs, skipped=skipped)


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

    def _log(msg: str) -> None:
        if log_fn:
            log_fn(msg)

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    output_files: List[str] = []

    for graph in result.graphs:
        # Sanitise trace_id for filename
        safe_id = graph.trace_id.replace("/", "_").replace("\\", "_")

        # Write GraphML file
        graphml_file = output_path / f"{safe_id}.graphml"
        graphml_file.write_text(graph.graphml, encoding="utf-8")

        # Write metadata file
        metadata_file = output_path / f"{safe_id}.metadata.json"
        metadata_file.write_text(
            json.dumps(graph.metadata, indent=2, default=_json_serialise),
            encoding="utf-8",
        )

        output_files.append(str(graphml_file))
        _log(f"Wrote {graph.trace_id} -> {graphml_file}")

    _log(f"Wrote {len(output_files)} files to {output_dir}")

    return output_files
