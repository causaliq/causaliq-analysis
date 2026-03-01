"""
CausalIQ Workflow Action for analysis operations.

This module implements the Action interface for causaliq-workflow integration,
enabling trace migration to be used in workflow definitions.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

# Check if workflow is available at runtime
WORKFLOW_AVAILABLE = False

# TYPE_CHECKING pattern: The if-block is only executed by type checkers (mypy),
# never at runtime. The else-block always runs at runtime. This allows type
# checkers to see the real types while providing fallback stubs when the
# optional causaliq_workflow package isn't installed.
if TYPE_CHECKING:  # pragma: no cover
    # Import types for type checking only (mypy sees these)
    from causaliq_core import (
        ActionExecutionError,
        ActionInput,
        ActionResult,
        CausalIQActionProvider,
    )
    from causaliq_workflow.logger import WorkflowLogger
    from causaliq_workflow.registry import WorkflowContext
else:
    # Runtime imports with fallback stubs (Python executes this)
    try:
        from causaliq_core import (
            ActionExecutionError,
            ActionInput,
            ActionResult,
            CausalIQActionProvider,
        )
        from causaliq_workflow.logger import WorkflowLogger
        from causaliq_workflow.registry import WorkflowContext

        WORKFLOW_AVAILABLE = True
    except ImportError:
        # Define minimal stubs for runtime when workflow not installed
        class CausalIQActionProvider:  # type: ignore[no-redef]
            pass

        class ActionExecutionError(Exception):
            pass

        # Type alias stub for ActionResult
        ActionResult = tuple  # type: ignore[misc]

        @dataclass
        class ActionInput:
            name: str
            description: str
            required: bool = False
            default: Any = None
            type_hint: str = "Any"

        class WorkflowContext:
            pass

        class WorkflowLogger:
            pass


from causaliq_analysis.migrate import run_migrate_trace  # noqa: E402
from causaliq_analysis.validation import (  # noqa: E402
    parse_sample_size,
    parse_seeds_workflow,
)


class AnalysisActionProvider(CausalIQActionProvider):
    """
    CausalIQ Analysis action provider for workflow integration.

    Supports operations on causal graphs including:
    - migrate_trace: Convert legacy Trace files to GraphML format
    - merge_graphs: Merge multiple graphs into a PDG with probabilities
    """

    # Provider metadata
    name = "causaliq-analysis"
    version = "0.3.0"
    description = "Migration and analysis of causal graph trace files"
    author = "CausalIQ"

    # Input specifications
    inputs = {
        "action": ActionInput(
            name="action",
            description=(
                "Action to perform: 'migrate_trace' or 'merge_graphs'"
            ),
            required=True,
            type_hint="str",
        ),
        # migrate_trace inputs
        "traces": ActionInput(
            name="traces",
            description=(
                "Path pattern to trace files "
                "(e.g., 'series/network.pkl.gz')"
            ),
            required=False,
            type_hint="str",
        ),
        "root_dir": ActionInput(
            name="root_dir",
            description="Root directory containing trace files",
            required=False,
            default="experiments",
            type_hint="str",
        ),
        "series": ActionInput(
            name="series",
            description="Series path (e.g., 'TABU/SAMPLE/BASE')",
            required=False,
            type_hint="str",
        ),
        "network": ActionInput(
            name="network",
            description="Network name for trace identification",
            required=False,
            type_hint="str",
        ),
        "sample_size": ActionInput(
            name="sample_size",
            description=(
                "Sample size to filter traces (int or string like '10k')"
            ),
            required=False,
            type_hint="int or str",
        ),
        "seeds": ActionInput(
            name="seeds",
            description="Seeds to include (comma-separated or list)",
            required=False,
            default="",
            type_hint="str or list",
        ),
        # merge_graphs input
        "input": ActionInput(
            name="input",
            description=(
                "List of input files (.graphml or .db). Type is detected "
                "by extension. For .db files, all graphml objects from all "
                "cache entries are read. Not required when using "
                "aggregation mode (workflow with 'aggregate' parameter)."
            ),
            required=False,
            type_hint="list[str]",
        ),
        "aggregate": ActionInput(
            name="aggregate",
            description=(
                "Workflow cache path(s) for aggregation mode. When used "
                "with a workflow matrix, entries are grouped by matrix "
                "variables and graphs are extracted from matching entries. "
                "Mutually exclusive with 'input' parameter."
            ),
            required=False,
            type_hint="str or list[str]",
        ),
        "weights": ActionInput(
            name="weights",
            description=(
                "Weights for each input graph (must sum to 1.0). "
                "If omitted, uniform weights are used."
            ),
            required=False,
            type_hint="list[float]",
        ),
        "cpdag": ActionInput(
            name="cpdag",
            description=(
                "Convert DAGs to CPDAGs before merging. "
                "Averages over equivalence classes."
            ),
            required=False,
            default=False,
            type_hint="bool",
        ),
    }

    # Output specifications
    outputs = {
        "num_graphs": "Number of graphs processed",
        "status": "Execution status",
        "skipped": "Number of traces skipped",
        "merged_pdg": "Merged PDG in GraphML format (merge_graphs)",
    }

    def run(
        self,
        action: str,
        parameters: Dict[str, Any],
        mode: str = "dry-run",
        context: Optional[WorkflowContext] = None,
        logger: Optional[WorkflowLogger] = None,
    ) -> ActionResult:
        """
        Execute the analysis action.

        Args:
            action: Action to perform ('migrate_trace' or 'merge_graphs')
            parameters: Action parameter values
            mode: Execution mode ('dry-run', 'run', 'compare')
            context: Workflow context for optimization
            logger: Optional logger for reporting

        Returns:
            Tuple of (status, metadata, objects)

        Raises:
            ActionExecutionError: If execution fails
        """
        if action == "migrate_trace":
            return self._run_migrate_trace(parameters, mode, context, logger)
        elif action == "merge_graphs":
            return self._run_merge_graphs(parameters, mode, context, logger)
        else:
            raise ActionExecutionError(
                f"Unknown action: {action}. "
                "Supported actions: migrate_trace, merge_graphs"
            )

    def _run_migrate_trace(
        self,
        parameters: Dict[str, Any],
        mode: str,
        context: Optional[WorkflowContext],
        logger: Optional[WorkflowLogger],
    ) -> ActionResult:
        """Execute trace migration to GraphML format."""
        try:
            # Extract parameters
            traces_pattern = parameters.get("traces")
            root_dir = parameters.get("root_dir", "experiments")
            series = parameters.get("series")
            network = parameters.get("network")
            sample_size_input = parameters.get("sample_size")
            seeds_input = parameters.get("seeds", "")

            # Build trace path pattern
            if traces_pattern:
                partial_id = traces_pattern.replace(".pkl.gz", "")
            elif series and network:
                partial_id = f"{series}/{network}"
            else:
                raise ActionExecutionError(
                    "Must provide either 'traces' or both 'series' and "
                    "'network'"
                )

            # Parse optional filters
            sample_size = None
            if sample_size_input is not None:
                sample_size = parse_sample_size(sample_size_input)

            seed_tuple = parse_seeds_workflow(seeds_input)

            # Dry-run mode
            if mode == "dry-run":
                if logger and logger.is_terminal_logging:
                    print(f"Would migrate traces from {partial_id}")
                return (
                    "skipped",
                    {
                        "message": "Dry-run mode",
                        "num_graphs": 0,
                    },
                    [],
                )

            # Set up logging callback
            log_fn = None
            if logger and logger.is_terminal_logging:
                log_fn = print

            # Run migration - returns content, does not write files
            result = run_migrate_trace(
                partial_id=partial_id,
                root_dir=root_dir,
                sample_size=sample_size,
                seeds=seed_tuple if seed_tuple else None,
                log_fn=log_fn,
            )

            # Build objects list for cache storage (GraphML only)
            # Per-graph metadata keyed by object name at top level
            objects = []
            metadata: Dict[str, Any] = {
                "num_graphs": result.num_graphs,
                "skipped": result.skipped,
            }

            for graph in result.graphs:
                # Sanitise trace_id for object name
                safe_id = graph.trace_id.replace("/", "_").replace("\\", "_")

                # Add GraphML object
                objects.append(
                    {
                        "type": "graphml",
                        "name": safe_id,
                        "content": graph.graphml,
                    }
                )

                # Per-graph metadata keyed by object name
                metadata[safe_id] = graph.metadata

            return (
                "success",
                metadata,
                objects,
            )

        except ValueError as e:
            raise ActionExecutionError(f"Trace migration failed: {e}") from e
        except Exception as e:
            raise ActionExecutionError(f"Trace migration failed: {e}") from e

    def _run_merge_graphs(
        self,
        parameters: Dict[str, Any],
        mode: str,
        context: Optional[WorkflowContext],
        logger: Optional[WorkflowLogger],
    ) -> ActionResult:
        """Execute graph merging to produce a PDG.

        Supports two modes of operation:

        1. **Aggregation mode**: When called from a workflow with a matrix
           definition and 'aggregate' parameter, receives pre-scanned cache
           entries via '_aggregation_entries'. Extracts graphs from these
           entries and merges them.

        2. **Direct mode**: When called from CLI or workflow without
           aggregation, reads graphs from 'inputs' file paths (.graphml or
           .db files).
        """
        from io import StringIO

        from causaliq_core.graph.io import graphml

        from causaliq_analysis.merge import merge_graphs

        try:
            # Extract parameters
            aggregation_entries: Optional[List[Dict[str, Any]]] = (
                parameters.get("_aggregation_entries")
            )
            input_files = parameters.get("input", []) or []
            weights = parameters.get("weights")
            cpdag = parameters.get("cpdag", False)

            # Detect aggregation mode
            is_aggregation_mode = aggregation_entries is not None

            # Validate: must have either aggregation entries or file inputs
            if not is_aggregation_mode and not input_files:
                raise ActionExecutionError(
                    "merge_graphs requires either 'aggregate' parameter "
                    "(workflow aggregation mode) or 'input' (list of "
                    ".graphml or .db files)"
                )

            # Dry-run mode
            if mode == "dry-run":
                if logger and logger.is_terminal_logging:
                    if is_aggregation_mode and aggregation_entries:
                        print(
                            f"Would merge graphs from "
                            f"{len(aggregation_entries)} aggregated entries"
                        )
                    else:
                        print(
                            f"Would merge from {len(input_files)} input files"
                        )
                return (
                    "skipped",
                    {
                        "message": "Dry-run mode",
                        "aggregation_mode": is_aggregation_mode,
                        "num_inputs": (
                            len(aggregation_entries)
                            if aggregation_entries
                            else len(input_files)
                        ),
                    },
                    [],
                )

            # Set up logging callback
            log_fn = None
            if logger and logger.is_terminal_logging:
                log_fn = print

            # Read graphs based on mode
            graphs: List[Any] = []
            source_info: Dict[str, Any] = {}

            if is_aggregation_mode and aggregation_entries:
                # Aggregation mode: extract graphs from pre-scanned entries
                graphs, source_info = self._extract_graphs_from_entries(
                    aggregation_entries, log_fn
                )
            else:
                # Direct mode: read from file paths
                cache_entries_read = 0

                for input_path in input_files:
                    path_lower = input_path.lower()

                    if path_lower.endswith(".db"):
                        # Read from WorkflowCache
                        cache_graphs, entries = self._read_graphs_from_cache(
                            input_path, log_fn
                        )
                        graphs.extend(cache_graphs)
                        cache_entries_read += entries
                    else:
                        # Read as GraphML file
                        try:
                            graph = graphml.read(input_path)
                            graphs.append(graph)
                            if log_fn:
                                log_fn(f"Loaded file: {input_path}")
                        except Exception as e:
                            raise ActionExecutionError(
                                f"Failed to read {input_path}: {e}"
                            ) from e

                if cache_entries_read > 0:
                    source_info["cache_entries_read"] = cache_entries_read

            if not graphs:
                raise ActionExecutionError(
                    "No graphs found to merge. Check inputs."
                )

            # Merge graphs
            pdg = merge_graphs(graphs, weights=weights, cpdag=cpdag)

            # Serialise PDG to GraphML
            buffer = StringIO()
            graphml.write_pdg(pdg, buffer)
            pdg_graphml = buffer.getvalue()

            if log_fn:
                log_fn(f"Merged {len(graphs)} graphs into PDG")

            # Build result metadata
            metadata: Dict[str, Any] = {
                "num_graphs": len(graphs),
                "cpdag": cpdag,
                "aggregation_mode": is_aggregation_mode,
            }
            if weights:
                metadata["weights"] = weights
            metadata.update(source_info)

            objects = [
                {
                    "type": "graphml",
                    "name": "merged_pdg",
                    "content": pdg_graphml,
                }
            ]

            return (
                "success",
                metadata,
                objects,
            )

        except ActionExecutionError:
            raise
        except ValueError as e:
            raise ActionExecutionError(f"Graph merge failed: {e}") from e
        except Exception as e:
            raise ActionExecutionError(f"Graph merge failed: {e}") from e

    def _extract_graphs_from_entries(
        self,
        entries: List[Dict[str, Any]],
        log_fn: Optional[Any],
    ) -> Tuple[List[Any], Dict[str, Any]]:
        """Extract graphs from aggregation entries.

        Reads graphml objects from pre-scanned cache entries provided
        by the workflow executor in aggregation mode.

        Args:
            entries: List of entry dictionaries from aggregation scan.
                Each entry has: matrix_values, metadata, cache_path,
                entry_hash, entry (the CacheEntry object).
            log_fn: Optional logging function.

        Returns:
            Tuple of (list of graphs, source_info dict with provenance).

        Raises:
            ActionExecutionError: If graph extraction fails.
        """
        from io import StringIO

        from causaliq_core.graph.io import graphml

        graphs = []
        source_caches: set = set()
        entries_with_graphs = 0

        for entry_dict in entries:
            entry = entry_dict.get("entry")
            cache_path = entry_dict.get("cache_path", "unknown")
            matrix_values = entry_dict.get("matrix_values", {})

            if entry is None:
                continue

            source_caches.add(cache_path)
            found_in_entry = 0

            # Find all graphml objects in this entry
            for obj_name in entry.object_names():
                obj = entry.get_object(obj_name)
                if obj is None or obj.type != "graphml":
                    continue

                try:
                    graph = graphml.read(StringIO(obj.content))
                    graphs.append(graph)
                    found_in_entry += 1
                    if log_fn:
                        log_fn(f"Loaded '{obj_name}' from {matrix_values}")
                except Exception as e:
                    raise ActionExecutionError(
                        f"Failed to parse graph '{obj_name}' from "
                        f"entry {matrix_values}: {e}"
                    ) from e

            if found_in_entry > 0:
                entries_with_graphs += 1
            elif log_fn:
                log_fn(f"Entry {matrix_values} has no graphml objects")

        source_info = {
            "source_count": entries_with_graphs,
            "source_caches": sorted(source_caches),
        }

        return graphs, source_info

    def _read_graphs_from_cache(
        self,
        cache_path: str,
        log_fn: Optional[Any],
    ) -> Tuple[List[Any], int]:
        """Read graphs from a WorkflowCache database.

        Finds all objects with type='graphml' in all cache entries.

        Args:
            cache_path: Path to WorkflowCache database file (.db).
            log_fn: Optional logging function.

        Returns:
            Tuple of (list of graphs, number of entries with graphs).

        Raises:
            ActionExecutionError: If cache cannot be read.
        """
        from io import StringIO

        from causaliq_core.graph.io import graphml
        from causaliq_workflow.cache import WorkflowCache

        graphs = []
        entries_with_graphs = 0

        try:
            with WorkflowCache(cache_path) as cache:
                entries = cache.list_entries()
                if log_fn:
                    log_fn(f"Found {len(entries)} entries in cache")

                for entry_info in entries:
                    matrix_values = entry_info.get("matrix_values", {})
                    entry = cache.get(matrix_values)

                    if entry is None:
                        continue

                    # Find all graphml objects in this entry
                    found_in_entry = 0
                    for obj_name in entry.object_names():
                        obj = entry.get_object(obj_name)
                        if obj is None or obj.type != "graphml":
                            continue

                        try:
                            graph = graphml.read(StringIO(obj.content))
                            graphs.append(graph)
                            found_in_entry += 1
                            if log_fn:
                                log_fn(
                                    f"Loaded '{obj_name}' from {matrix_values}"
                                )
                        except Exception as e:
                            raise ActionExecutionError(
                                f"Failed to parse graph '{obj_name}' from "
                                f"cache entry {matrix_values}: {e}"
                            ) from e

                    if found_in_entry > 0:
                        entries_with_graphs += 1
                    elif log_fn:
                        log_fn(f"Entry {matrix_values} has no graphml objects")

        except FileNotFoundError:
            raise ActionExecutionError(f"Cache file not found: {cache_path}")
        except Exception as e:
            if isinstance(e, ActionExecutionError):
                raise
            raise ActionExecutionError(
                f"Failed to read from cache '{cache_path}': {e}"
            ) from e

        return graphs, entries_with_graphs


# Export as ActionProvider for auto-discovery by causaliq-workflow
ActionProvider = AnalysisActionProvider
