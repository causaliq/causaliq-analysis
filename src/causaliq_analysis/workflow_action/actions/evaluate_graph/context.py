"""Reference context values for evaluate_graph."""

import json
from typing import Any, Dict, Optional

from causaliq_analysis.workflow_action.types import ActionExecutionError

__all__ = ["_context_values"]


def _context_values(context_path: Optional[str]) -> Dict[str, Any]:
    """Read the provenance values of a network context JSON file.

    Args:
        context_path: Path to the context file, or None when the action
            was called without one.

    Returns:
        Mapping with ``domain`` and ``source_repository``. Missing values
        are empty strings.

    Raises:
        ActionExecutionError: If the context file cannot be read or parsed.
    """
    if not context_path:
        return {"domain": "", "source_repository": ""}
    try:
        with open(context_path, encoding="utf-8") as handle:
            context = json.load(handle)
    except FileNotFoundError:
        raise ActionExecutionError(f"Context file not found: {context_path}")
    except (OSError, ValueError) as exc:
        raise ActionExecutionError(
            f"Failed to read context file '{context_path}': {exc}"
        ) from exc
    if not isinstance(context, dict):
        raise ActionExecutionError(
            f"Context file '{context_path}' must hold a JSON object"
        )
    provenance = context.get("provenance")
    if not isinstance(provenance, dict):
        provenance = {}
    return {
        "domain": str(context.get("domain") or ""),
        "source_repository": str(provenance.get("source_repository") or ""),
    }
