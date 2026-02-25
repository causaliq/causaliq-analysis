"""
CausalIQ Workflow Action for analysis operations.

This module implements the Action interface for causaliq-workflow integration,
enabling trace migration to be used in workflow definitions.
"""

from dataclasses import dataclass
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
            description="Action to perform: 'migrate_trace'",
            required=True,
            type_hint="str",
        ),
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
    }

    # Output specifications
    outputs = {
        "num_graphs": "Number of graphs processed",
        "status": "Execution status",
        "skipped": "Number of traces skipped",
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
            action: Action to perform ('migrate_trace')
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
        else:
            raise ActionExecutionError(
                f"Unknown action: {action}. Supported actions: migrate_trace"
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


# Export as ActionProvider for auto-discovery by causaliq-workflow
ActionProvider = AnalysisActionProvider
