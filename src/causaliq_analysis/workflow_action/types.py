"""
Canonical type imports and fallback stubs for workflow action support.

The TYPE_CHECKING block is only executed by type checkers (mypy), never at
runtime. The else-block always runs at runtime, allowing type checkers to
see the real types while providing fallback stubs when the optional
causaliq_workflow package is not installed.

The action provider, the shared helpers and the action classes all resolve
these shared types from this module, so a single availability decision
applies across the whole sub-package.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

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
    except ImportError:
        # Define minimal stubs for runtime when workflow not installed
        class CausalIQActionProvider:  # type: ignore[no-redef]
            pass

        class ActionExecutionError(Exception):
            pass

        class ActionValidationError(Exception):  # type: ignore[no-redef]
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

        # Stub for ActionPattern enum
        class ActionPattern:  # type: ignore[no-redef]
            CREATE = "create"
            UPDATE = "update"
            AGGREGATE = "aggregate"
            NOCACHES = "nocaches"

        class WorkflowContext:
            pass

        class WorkflowLogger:
            pass


__all__ = [
    "ActionExecutionError",
    "ActionInput",
    "ActionPattern",
    "ActionResult",
    "ActionValidationError",
    "CausalIQActionProvider",
    "WorkflowContext",
    "WorkflowLogger",
]
