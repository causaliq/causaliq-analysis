"""
CausalIQ Workflow Action for graph averaging and analysis operations.

This module implements the Action interface for causaliq-workflow integration,
enabling graph averaging to be used in workflow definitions.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Optional

# Check if workflow is available at runtime
WORKFLOW_AVAILABLE = False

# TYPE_CHECKING pattern: The if-block is only executed by type checkers (mypy),
# never at runtime. The else-block always runs at runtime. This allows type
# checkers to see the real types while providing fallback stubs when the
# optional causaliq_workflow package isn't installed.
if TYPE_CHECKING:  # pragma: no cover
    # Import types for type checking only (mypy sees these)
    from causaliq_workflow.action import (
        ActionExecutionError,
        ActionInput,
        CausalIQAction,
    )
    from causaliq_workflow.logger import WorkflowLogger
    from causaliq_workflow.registry import WorkflowContext
else:
    # Runtime imports with fallback stubs (Python executes this)
    try:
        from causaliq_workflow.action import (
            ActionExecutionError,
            ActionInput,
            CausalIQAction,
        )
        from causaliq_workflow.logger import WorkflowLogger
        from causaliq_workflow.registry import WorkflowContext

        WORKFLOW_AVAILABLE = True
    except ImportError:
        # Define minimal stubs for runtime when workflow not installed
        class CausalIQAction:  # type: ignore[no-redef]
            pass

        class ActionExecutionError(Exception):
            pass

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


from causaliq_analysis.graph import (  # noqa: E402
    _validate_average_params,
    average,
)
from causaliq_analysis.trace import Trace  # noqa: E402
from causaliq_analysis.validation import (  # noqa: E402
    parse_sample_size,
    parse_seeds_workflow,
)


class CausalIQAnalysisAction(CausalIQAction):
    """
    CausalIQ Analysis action for workflow integration.

    Supports multiple operations on causal graphs including:
    - graph-average: Compute edge probabilities across multiple learned graphs
    """

    # Action metadata
    name = "causaliq-analysis"
    version = "0.2.0"
    description = "Analysis and visualization of causal graphs"
    author = "CausalIQ"

    # Input specifications
    inputs = {
        "operation": ActionInput(
            name="operation",
            description="Operation to perform (e.g., 'graph-average')",
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
            description="Network name for graph averaging",
            required=False,
            type_hint="str",
        ),
        "sample_size": ActionInput(
            name="sample_size",
            description=(
                "Sample size to filter traces " "(int or string like '10k')"
            ),
            required=False,
            type_hint="int or str",
        ),
        "basis": ActionInput(
            name="basis",
            description="Basis for averaging: 'dag' or 'pdag'",
            required=False,
            default="dag",
            type_hint="str",
        ),
        "seeds": ActionInput(
            name="seeds",
            description="Seeds to include (comma-separated or list)",
            required=False,
            default="",
            type_hint="str or list",
        ),
        "result": ActionInput(
            name="result",
            description="Output file path for results (CSV)",
            required=False,
            type_hint="str",
        ),
    }

    # Output specifications
    outputs = {
        "result_file": "Path to the generated result file",
        "num_graphs": "Number of graphs averaged",
        "status": "Execution status",
    }

    def run(
        self,
        inputs: Dict[str, Any],
        mode: str = "dry-run",
        context: Optional[WorkflowContext] = None,
        logger: Optional[WorkflowLogger] = None,
    ) -> Dict[str, Any]:
        """
        Execute the analysis action.

        Args:
            inputs: Action input parameters
            mode: Execution mode ('dry-run', 'run', 'compare')
            context: Workflow context for optimization
            logger: Optional logger for reporting

        Returns:
            Dictionary of outputs

        Raises:
            ActionExecutionError: If execution fails
        """
        operation = inputs.get("operation", "").lower()

        if operation == "graph-average":
            return self._run_graph_average(inputs, mode, context, logger)
        else:
            raise ActionExecutionError(
                f"Unknown operation: {operation}. "
                f"Supported operations: graph-average"
            )

    def _run_graph_average(
        self,
        inputs: Dict[str, Any],
        mode: str,
        context: Optional[WorkflowContext],
        logger: Optional[WorkflowLogger],
    ) -> Dict[str, Any]:
        """Execute graph averaging operation."""
        try:
            # Extract and validate inputs
            traces_pattern = inputs.get("traces")
            root_dir = inputs.get("root_dir", "experiments")
            series = inputs.get("series")
            network = inputs.get("network")
            sample_size_input = inputs.get("sample_size")
            basis = inputs.get("basis", "dag")
            seeds_input = inputs.get("seeds", "")
            result_path = inputs.get("result")

            # Build trace path pattern
            if traces_pattern:
                # Direct pattern provided
                partial_id = traces_pattern.replace(".pkl.gz", "")
            elif series and network:
                # Build from series and network
                partial_id = f"{series}/{network}"
            else:
                raise ActionExecutionError(
                    "Must provide either 'traces' or both 'series' and "
                    "'network'"
                )

            # Parse sample size
            if sample_size_input is None:
                raise ActionExecutionError("sample_size is required")

            sample_size = parse_sample_size(sample_size_input)

            # Parse basis
            pdag = basis.lower() == "pdag"

            # Parse seeds
            seed_tuple = parse_seeds_workflow(seeds_input)

            # Validate parameters using common validation
            _validate_average_params(sample_size, pdag, seed_tuple)

            # Determine output path
            if not result_path:
                # Default output path based on inputs
                result_path = f"{root_dir}/{partial_id}_{sample_size}.csv"

            result_path_obj = Path(result_path)

            # Dry-run mode: just validate and report
            if mode == "dry-run":
                if logger and logger.is_terminal_logging:
                    print(
                        f"Would average graphs for {partial_id} "
                        f"with N={sample_size}, basis={basis}"
                    )
                return {
                    "result_file": str(result_path_obj),
                    "num_graphs": 0,
                    "status": "dry-run",
                }

            # Check if output exists (for run mode conservative execution)
            if mode == "run" and result_path_obj.exists():
                if logger and logger.is_terminal_logging:
                    print(f"Output {result_path} already exists, skipping")
                return {
                    "result_file": str(result_path_obj),
                    "num_graphs": 0,
                    "status": "skipped",
                }

            # Load traces
            if logger and logger.is_terminal_logging:
                print(f"Loading traces from {partial_id}...")

            traces = Trace.read(partial_id=partial_id, root_dir=root_dir)
            if traces is None:
                raise ActionExecutionError(
                    f"No traces found for {partial_id} in {root_dir}"
                )

            # Compute average
            if logger and logger.is_terminal_logging:
                print(
                    f"Computing average for N={sample_size}, "
                    f"basis={basis}, seeds={seed_tuple}..."
                )

            df = average(
                traces=traces,
                sample_size=sample_size,
                pdag=pdag,
                seeds=seed_tuple,
            )

            # Write output
            result_path_obj.parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(result_path_obj, index=False)

            if logger and logger.is_terminal_logging:
                print(f"Edge probabilities written to {result_path_obj}")

            return {
                "result_file": str(result_path_obj),
                "num_graphs": len(traces),
                "status": "success",
            }

        except Exception as e:
            raise ActionExecutionError(f"Graph averaging failed: {e}") from e
