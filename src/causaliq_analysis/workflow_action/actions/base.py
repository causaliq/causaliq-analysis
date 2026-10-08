"""
Abstract base contract for individual analysis workflow actions.

Each analysis workflow action is implemented as a small class that
validates its own parameters and executes a single action. The provider in
the parent package delegates to these action classes.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Tuple

from causaliq_analysis.workflow_action.types import (
    ActionPattern,
    ActionResult,
    ActionValidationError,
)

__all__ = ["AnalysisAction"]


class AnalysisAction(ABC):
    """Base contract for a single analysis workflow action.

    Attributes:
        action_name: Action name as used in workflow definitions.
        pattern: Workflow action pattern used for cache validation.
        required_parameters: Parameter names that must be provided.

    """

    action_name: str = ""
    pattern: ActionPattern = ActionPattern.NOCACHES
    required_parameters: Tuple[str, ...] = ()

    def validate(self, parameters: Dict[str, Any]) -> None:
        """Validate parameters shared by all analysis actions.

        Args:
            parameters: Action parameter values.

        Raises:
            ActionValidationError: If a required parameter is missing.

        """
        missing = [
            name
            for name in self.required_parameters
            if parameters.get(name) is None
        ]
        if missing:
            raise ActionValidationError(
                f"'{self.action_name}' requires "
                f"{', '.join(sorted(missing))}"
            )

    @abstractmethod
    def run(
        self,
        parameters: Dict[str, Any],
        mode: str,
        context: Optional[Any] = None,
        logger: Optional[Any] = None,
    ) -> ActionResult:
        """Execute the action and return its result.

        Args:
            parameters: Action parameter values.
            mode: Execution mode ('dry-run', 'run' or 'compare').
            context: Workflow context for optimisation.
            logger: Optional logger for task execution reporting.

        Returns:
            Tuple of (status, metadata, objects).

        """
        raise NotImplementedError
