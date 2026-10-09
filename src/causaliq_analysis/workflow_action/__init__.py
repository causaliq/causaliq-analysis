"""
CausalIQ Workflow Action for analysis operations.

This package implements the Action interface for causaliq-workflow
integration, enabling trace migration to be used in workflow definitions.

The provider class lives here, with shared type imports and fallback stubs
in ``types.py`` and shared helper functions in ``helpers.py``.
"""

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
        ActionPattern,
        ActionResult,
        ActionValidationError,
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
            ActionPattern,
            ActionResult,
            ActionValidationError,
            CausalIQActionProvider,
        )
        from causaliq_workflow.logger import WorkflowLogger
        from causaliq_workflow.registry import WorkflowContext

        WORKFLOW_AVAILABLE = True
    except ImportError:
        # Fall back to stub definitions without workflow support
        from causaliq_analysis.workflow_action.types import (
            ActionExecutionError,
            ActionInput,
            ActionPattern,
            ActionResult,
            ActionValidationError,
            CausalIQActionProvider,
            WorkflowContext,
            WorkflowLogger,
        )

from causaliq_analysis.validation import (  # noqa: E402
    validate_filter_expression,
    validate_metric_specs,
)
from causaliq_analysis.workflow_action import helpers  # noqa: E402
from causaliq_analysis.workflow_action.actions import (  # noqa: E402
    ACTION_CLASSES,
)


