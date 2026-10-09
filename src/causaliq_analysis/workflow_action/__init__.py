"""
CausalIQ Workflow Action for analysis operations.

This package implements the Action interface for causaliq-workflow
integration, enabling graph migration, merging, evaluation, summarisation
and plotting to be used in workflow definitions.

The provider class lives here; individual actions are implemented in
``actions/`` and registered in ``ACTION_CLASSES``, with shared type imports
and fallback stubs in ``types.py`` and shared helper functions in
``helpers.py``.
"""

from typing import TYPE_CHECKING, Any, Dict, Optional

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
        from causaliq_analysis.workflow_action.types import (  # noqa: F401
            ActionExecutionError,
            ActionInput,
            ActionPattern,
            ActionResult,
            ActionValidationError,
            CausalIQActionProvider,
            WorkflowContext,
            WorkflowLogger,
        )

from causaliq_analysis.workflow_action.actions import (  # noqa: E402
    ACTION_CLASSES,
)


class AnalysisActionProvider(CausalIQActionProvider):
    """
    CausalIQ Analysis action provider for workflow integration.

    Parameter validation and execution are delegated to the action class
    registered for each action in ``ACTION_CLASSES``. Supports operations
    on causal graphs including:
    - migrate_trace: Convert legacy Trace files to GraphML format
    - merge_graphs: Merge multiple graphs into a PDG with probabilities
    - evaluate_graph: Compute structural metrics vs ground truth
    - best_graph: Extract the optimal DAG from cached graphs
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

        Checks the action is supported, rejects unknown parameters, then
        delegates to the action class registered for the action. Value
        errors raised by the action class are reported as validation
        errors.

        Args:
            action: Action to perform.
            parameters: Parameter dictionary.

        Raises:
            ActionValidationError: If validation fails or the action is
                not supported.
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
            ACTION_CLASSES[action]().validate(parameters)
        except ValueError as e:
            raise ActionValidationError(str(e))

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
        """Execute the analysis action via its registered action class.

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


# Export as ActionProvider for auto-discovery by causaliq-workflow
ActionProvider = AnalysisActionProvider
