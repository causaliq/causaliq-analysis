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

from causaliq_analysis.graph_io import read_graph_or_pdg_file  # noqa: E402
from causaliq_analysis.migrate import run_migrate_trace  # noqa: E402
from causaliq_analysis.validation import (  # noqa: E402
    parse_sample_size,
    parse_seed_workflow,
    require_param,
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

    # Valid metrics for evaluate_graph action
    VALID_EVALUATE_METRICS = frozenset(
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
                self._validate_migrate_trace(parameters)
            elif action == "merge_graphs":
                self._validate_merge_graphs(parameters)
            elif action == "evaluate_graph":
                self._validate_evaluate_graph(parameters)
            elif action == "best_graph":
                self._validate_best_graph(parameters)
            elif action == "summarise":
                self._validate_summarise(parameters)
            elif action == "plot":
                ACTION_CLASSES["plot"]().validate(parameters)
        except ValueError as e:
            raise ActionValidationError(str(e))

    def _validate_migrate_trace(self, parameters: Dict[str, Any]) -> None:
        """Validate migrate_trace parameters."""
        # Require traces OR (series AND network)
        has_traces = (
            "traces" in parameters and parameters["traces"] is not None
        )
        has_series = (
            "series" in parameters and parameters["series"] is not None
        )
        has_network = (
            "network" in parameters and parameters["network"] is not None
        )

        if not has_traces and not (has_series and has_network):
            raise ValueError(
                "'migrate_trace' requires either 'traces' parameter or "
                "both 'series' and 'network' parameters"
            )

        # Validate sample_size if provided
        sample_size = parameters.get("sample_size")
        if sample_size is not None:
            parse_sample_size(sample_size)

        # Validate seed if provided
        seed = parameters.get("seed")
        if seed is not None:
            parse_seed_workflow(seed)

        # Validate output - must be .db (workflow cache)
        output_path = parameters.get("output")
        if output_path is not None:
            if not str(output_path).lower().endswith(".db"):
                raise ValueError(
                    "migrate_trace output must be a workflow cache (.db). "
                    f"Got: {output_path}"
                )

    def _validate_merge_graphs(self, parameters: Dict[str, Any]) -> None:
        """Validate merge_graphs parameters."""
        # Require _aggregation_entries OR input
        has_agg = "_aggregation_entries" in parameters
        has_input = "input" in parameters and parameters["input"] is not None

        if not has_agg and not has_input:
            raise ValueError(
                "'merge_graphs' requires either '_aggregation_entries' "
                "(aggregation mode) or 'input' parameter"
            )

        # Validate filter expression syntax if provided
        filter_expr = parameters.get("filter")
        validate_filter_expression(filter_expr)

        # Validate weights if provided as dict (spec format)
        weights = parameters.get("weights")
        if weights is not None and isinstance(weights, dict):
            try:
                from causaliq_core.utils import (
                    WeightSpecError,
                    validate_weight_spec,
                )

                validate_weight_spec(weights)
            except WeightSpecError as e:
                raise ValueError(f"Invalid weight specification: {e}")

        # Validate output - must be .db (workflow cache)
        output_path = parameters.get("output")
        if output_path is not None:
            if not str(output_path).lower().endswith(".db"):
                raise ValueError(
                    "merge_graphs output must be a workflow cache (.db). "
                    f"Got: {output_path}"
                )

        # Validate strategy if provided
        strategy = parameters.get("strategy")
        if strategy is not None and strategy not in {
            "average",
            "noisy_or",
            "max",
        }:
            raise ValueError(
                f"strategy must be 'average', 'noisy_or', "
                f"or 'max', got '{strategy}'"
            )

    def _validate_evaluate_graph(self, parameters: Dict[str, Any]) -> None:
        """Validate evaluate_graph parameters."""
        # UPDATE pattern: requires _update_entry at runtime, but
        # reference and metric are always required
        require_param(parameters, "reference", "evaluate_graph")
        require_param(parameters, "metric", "evaluate_graph")

        # Validate metric names
        metric = parameters.get("metric")
        metrics = [metric] if isinstance(metric, str) else metric
        if metrics:
            invalid = set(metrics) - self.VALID_EVALUATE_METRICS
            if invalid:
                valid_list = ", ".join(sorted(self.VALID_EVALUATE_METRICS))
                raise ValueError(
                    f"Invalid metric(s): {', '.join(sorted(invalid))}. "
                    f"Valid metrics are: {valid_list}"
                )

    def _validate_best_graph(self, parameters: Dict[str, Any]) -> None:
        """Validate best_graph parameters.

        UPDATE pattern: requires input cache path containing entries with
        PDG objects. Adds DAG object to each matched entry.

        When called from workflow UPDATE mode, _update_entry is passed and
        input is handled by workflow engine.
        """
        # Require input only when not in UPDATE mode (workflow handles input)
        if "_update_entry" not in parameters:
            require_param(parameters, "input", "best_graph")

        # Validate threshold if provided
        threshold = parameters.get("threshold")
        if threshold is not None:
            try:
                float(threshold)
            except (ValueError, TypeError):
                raise ValueError(
                    f"'threshold' must be a number, got: {threshold}"
                )

        # Validate filter expression syntax if provided
        filter_expr = parameters.get("filter")
        validate_filter_expression(filter_expr)

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
            return self._run_migrate_trace(parameters, mode, context, logger)
        elif action == "merge_graphs":
            return self._run_merge_graphs(parameters, mode, context, logger)
        elif action == "evaluate_graph":
            return self._run_evaluate_graph(parameters, mode, context, logger)
        elif action == "best_graph":
            return self._run_best_graph(parameters, mode, context, logger)
        elif action == "plot":
            plot_action = ACTION_CLASSES["plot"]()
            return plot_action.run(parameters, mode, context, logger)
        else:
            # action == "summarise" - must be valid since validate_parameters
            # already verified action is in supported_actions
            return self._run_summarise(parameters, mode, context, logger)

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
            seed_input = parameters.get("seed", "")

            # Build trace path pattern
            if traces_pattern:
                partial_id = traces_pattern.replace(".pkl.gz", "")
            elif series and network:
                partial_id = f"{series}/{network}"
            else:  # pragma: no cover
                raise ActionExecutionError(
                    "Must provide either 'traces' or both 'series' and "
                    "'network'"
                )

            # Parse optional filters
            sample_size = None
            if sample_size_input is not None:
                sample_size = parse_sample_size(sample_size_input)

            seed_tuple = parse_seed_workflow(seed_input)

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
                seed=seed_tuple if seed_tuple else None,
                log_fn=log_fn,
            )

            # No matching traces — skip this matrix entry.
            if result.num_graphs == 0:
                return (
                    "skipped",
                    {
                        "message": (
                            f"No traces for {partial_id} "
                            f"sample_size={sample_size} "
                            f"seed={seed_tuple}"
                        ),
                        "num_graphs": 0,
                    },
                    [],
                )

            # Build objects list for cache storage (GraphML only)
            # Per-graph metadata at top level (flattened)
            objects = []
            metadata: Dict[str, Any] = {
                "num_graphs": result.num_graphs,
                "skipped": result.skipped,
            }

            for i, graph in enumerate(result.graphs):
                # Use 'dag' for single graph, 'dag_N' for multiple
                if len(result.graphs) == 1:
                    obj_type = "dag"
                else:
                    obj_type = f"dag_{i}"

                # Add GraphML object
                objects.append(
                    {
                        "type": obj_type,
                        "format": "graphml",
                        "action": "migrate_trace",
                        "content": graph.graphml,
                    }
                )

                # Per-graph metadata: flatten for single, nest for multiple
                graph_meta = {"trace_id": graph.trace_id, **graph.metadata}
                if len(result.graphs) == 1:
                    metadata.update(graph_meta)
                else:
                    metadata[obj_type] = graph_meta

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

        1. **Aggregation mode**: When called from a workflow with an
           AGGREGATE action pattern and .db input, receives pre-scanned
           cache entries via '_aggregation_entries'. Extracts graphs from
           these entries and merges them.

        2. **Direct mode**: When called from CLI or workflow without
           aggregation, reads graphs from 'inputs' file paths (.graphml or
           .db files).
        """
        from datetime import datetime, timezone
        from io import StringIO

        from causaliq_core.graph.io import graphml

        from causaliq_analysis.merge import merge_graphs

        try:
            # Extract parameters
            aggregation_entries: Optional[List[Dict[str, Any]]] = (
                parameters.get("_aggregation_entries")
            )
            input_raw = parameters.get("input", []) or []
            # Normalise input to list (accept string or list)
            if isinstance(input_raw, str):
                input_files = [input_raw]
            else:
                input_files = list(input_raw)
            weights = parameters.get("weights")
            filter_expr = parameters.get("filter")
            object_type = parameters.get("object_type")

            # Derive cpdag flag and object filter from object_type
            cpdag = object_type == "cpdag"
            obj_filter = "dag" if object_type == "cpdag" else object_type

            # Detect aggregation mode
            is_aggregation_mode = aggregation_entries is not None

            # Validate: must have either aggregation entries or file inputs
            if not is_aggregation_mode and not input_files:  # pragma: no cover
                raise ActionExecutionError(
                    "merge_graphs requires 'input' (list of .graphml or "
                    ".db files). For aggregation mode, use AGGREGATE action "
                    "pattern with .db input."
                )

            # Dry-run mode
            if mode == "dry-run":
                if logger and logger.is_terminal_logging:
                    if is_aggregation_mode:
                        entry_count = len(aggregation_entries or [])
                        print(
                            f"Would merge graphs from "
                            f"{entry_count} aggregated entries"
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
                            len(aggregation_entries or [])
                            if is_aggregation_mode
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
            graph_metadata: List[Dict[str, Any]] = []
            source_info: Dict[str, Any] = {}

            if is_aggregation_mode:
                # Aggregation mode: extract graphs from pre-scanned entries
                # If no entries matched, this is an error (don't fall back to
                # direct mode which would read ALL entries)
                if not aggregation_entries:
                    raise ActionExecutionError(
                        "No cache entries matched the current matrix values. "
                        "Check that matrix values in workflow match those in "
                        "the input cache (values are case-sensitive)."
                    )
                graphs, graph_metadata, source_info = (
                    self._extract_graphs_from_entries(
                        aggregation_entries,
                        log_fn,
                        object_type=obj_filter,
                    )
                )
            else:
                # Direct mode: read from file paths
                cache_entries_read = 0

                for input_path in input_files:
                    path_lower = input_path.lower()

                    if path_lower.endswith(".db"):
                        # Read from WorkflowCache
                        cache_graphs, entries = self._read_graphs_from_cache(
                            input_path,
                            log_fn,
                            object_type=obj_filter,
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

            # Process weights: detect if metadata-driven (dict) or explicit
            final_weights: Optional[List[float]] = None
            weights_applied = False

            if weights is not None:
                if isinstance(weights, dict):
                    # Metadata-driven weight specification
                    if not graph_metadata:
                        raise ActionExecutionError(
                            "Metadata-driven weights require aggregation "
                            "mode (AGGREGATE pattern with .db input) or "
                            "provide explicit weight list."
                        )
                    final_weights = self._compute_weights_from_metadata(
                        graph_metadata, weights, log_fn
                    )
                    weights_applied = True
                elif isinstance(weights, list):
                    # Explicit weight list
                    final_weights = weights
                else:
                    raise ActionExecutionError(
                        f"weights must be a list or dict, "
                        f"got {type(weights).__name__}"
                    )

            # Merge graphs
            strategy = parameters.get("strategy", "average")
            pdg = merge_graphs(
                graphs,
                weights=final_weights,
                cpdag=cpdag,
                strategy=strategy,
            )

            # Serialise PDG to GraphML
            buffer = StringIO()
            graphml.write_pdg(pdg, buffer)
            pdg_graphml = buffer.getvalue()

            if log_fn:
                log_fn(f"Merged {len(graphs)} graphs into PDG")

            # Build result metadata with provenance
            metadata: Dict[str, Any] = {
                "action": "merge_graphs",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "num_graphs": len(graphs),
                "cpdag": cpdag,
                "strategy": strategy,
                "aggregation_mode": is_aggregation_mode,
                "output": {"type": "pdg", "format": "graphml"},
            }
            if object_type is not None:
                metadata["object_type"] = object_type
            if filter_expr is not None:
                metadata["filter"] = filter_expr
            if weights_applied:
                metadata["weights_spec"] = weights
                metadata["weights_computed"] = final_weights
            elif final_weights:
                metadata["weights"] = final_weights
            metadata.update(source_info)

            objects = [
                {
                    "type": "pdg",
                    "format": "graphml",
                    "action": "merge_graphs",
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

    def _extract_graph_from_entry(
        self,
        entry: Any,
        source_label: str,
    ) -> Tuple[Any, str]:
        """Delegate to the shared helper in helpers.py."""
        return helpers._extract_graph_from_entry(entry, source_label)

    def _resolve_reference_graph(
        self,
        reference_path: str,
        update_entry: Dict[str, Any],
    ) -> Any:
        """Resolve the reference graph from a file or workflow cache.

        When reference_path points to a workflow cache (.db), the
        reference graph is resolved from the reference cache entry whose
        matrix variable values match the current input entry. The
        reference cache must use the same key structure (matrix variable
        names) as the input cache.

        Args:
            reference_path: Path to a reference graph file or a workflow
                cache (.db) containing reference graphs.
            update_entry: UPDATE action entry data containing the
                'matrix_values' for the current input entry.

        Returns:
            The parsed reference graph.

        Raises:
            ActionExecutionError: If the reference cannot be resolved.
        """
        # Single ground-truth reference graph file
        if not str(reference_path).lower().endswith(".db"):
            try:
                return read_graph_or_pdg_file(reference_path)
            except FileNotFoundError:
                raise ActionExecutionError(
                    f"Reference graph not found: {reference_path}"
                )
            except Exception as e:
                raise ActionExecutionError(
                    f"Failed to read reference graph: {e}"
                ) from e

        # Workflow cache reference: compare graphs in another cache
        from causaliq_workflow.cache import WorkflowCache

        matrix_values = update_entry.get("matrix_values", {})
        input_keys = set(matrix_values.keys())

        try:
            with WorkflowCache(reference_path) as ref_cache:
                ref_entries = ref_cache.list_entries()
                if not ref_entries:
                    raise ActionExecutionError(
                        f"Reference cache is empty: {reference_path}"
                    )

                # Reference cache must use the same key structure as the
                # input cache so matrix values resolve to matching entries.
                for ref_info in ref_entries:
                    ref_keys = set(ref_info.get("matrix_values", {}).keys())
                    if ref_keys != input_keys:
                        raise ActionExecutionError(
                            "Reference cache key structure does not match "
                            "input cache. Input keys: "
                            f"{sorted(input_keys)}, reference keys: "
                            f"{sorted(ref_keys)}"
                        )

                # Resolve the reference entry with identical matrix values
                ref_entry = ref_cache.get(matrix_values)
                if ref_entry is None:
                    raise ActionExecutionError(
                        "No entry in reference cache for matrix values "
                        f"{dict(matrix_values)}"
                    )

                source_label = f"reference cache entry {dict(matrix_values)}"
                graph, _ = self._extract_graph_from_entry(
                    ref_entry, source_label
                )
                return graph
        except ActionExecutionError:
            raise
        except Exception as e:
            raise ActionExecutionError(
                f"Failed to read reference cache: {e}"
            ) from e

    def _run_evaluate_graph(
        self,
        parameters: Dict[str, Any],
        mode: str,
        context: Optional[WorkflowContext],
        logger: Optional[WorkflowLogger],
    ) -> ActionResult:
        """Evaluate graph against ground truth reference.

        UPDATE pattern action: receives entry data via _update_entry,
        computes structural metrics, returns them as metadata. The
        reference may be a single ground-truth graph file or a workflow
        cache (.db) with entries sharing the input cache's key structure.

        Args:
            parameters: Action parameters including _update_entry
            mode: Execution mode ('dry-run', 'run', 'compare')
            context: Workflow context
            logger: Optional logger

        Returns:
            ActionResult with structural metrics as metadata
        """
        from causaliq_core.graph import PDG

        from causaliq_analysis.metrics import (
            EDGE_METRICS,
            pdag_compare,
            pdg_compare,
        )

        # Extract UPDATE action entry data
        update_entry = parameters.get("_update_entry")
        if not update_entry:
            raise ActionExecutionError(
                "evaluate_graph requires _update_entry parameter "
                "(UPDATE pattern action)"
            )

        reference_path = parameters.get("reference")
        if not reference_path:  # pragma: no cover
            raise ActionExecutionError(
                "evaluate_graph requires 'reference' parameter"
            )

        # Get requested metrics (metric is mandatory, validated above)
        requested_metrics = parameters.get("metric")
        if isinstance(requested_metrics, str):
            requested_metrics = [requested_metrics]
        # Type assertion: metric is required, so this is always a list
        assert requested_metrics is not None, "metric is required"

        # Handle dry-run mode
        if mode == "dry-run":
            matrix_values = update_entry.get("matrix_values", {})
            if logger and logger.is_terminal_logging:
                print(
                    f"Would evaluate graph {matrix_values} "
                    f"vs reference: {reference_path}"
                )
            return (
                "skipped",
                {
                    "reference": reference_path,
                },
                [],
            )

        # Extract graph from entry
        entry = update_entry.get("entry")
        if entry is None:
            raise ActionExecutionError("No entry object in _update_entry")

        graph, graph_type = self._extract_graph_from_entry(
            entry, "cache entry"
        )

        # Load reference graph (file or workflow cache)
        reference = self._resolve_reference_graph(reference_path, update_entry)

        # Compute metrics, using the probabilistic comparison for PDGs
        try:
            if isinstance(graph, PDG) or isinstance(reference, PDG):
                metrics = pdg_compare(graph, reference)
            else:
                metrics = pdag_compare(graph, reference)
        except Exception as e:
            raise ActionExecutionError(
                f"Metric computation failed: {e}"
            ) from e

        # Check if equivalence class metrics are needed
        need_equiv = any(m.startswith("equiv.") for m in requested_metrics)
        equiv_metrics_computed: Dict[str, Any] = {}

        if need_equiv:
            from causaliq_core.graph import DAG, PDAG
            from causaliq_core.graph.convert import dag_to_pdag, pdag_to_cpdag

            def _to_cpdag(g: Any) -> PDAG:
                """Convert graph to CPDAG (equivalence class)."""
                if isinstance(g, DAG):
                    return dag_to_pdag(g)
                elif isinstance(g, PDAG):
                    cpdag = pdag_to_cpdag(g)
                    if cpdag is None:
                        raise ActionExecutionError(
                            "PDAG is not extendable to a CPDAG"
                        )
                    return cpdag
                raise ActionExecutionError(
                    f"Cannot convert {type(g).__name__} to CPDAG"
                )

            try:
                learned_cpdag = _to_cpdag(graph)
                reference_cpdag = _to_cpdag(reference)
                equiv_result = pdag_compare(learned_cpdag, reference_cpdag)
                equiv_metrics_computed = {
                    "equiv.f1": equiv_result["f1"],
                    "equiv.shd": equiv_result["shd"],
                }
                if "equiv.edge" in requested_metrics:
                    for name in EDGE_METRICS:
                        equiv_metrics_computed[f"equiv.{name}"] = equiv_result[
                            name
                        ]
            except (ActionExecutionError, ValueError, TypeError):
                # PDAG not extendable to CPDAG (e.g. PC output
                # with conflicting orientations). Skip equiv
                # metrics and continue with skeleton metrics.
                if logger and logger.is_terminal_logging:
                    print(
                        "Warning: equivalence class not available, "
                        "skipping equiv metrics"
                    )

        # 'edge' and 'equiv.edge' are group requests which expand to the
        # individual low-level comparison count metric names
        wanted = set(requested_metrics)
        if "edge" in wanted:
            wanted.update(EDGE_METRICS)
        if "equiv.edge" in wanted:
            wanted.update(f"equiv.{name}" for name in EDGE_METRICS)

        # Build metadata with standard metric names
        # Note: pdag_compare returns 'p' and 'r' for precision/recall
        all_metrics: Dict[str, Any] = {
            "precision": metrics["p"],
            "recall": metrics["r"],
            "f1": metrics["f1"],
            "shd": metrics["shd"],
            **equiv_metrics_computed,
        }

        # Add low-level edge counts when explicitly requested
        if "edge" in wanted:
            for name in EDGE_METRICS:
                all_metrics[name] = metrics[name]

        # Filter to requested metrics (metric is mandatory)
        filtered_metrics = {
            k: v for k, v in all_metrics.items() if k in wanted
        }

        # Build final metadata (always include reference info)
        metadata: Dict[str, Any] = {
            **filtered_metrics,
            "reference": reference_path,
            "evaluated_graph": graph_type,
        }

        if logger and logger.is_terminal_logging:
            print(
                f"Evaluated {graph_type}: F1={metrics['f1']:.3f}, "
                f"SHD={metrics['shd']}"
            )

        return ("success", metadata, [])

    def _run_best_graph(
        self,
        parameters: Dict[str, Any],
        mode: str,
        context: Optional[WorkflowContext],
        logger: Optional[WorkflowLogger],
    ) -> ActionResult:
        """Extract optimal DAG from PDG using greedy algorithm.

        UPDATE pattern action: reads PDG from cache entry, extracts
        optimal DAG, returns it as an object to add to the entry.

        Supports two modes of operation:

        1. **Update mode**: When called from workflow with cache input,
           receives entry data via '_update_entry'. Extracts PDG from
           the pdg object in the entry.

        2. **Direct mode**: When called from CLI with file path, reads PDG
           directly from the specified GraphML file.

        Args:
            parameters: Action parameters including input, threshold
            mode: Execution mode ('dry-run', 'run', 'compare')
            context: Workflow context
            logger: Optional logger

        Returns:
            ActionResult with optimal DAG object to add to entry
        """
        from datetime import datetime, timezone
        from io import StringIO

        from causaliq_core.graph.io import graphml

        # Extract UPDATE action entry data
        update_entry = parameters.get("_update_entry")
        input_path = parameters.get("input")
        threshold = float(parameters.get("threshold", 0.0))

        # Detect update mode
        is_update_mode = update_entry is not None

        # Handle dry-run mode
        if mode == "dry-run":
            if logger and logger.is_terminal_logging:
                if is_update_mode:
                    assert update_entry is not None  # Type narrowing
                    matrix_values = update_entry.get("matrix_values", {})
                    print(
                        f"Would extract DAG from entry {matrix_values} "
                        f"(threshold={threshold})"
                    )
                else:
                    print(
                        f"Would extract optimal DAG from {input_path} "
                        f"(threshold={threshold})"
                    )
            return (
                "skipped",
                {
                    "input": input_path,
                    "threshold": threshold,
                    "update_mode": is_update_mode,
                },
                [],
            )

        # Read PDG based on mode
        pdg = None
        source_info: str = ""

        if is_update_mode:
            # Update mode: extract PDG from entry
            assert update_entry is not None  # Type narrowing
            entry = update_entry.get("entry")
            if entry is None:
                raise ActionExecutionError("No entry object in _update_entry")

            # Find pdg object in entry
            pdg_obj = entry.get_object("pdg")
            if pdg_obj is None:
                raise ActionExecutionError(
                    "Cache entry does not contain 'pdg' object. "
                    "Ensure input cache was created by merge_graphs action."
                )

            try:
                pdg = graphml.read_pdg(StringIO(pdg_obj.content))
                matrix_vals = update_entry.get("matrix_values", {})
                source_info = f"cache entry {matrix_vals}"
            except Exception as e:
                raise ActionExecutionError(
                    f"Failed to parse pdg from cache: {e}"
                ) from e
        else:
            # Direct mode: read from file path
            if not input_path:
                raise ActionExecutionError(
                    "best_graph requires 'input' parameter"
                )

            try:
                pdg = graphml.read_pdg(input_path)
                source_info = input_path
            except FileNotFoundError:
                raise ActionExecutionError(f"PDG file not found: {input_path}")
            except Exception as e:
                raise ActionExecutionError(f"Failed to read PDG: {e}") from e

        # Extract optimal DAG
        try:
            result = pdg.to_dag_greedy(threshold=threshold)
        except Exception as e:
            raise ActionExecutionError(f"DAG extraction failed: {e}") from e

        # Serialise DAG to GraphML
        buffer = StringIO()
        graphml.write(result.dag, buffer)
        dag_graphml = buffer.getvalue()

        if logger and logger.is_terminal_logging:
            print(
                f"Extracted DAG from {source_info}: "
                f"{result.edges_included} edges, "
                f"{result.edges_skipped_cycle} skipped (cycle), "
                f"{result.tie_breaks_applied} tie-breaks"
            )

        # Build metadata
        metadata: Dict[str, Any] = {
            "action": "best_graph",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "input_source": input_path if input_path else "update",
            "input": {"type": "pdg"},
            "output": {"type": "dag", "format": "graphml"},
            "threshold": threshold,
            "edges_included": result.edges_included,
            "edges_skipped_cycle": result.edges_skipped_cycle,
            "edges_skipped_threshold": result.edges_skipped_threshold,
            "tie_breaks_applied": result.tie_breaks_applied,
        }

        objects = [
            {
                "type": "dag",
                "format": "graphml",
                "action": "best_graph",
                "content": dag_graphml,
            }
        ]

        return ("success", metadata, objects)

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