class AnalysisActionProvider(CausalIQActionProvider):
    """
    CausalIQ Analysis action provider for workflow integration.

    Supports operations on causal graphs including:
    - migrate_trace: Convert legacy Trace files to GraphML format
    - merge_graphs: Merge multiple graphs into a PDG with probabilities
    - evaluate_graph: Compute structural metrics vs ground truth
    - summarise: Summarise numerical metrics into statistics
    - plot: Generate charts from a summarise CSV output
    """

    # Provider metadata
    name = "causaliq-analysis"
    version: str = ""  # Set dynamically from __version__
    description = "Migration and analysis of causal graph trace files"
    author = "CausalIQ"

    def __init__(self) -> None:
        """Initialise provider with version from package metadata."""
        import causaliq_analysis

        self.version = causaliq_analysis.__version__

    # Supported actions
    supported_actions = {
        "migrate_trace",
        "merge_graphs",
        "evaluate_graph",
        "best_graph",
        "summarise",
        "plot",
    }

    # Action patterns for workflow validation
    action_patterns = {
        "migrate_trace": ActionPattern.CREATE,
        "merge_graphs": ActionPattern.AGGREGATE,
        "evaluate_graph": ActionPattern.UPDATE,
        "best_graph": ActionPattern.UPDATE,
        "summarise": ActionPattern.AGGREGATE,
        "plot": ActionPattern.NOCACHES,
    }

    # Input specifications
    inputs = {
        "action": ActionInput(
            name="action",
            description=(
                "Action to perform: 'migrate_trace', 'merge_graphs', "
                "or 'evaluate_graph'"
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
        "seed": ActionInput(
            name="seed",
            description="Seed values to include (comma-separated or list)",
            required=False,
            default="",
            type_hint="str or list",
        ),
        # Shared filter parameter
        "filter": ActionInput(
            name="filter",
            description=(
                "Filter expression to select traces/entries by metadata. "
                "Uses Python syntax (e.g., \"algorithm == 'TABU'\", "
                "\"N > 1000 and network in ['asia', 'alarm']\")"
            ),
            required=False,
            type_hint="str",
        ),
        # merge_graphs input
        "input": ActionInput(
            name="input",
            description=(
                "Input file(s) (.graphml or .db). Can be a single path "
                "or a list of paths. Type is detected by extension. For "
                ".db files in aggregation mode (AGGREGATE action pattern), "
                "entries are grouped by matrix variables and graphs are "
                "extracted from matching entries."
            ),
            required=False,
            type_hint="str or list[str]",
        ),
        "weights": ActionInput(
            name="weights",
            description=(
                "Weights for merging. Can be: (1) a list of floats (one per "
                "graph, must sum to 1.0), or (2) a metadata-driven weight "
                "specification dict mapping metadata field names to "
                "value-weight pairs. In aggregation mode, weights are "
                "computed from entry metadata and normalised. "
                "If omitted, uniform weights are used."
            ),
            required=False,
            type_hint="list[float] or dict[str, dict[str, float]]",
        ),
        "object_type": ActionInput(
            name="object_type",
            description=(
                "Select graph object type to extract from cache "
                "entries. 'dag' extracts DAG objects, 'cpdag' "
                "extracts DAG objects and converts to CPDAGs "
                "before merging, 'pdg' extracts PDG objects. "
                "If not set, all graphml objects are used."
            ),
            required=False,
            type_hint="str",
        ),
        "strategy": ActionInput(
            name="strategy",
            description=(
                "Merge strategy for combining graphs. "
                "'average' for weighted average of "
                "probability vectors (default). "
                "'noisy_or' for noisy-OR existence with "
                "weighted orientation. 'max' to select "
                "the most confident source per edge."
            ),
            required=False,
            type_hint="str",
        ),
        # evaluate_graph inputs
        "reference": ActionInput(
            name="reference",
            description=(
                "Ground truth reference: path to a graph file "
                "(.graphml, .csv, .tetrad, .xdsl, .dsc) or a workflow "
                "cache (.db) containing reference graphs with the same "
                "key structure as the input cache. GraphML files may "
                "contain a PDG, in which case probabilities are compared."
            ),
            required=False,
            type_hint="str",
        ),
        # metric input (used by evaluate_graph and summarise)
        "metric": ActionInput(
            name="metric",
            description=(
                "For evaluate_graph: List of metrics to include in output "
                "(e.g., ['f1', 'shd', 'precision', 'recall', 'edge', "
                "'equiv.f1', 'equiv.shd', 'equiv.edge']). Required. "
                "The 'edge' and 'equiv.edge' values expand to the "
                "low-level edge counts returned by pdag_compare or "
                "pdg_compare (fractional for PDG inputs). "
                "For summarise: List of metric specs in <field>.<stat> format "
                "(e.g., ['f1.mean', 'shd.sd'])."
            ),
            required=False,
            type_hint="list[str] | str",
        ),
        # best_graph inputs - uses 'input' for cache containing merged_pdg
        "threshold": ActionInput(
            name="threshold",
            description=(
                "Minimum edge probability threshold for inclusion "
                "(default: 0.0)"
            ),
            required=False,
            default=0.0,
            type_hint="float",
        ),
        # plot inputs
        "type": ActionInput(
            name="type",
            description=(
                "Type of plot required, e.g. line, bar, box, violin, "
                "histogram, regression or scatter."
            ),
            required=False,
            default="line",
            type_hint="str",
        ),
        "subplot": ActionInput(
            name="subplot",
            description=(
                "Column name in the input CSV which defines the subplot "
                "(e.g. network)."
            ),
            required=False,
            type_hint="str",
        ),
        "group": ActionInput(
            name="group",
            description=(
                "Column name in the input CSV which defines how data "
                "points are grouped, typically shown in the legend "
                "(e.g. series)."
            ),
            required=False,
            type_hint="str",
        ),
        "x": ActionInput(
            name="x",
            description=(
                "Column name in the input CSV which provides the x-axis "
                "values (e.g. sample_size)."
            ),
            required=False,
            type_hint="str",
        ),
        "y": ActionInput(
            name="y",
            description=(
                "Column name in the input CSV which provides the y-axis "
                "values (e.g. f1.mean)."
            ),
            required=False,
            type_hint="str",
        ),
        "properties": ActionInput(
            name="properties",
            description=(
                "List of chart properties in '<name>=<value>' format "
                "with Python literal values (e.g. "
                "'dict.property={\"a\": 1}')."
            ),
            required=False,
            type_hint="list[str]",
        ),
    }

    # Output specifications
    outputs = {
        "num_graphs": "Number of graphs processed",
        "status": "Execution status",
        "skipped": "Number of traces skipped",
        "merged_pdg": "Merged PDG in GraphML format (merge_graphs)",
        # evaluate_graph outputs
        "precision": "Structural precision score",
        "recall": "Structural recall score",
        "f1": "Structural F1 score",
        "shd": "Structural Hamming Distance",
        "edge": (
            "Low-level edge counts from direct comparison (arc_matched, "
            "arc_reversed, edge_not_arc, arc_not_edge, edge_matched, "
            "arc_extra, edge_extra, arc_missing, edge_missing, "
            "missing_matched)"
        ),
        "equiv.edge": (
            "Low-level edge counts from CPDAG comparison, prefixed with "
            "'equiv.'"
        ),
        # summarise outputs
        "source_count": "Number of input entries summarised",
        "csv_output": "CSV file with summary statistics",
        # best_graph outputs
        "edges_included": "Number of edges in optimal DAG",
        "edges_skipped_cycle": "Edges skipped to avoid cycles",
        "edges_skipped_threshold": "Edges below probability threshold",
        "tie_breaks_applied": "Direction ties resolved alphabetically",
        "optimal_dag": "Optimal DAG in GraphML format",
        # plot outputs
        "plot_file": "Output chart image file path",
    }

    # Valid parameters per action (for unknown parameter validation)
    action_parameters: Dict[str, set] = {
        "migrate_trace": {
            "traces",
            "series",
            "network",
            "sample_size",
            "seed",
            "root_dir",
            "output",
        },
        "merge_graphs": {
            "input",
            "weights",
            "object_type",
            "strategy",
            "filter",
            "output",
            "_aggregation_entries",  # Internal workflow parameter
        },
        "evaluate_graph": {
            "input",
            "filter",
            "metric",
            "reference",
            "_update_entry",  # Internal workflow parameter
        },
        "best_graph": {
            "input",
            "threshold",
            "filter",
            "_update_entry",  # Internal workflow parameter
        },
        "summarise": {
            "metric",
            "filter",
            "input",
            "output",
            "_aggregation_entries",  # Internal workflow parameter
        },
        "plot": {
            "input",
            "output",
            "type",
            "subplot",
            "group",
            "x",
            "y",
            "properties",
        },
    }

    def validate_parameters(
        self, action: str, parameters: Dict[str, Any]
    ) -> None:
        """Validate action and parameters before execution.

        Performs action-specific parameter validation using shared
        validation utilities from causaliq_analysis.validation.

        Args:
            action: Action to perform.
            parameters: Parameter dictionary.

        Raises:
            ActionValidationError: If validation fails.
        """
        # Check action is supported via base class
        super().validate_parameters(action, parameters)

        # Check for unknown parameters
        valid_params = self.action_parameters.get(action, set())
        # Filter out 'action' which is always valid
        param_keys = {k for k in parameters.keys() if k != "action"}
        unknown = param_keys - valid_params
        if unknown:
            raise ActionValidationError(
                f"Unknown parameter(s) for '{action}': {sorted(unknown)}"
            )

        try:
            if action == "migrate_trace":
                ACTION_CLASSES["migrate_trace"]().validate(parameters)
            elif action == "merge_graphs":
                ACTION_CLASSES["merge_graphs"]().validate(parameters)
            elif action == "evaluate_graph":
                ACTION_CLASSES["evaluate_graph"]().validate(parameters)
            elif action == "best_graph":
                ACTION_CLASSES["best_graph"]().validate(parameters)
            elif action == "summarise":
                self._validate_summarise(parameters)
            elif action == "plot":
                ACTION_CLASSES["plot"]().validate(parameters)
        except ValueError as e:
            raise ActionValidationError(str(e))

    def _validate_summarise(self, parameters: Dict[str, Any]) -> None:
        """Validate summarise parameters."""
        # Require metric list
        metric_specs = parameters.get("metric", [])
        validate_metric_specs(metric_specs)

        # Validate filter expression syntax if provided
        filter_expr = parameters.get("filter")
        validate_filter_expression(filter_expr)

        # Validate output - must be .csv
        output_path = parameters.get("output")
        if output_path is None:
            raise ValueError(
                "summarise requires 'output' parameter with .csv file path."
            )
        if not str(output_path).lower().endswith(".csv"):
            raise ValueError(
                "summarise output must be a CSV file (.csv). "
                f"Got: {output_path}"
            )

    def run(
        self,
        action: str,
        parameters: Dict[str, Any],
        mode: str = "dry-run",
        context: Optional[WorkflowContext] = None,
        logger: Optional[WorkflowLogger] = None,
    ) -> ActionResult:
        """Execute analysis action with action-specific dry-run handling.

        Overrides base class to preserve action-specific dry-run behaviour
        that requires logger access for terminal output.

        Args:
            action: Action to perform.
            parameters: Action parameter values.
            mode: Execution mode ('dry-run', 'run', 'compare').
            context: Workflow context for optimisation.
            logger: Logger for reporting.

        Returns:
            Tuple of (status, metadata, objects).

        Raises:
            ActionExecutionError: If execution fails.
        """
        # Validate parameters (base class hook)
        self.validate_parameters(action, parameters)
        # Skip base class _dry_run_result() - action handlers have
        # their own dry-run logic that needs logger access
        return self._execute(action, parameters, mode, context, logger)

    def _run_action_class(
        self,
        action: str,
        parameters: Dict[str, Any],
        mode: str,
        context: Optional[WorkflowContext],
        logger: Optional[WorkflowLogger],
    ) -> ActionResult:
        """Execute an action from the action class registry.

        Args:
            action: Action to perform.
            parameters: Action parameter values.
            mode: Execution mode ('dry-run', 'run' or 'compare').
            context: Workflow context for optimisation.
            logger: Logger for reporting.

        Returns:
            Tuple of (status, metadata, objects).

        """
        return ACTION_CLASSES[action]().run(parameters, mode, context, logger)

    def _execute(
        self,
        action: str,
        parameters: Dict[str, Any],
        mode: str,
        context: Optional[WorkflowContext],
        logger: Optional[WorkflowLogger],
    ) -> ActionResult:
        """Execute the analysis action.

        Args:
            action: Action to perform ('migrate_trace', 'merge_graphs',
                'evaluate_graph', 'best_graph', 'summarise', or 'plot')
            parameters: Action parameter values.
            mode: Execution mode ('dry-run', 'run', 'compare').
            context: Workflow context for optimisation.
            logger: Logger for reporting.

        Returns:
            Tuple of (status, metadata, objects).

        Raises:
            ActionExecutionError: If execution fails.
        """
        if action == "migrate_trace":
            return self._run_action_class(
                action, parameters, mode, context, logger
            )
        elif action == "merge_graphs":
            return self._run_action_class(
                action, parameters, mode, context, logger
            )
        elif action == "evaluate_graph":
            return self._run_action_class(
                action, parameters, mode, context, logger
            )
        elif action == "best_graph":
            return self._run_action_class(
                action, parameters, mode, context, logger
            )
        elif action == "plot":
            return self._run_action_class(
                action, parameters, mode, context, logger
            )
        else:
            # action == "summarise" - must be valid since validate_parameters
            # already verified action is in supported_actions
            return self._run_summarise(parameters, mode, context, logger)

    def _extract_graph_from_entry(
        self,
        entry: Any,
        source_label: str,
    ) -> Tuple[Any, str]:
        """Delegate to the shared helper in helpers.py."""
        return helpers._extract_graph_from_entry(entry, source_label)

    def _run_summarise(
        self,
        parameters: Dict[str, Any],
        mode: str,
        context: Optional[WorkflowContext],
        logger: Optional[WorkflowLogger],
    ) -> ActionResult:
        """Execute metric summarisation.

        Aggregates numerical metrics from cache entries into summary
        statistics (mean, SD, count) and outputs CSV.

        Supports two modes of operation:

        1. **Aggregation mode**: When called from a workflow with an
           AGGREGATE action pattern and .db input, receives pre-scanned
           cache entries via '_aggregation_entries'. For each matrix
           combination, computes summary statistics from matching entries.

        2. **Direct mode**: When called from CLI or workflow without
           aggregation, reads entries from 'input' cache file(s) and
           produces a single summary row.
        """
        import csv
        import statistics
        from datetime import datetime, timezone
        from pathlib import Path

        SUPPORTED_STATS = {"mean", "sd", "count"}

        try:
            # Extract parameters
            aggregation_entries: Optional[List[Dict[str, Any]]] = (
                parameters.get("_aggregation_entries")
            )
            metric_specs = parameters.get("metric", [])
            filter_expr = parameters.get("filter")
            output_path = parameters.get("output")

            # Normalise metric_specs to list (accept string or list)
            if isinstance(metric_specs, str):
                metric_specs = [metric_specs]

            # Validate metric specs (validation happens in validate_parameters)
            if not metric_specs:  # pragma: no cover
                raise ActionExecutionError(
                    "summarise requires 'metric' parameter with at least one "
                    "metric specification (e.g., ['f1.mean', 'shd.sd'])"
                )

            # Parse metric specifications
            parsed_metrics: List[Tuple[str, str]] = []
            for spec in metric_specs:
                # Detect comma-separated string (common YAML mistake)
                if "," in spec:  # pragma: no cover
                    raise ActionExecutionError(
                        f"Invalid metric spec '{spec}': contains comma. "
                        "Use YAML list syntax: metric: [f1.mean, shd.sd]"
                    )
                if "." not in spec:  # pragma: no cover
                    raise ActionExecutionError(
                        f"Invalid metric spec '{spec}': "
                        "must be <field>.<stat>"
                    )
                parts = spec.rsplit(".", 1)
                field, stat = parts[0], parts[1]
                if stat not in SUPPORTED_STATS:  # pragma: no cover
                    raise ActionExecutionError(
                        f"Unknown statistic '{stat}' in '{spec}'. "
                        f"Supported: {', '.join(sorted(SUPPORTED_STATS))}"
                    )
                parsed_metrics.append((field, stat))

            # Determine output target
            is_aggregation_mode = aggregation_entries is not None

            # Extract unique fields for value collection
            unique_fields = list(dict.fromkeys(f for f, _ in parsed_metrics))

            # Dry-run mode
            if mode == "dry-run":
                if logger and logger.is_terminal_logging:
                    if is_aggregation_mode:
                        entry_count = len(aggregation_entries or [])
                        print(
                            f"Would summarise metrics from "
                            f"{entry_count} entries"
                        )
                    else:
                        print("Would summarise metrics from input files")
                return (
                    "skipped",
                    {
                        "message": "Dry-run mode",
                        "aggregation_mode": is_aggregation_mode,
                        "metrics": metric_specs,
                    },
                    [],
                )

            # Set up logging callback
            log_fn = None
            if logger and logger.is_terminal_logging:
                log_fn = print

            # Collect values from entries
            all_values: Dict[str, List[float]] = {
                field: [] for field in unique_fields
            }
            source_count = 0
            source_caches: set = set()

            # Get matrix values from context (used for filtering and output)
            ctx_matrix: Dict[str, Any] = {}
            if context and hasattr(context, "matrix_values"):
                ctx_matrix = context.matrix_values or {}

            if is_aggregation_mode:
                # Aggregation mode: extract from pre-scanned entries
                # Process whatever entries were provided (may be empty if
                # no entries matched the current matrix values)

                # Pre-resolve random() in filter
                resolved_filter = filter_expr
                extra_names: Dict[str, Any] = {}
                if filter_expr and "random(" in filter_expr:
                    from causaliq_core.utils import (
                        resolve_random_calls,
                    )

                    _agg_meta = [
                        self._flatten_entry_metadata(
                            ed.get("matrix_values", {}),
                            ed.get("metadata", {}),
                        )
                        for ed in (aggregation_entries or [])
                    ]
                    resolved_filter, extra_names = resolve_random_calls(
                        filter_expr, _agg_meta
                    )

                for entry_dict in aggregation_entries or []:
                    matrix_values = entry_dict.get("matrix_values", {})
                    entry_metadata = entry_dict.get("metadata", {})
                    cache_path = entry_dict.get("cache_path", "unknown")

                    source_caches.add(cache_path)

                    # Flatten metadata for access
                    flat_meta = self._flatten_entry_metadata(
                        matrix_values, entry_metadata
                    )

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

                    source_count += 1

                    # Extract metric values
                    for field in unique_fields:
                        value = self._get_nested_value(flat_meta, field)
                        if value is not None and isinstance(
                            value, (int, float)
                        ):
                            all_values[field].append(float(value))

                    if log_fn:
                        log_fn(f"Processed entry: {matrix_values}")

            elif not is_aggregation_mode:
                # Direct mode: read from input files (only when NOT in
                # aggregation mode - don't fall back when aggregation finds
                # no matches)
                input_raw = parameters.get("input", []) or []
                if isinstance(input_raw, str):
                    input_files = [input_raw]
                else:
                    input_files = list(input_raw)

                if not input_files:
                    raise ActionExecutionError(
                        "summarise requires either aggregation entries or "
                        "'input' parameter with cache file path(s)"
                    )

                for cache_path in input_files:
                    if not cache_path.lower().endswith(".db"):
                        raise ActionExecutionError(
                            f"summarise workflow action only supports .db "
                            f"cache files, got: {cache_path}"
                        )

                    source_caches.add(cache_path)
                    count = self._collect_values_from_cache(
                        cache_path,
                        unique_fields,
                        all_values,
                        filter_expr,
                        ctx_matrix,
                        log_fn,
                    )
                    source_count += count

            if log_fn:
                log_fn(f"Collected values from {source_count} entries")

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
                        results[col_name] = ""
                elif stat == "sd":
                    if len(values) >= 2:
                        results[col_name] = statistics.stdev(values)
                    else:
                        results[col_name] = ""

            # Build metadata
            timestamp = datetime.now(timezone.utc).isoformat()
            metadata: Dict[str, Any] = {
                "source_count": source_count,
                "source_caches": sorted(source_caches),
                "metrics": metric_specs,
                "timestamp": timestamp,
            }
            if filter_expr:
                metadata["filter"] = filter_expr

            # Add computed values to metadata
            metadata.update(results)

            # Build output row: matrix values first, then metrics
            # This creates rows like: network, sample_size, f1.mean, ...
            row_data: Dict[str, Any] = {}

            # Add matrix values as first columns (from context)
            for key, value in ctx_matrix.items():
                row_data[key] = value

            # Add metric results
            row_data.update(results)

            # Write CSV output (output_path is validated to be .csv)
            assert output_path is not None  # Validated by _validate_summarise
            out_file = Path(output_path)
            out_file.parent.mkdir(parents=True, exist_ok=True)

            try:
                file_exists = out_file.exists()

                with open(
                    out_file,
                    "a" if file_exists else "w",
                    encoding="utf-8",
                    newline="",
                ) as f:
                    writer = csv.writer(f)
                    if not file_exists:
                        writer.writerow(row_data.keys())
                    writer.writerow(row_data.values())

                action = "appended to" if file_exists else "written to"
                metadata["csv_output"] = str(out_file)
                if log_fn:
                    log_fn(f"Summary {action} {out_file}")
            except Exception as e:
                raise ActionExecutionError(
                    f"Failed to write CSV output: {e}"
                ) from e

            return ("success", metadata, [])

        except ActionExecutionError:
            raise
        except Exception as e:
            raise ActionExecutionError(f"Summarise failed: {e}") from e

    def _collect_values_from_cache(
        self,
        cache_path: str,
        fields: List[str],
        all_values: Dict[str, List[float]],
        filter_expr: Optional[str],
        matrix_filter: Optional[Dict[str, Any]],
        log_fn: Optional[Any],
    ) -> int:
        """Delegate to the shared helper in helpers.py."""
        return helpers._collect_values_from_cache(
            cache_path, fields, all_values, filter_expr, matrix_filter, log_fn
        )

    def _get_nested_value(self, data: Dict[str, Any], field: str) -> Any:
        """Delegate to the shared helper in helpers.py."""
        return helpers._get_nested_value(data, field)

    def _extract_graphs_from_entries(
        self,
        entries: List[Dict[str, Any]],
        log_fn: Optional[Any],
        *,
        object_type: Optional[str] = None,
    ) -> Tuple[List[Any], List[Dict[str, Any]], Dict[str, Any]]:
        """Delegate to the shared helper in helpers.py."""
        return helpers._extract_graphs_from_entries(
            entries, log_fn, object_type=object_type
        )

    def _flatten_entry_metadata(
        self,
        matrix_values: Dict[str, Any],
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Delegate to the shared helper in helpers.py."""
        return helpers._flatten_entry_metadata(matrix_values, metadata)

    def _compute_weights_from_metadata(
        self,
        graph_metadata: List[Dict[str, Any]],
        weight_spec: Dict[str, Dict[str, float]],
        log_fn: Optional[Any],
    ) -> List[float]:
        """Delegate to the shared helper in helpers.py."""
        return helpers._compute_weights_from_metadata(
            graph_metadata, weight_spec, log_fn
        )

    def _read_graphs_from_cache(
        self,
        cache_path: str,
        log_fn: Optional[Any],
        *,
        object_type: Optional[str] = None,
    ) -> Tuple[List[Any], int]:
        """Delegate to the shared helper in helpers.py."""
        return helpers._read_graphs_from_cache(
            cache_path, log_fn, object_type=object_type
        )


# Export as ActionProvider for auto-discovery by causaliq-workflow
ActionProvider = AnalysisActionProvider
