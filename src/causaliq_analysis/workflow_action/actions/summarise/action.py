"""The summarise action class and parameter validation."""

from typing import Any, Dict, Optional

from causaliq_analysis.validation import validate_filter_expression
from causaliq_analysis.workflow_action.actions.base import AnalysisAction
from causaliq_analysis.workflow_action.types import (
    ActionExecutionError,
    ActionPattern,
    ActionResult,
)

from .execution import _dry_run_result, _summarise
from .request import (
    _require_tabular_output,
    _summarise_request,
    _validate_columns,
)

__all__ = ["SummariseAction"]


class SummariseAction(AnalysisAction):
    """Summarise metric values from cache entries into a table.

    Attributes:
        action_name: Action name as used in workflow definitions.
        pattern: Workflow action pattern used for cache validation.

    """

    action_name = "summarise"
    pattern = ActionPattern.AGGREGATE

    def validate(self, parameters: Dict[str, Any]) -> None:
        """Validate summarise parameters before execution.

        Args:
            parameters: Action parameter values.

        Raises:
            ValueError: If a parameter is missing or invalid. The provider
                converts this to an ActionValidationError.

        """
        _validate_columns(parameters)
        validate_filter_expression(parameters.get("filter"))
        _require_tabular_output(parameters)

    def run(
        self,
        parameters: Dict[str, Any],
        mode: str,
        context: Optional[Any] = None,
        logger: Optional[Any] = None,
    ) -> ActionResult:
        """Execute metric summarisation to a table file.

        Aggregation mode summarises the pre-scanned cache entries passed
        via '_aggregation_entries' per matrix combination; direct mode
        reads entries from the 'input' cache files and produces a single
        summary row.

        Args:
            parameters: Action parameter values.
            mode: Execution mode ('dry-run', 'run' or 'compare').
            context: Workflow context for optimisation.
            logger: Logger for reporting.

        Returns:
            Tuple of (status, metadata, objects).

        Raises:
            ActionExecutionError: If execution fails.

        """
        try:
            request = _summarise_request(parameters)
            if mode == "dry-run":
                return _dry_run_result(request, logger)
            return _summarise(request, context, logger)
        except ActionExecutionError:
            raise
        except Exception as e:
            raise ActionExecutionError(f"Summarise failed: {e}") from e
