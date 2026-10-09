"""
Best_graph workflow action.

Extracts the optimal DAG from a PDG with the greedy algorithm. The action is
stateless, so validation and execution delegate to module-level helpers and
each step stays within the module and method limits.
"""

from datetime import datetime, timezone
from io import StringIO
from typing import Any, Dict, List, Optional, Tuple

from causaliq_analysis.validation import (
    require_param,
    validate_filter_expression,
)
from causaliq_analysis.workflow_action.actions.base import AnalysisAction
from causaliq_analysis.workflow_action.types import (
    ActionExecutionError,
    ActionPattern,
    ActionResult,
)

__all__ = ["BestGraphAction"]


class BestGraphAction(AnalysisAction):
    """Extract the optimal DAG from a PDG.

    Attributes:
        action_name: Action name as used in workflow definitions.
        pattern: Workflow action pattern used for cache validation.

    """

    action_name = "best_graph"
    pattern = ActionPattern.UPDATE

    def validate(self, parameters: Dict[str, Any]) -> None:
        """Validate best_graph parameters before execution.

        Args:
            parameters: Action parameter values.

        Raises:
            ValueError: If a parameter is missing or invalid. The provider
                converts this to an ActionValidationError.

        """
        _require_input_unless_update(parameters)
        _require_numeric_threshold(parameters)
        _require_valid_filter(parameters)

    def run(
        self,
        parameters: Dict[str, Any],
        mode: str,
        context: Optional[Any] = None,
        logger: Optional[Any] = None,
    ) -> ActionResult:
        """Execute optimal DAG extraction from a PDG.

        Reads the PDG from the workflow cache entry (UPDATE mode) or from a
        GraphML file (direct mode), extracts the optimal DAG and returns it
        as a GraphML object.

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
        request = _best_graph_request(parameters)
        if mode == "dry-run":
            return _dry_run_result(request, logger)
        pdg, source_info = _read_request_pdg(request)
        result, content = _extract_optimal_dag(pdg, request["threshold"])
        _log_extraction(source_info, result, logger)
        return _success_result(request, result, content)


def _require_input_unless_update(parameters: Dict[str, Any]) -> None:
    """Require an input path unless the workflow supplies the cache entry.

    Args:
        parameters: Action parameter values.

    Raises:
        ValueError: If 'input' is missing outside UPDATE mode.

    """
    if "_update_entry" not in parameters:
        require_param(parameters, "input", "best_graph")


def _require_numeric_threshold(parameters: Dict[str, Any]) -> None:
    """Require a numeric threshold when one is provided.

    Args:
        parameters: Action parameter values.

    Raises:
        ValueError: If 'threshold' is not a number.

    """
    threshold = parameters.get("threshold")
    if threshold is not None:
        _parse_threshold(threshold)


def _parse_threshold(threshold: Any) -> None:
    """Parse a threshold value, reporting invalid ones.

    Args:
        threshold: Threshold value to parse.

    Raises:
        ValueError: If the threshold is not numeric.

    """
    try:
        float(threshold)
    except (ValueError, TypeError):
        raise ValueError(f"'threshold' must be a number, got: {threshold}")


def _require_valid_filter(parameters: Dict[str, Any]) -> None:
    """Validate filter expression syntax when one is provided.

    Args:
        parameters: Action parameter values.

    Raises:
        ValueError: If the filter expression cannot be parsed.

    """
    validate_filter_expression(parameters.get("filter"))


def _best_graph_request(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Build the extraction request from action parameters.

    Args:
        parameters: Action parameter values.

    Returns:
        Request holding the input path, threshold and UPDATE entry data.

    """
    update_entry = parameters.get("_update_entry")
    request: Dict[str, Any] = {
        "input": parameters.get("input"),
        "threshold": float(parameters.get("threshold", 0.0)),
        "update_entry": update_entry,
        "is_update": update_entry is not None,
    }
    return request


def _dry_run_result(
    request: Dict[str, Any],
    logger: Optional[Any],
) -> ActionResult:
    """Return the dry-run result for a best_graph request.

    Args:
        request: Extraction request.
        logger: Logger for reporting.

    Returns:
        ActionResult tuple with status "skipped".

    """
    if logger and logger.is_terminal_logging:
        _print_dry_run(request)
    metadata: Dict[str, Any] = {
        "input": request["input"],
        "threshold": request["threshold"],
        "update_mode": request["is_update"],
    }
    return ("skipped", metadata, [])


def _print_dry_run(request: Dict[str, Any]) -> None:
    """Print the dry-run message for the active extraction mode.

    Args:
        request: Extraction request.

    """
    if request["is_update"]:
        matrix_values = _entry_matrix_values(request["update_entry"])
        print(
            f"Would extract DAG from entry {matrix_values} "
            f"(threshold={request['threshold']})"
        )
    else:
        print(
            f"Would extract optimal DAG from {request['input']} "
            f"(threshold={request['threshold']})"
        )


def _entry_matrix_values(update_entry: Dict[str, Any]) -> Dict[str, Any]:
    """Return the matrix values recorded on a workflow cache entry.

    Args:
        update_entry: UPDATE action entry data.

    Returns:
        Matrix variable values of the entry.

    """
    matrix_values: Dict[str, Any] = update_entry.get("matrix_values", {})
    return matrix_values


def _read_request_pdg(request: Dict[str, Any]) -> Tuple[Any, str]:
    """Read the PDG for a request from the cache entry or a file.

    Args:
        request: Extraction request.

    Returns:
        Tuple of (PDG, description of the PDG source).

    Raises:
        ActionExecutionError: If the PDG cannot be read or parsed.

    """
    if request["is_update"]:
        return _read_pdg_from_entry(request["update_entry"])
    return _read_pdg_from_file(request["input"])


def _read_pdg_from_entry(update_entry: Dict[str, Any]) -> Tuple[Any, str]:
    """Read the PDG from a workflow cache entry.

    Args:
        update_entry: UPDATE action entry data.

    Returns:
        Tuple of (PDG, description of the cache entry).

    Raises:
        ActionExecutionError: If the entry carries no parseable PDG.

    """
    entry = update_entry.get("entry")
    if entry is None:
        raise ActionExecutionError("No entry object in _update_entry")
    pdg_object = entry.get_object("pdg")
    if pdg_object is None:
        raise ActionExecutionError(
            "Cache entry does not contain 'pdg' object. "
            "Ensure input cache was created by merge_graphs action."
        )
    try:
        pdg = _parse_pdg(pdg_object.content)
        return pdg, f"cache entry {_entry_matrix_values(update_entry)}"
    except Exception as e:
        raise ActionExecutionError(
            f"Failed to parse pdg from cache: {e}"
        ) from e


def _parse_pdg(content: str) -> Any:
    """Parse PDG GraphML content into a PDG object.

    Args:
        content: PDG GraphML document text.

    Returns:
        Parsed PDG.

    """
    from causaliq_core.graph.io import graphml

    return graphml.read_pdg(StringIO(content))


def _read_pdg_from_file(input_path: Any) -> Tuple[Any, str]:
    """Read a PDG from a GraphML file path.

    Args:
        input_path: Path to the PDG GraphML file.

    Returns:
        Tuple of (PDG, file path).

    Raises:
        ActionExecutionError: If the path is missing or cannot be read.

    """
    from causaliq_core.graph.io import graphml

    if not input_path:
        raise ActionExecutionError("best_graph requires 'input' parameter")
    try:
        return graphml.read_pdg(input_path), input_path
    except FileNotFoundError:
        raise ActionExecutionError(f"PDG file not found: {input_path}")
    except Exception as e:
        raise ActionExecutionError(f"Failed to read PDG: {e}") from e


def _extract_optimal_dag(pdg: Any, threshold: float) -> Tuple[Any, str]:
    """Extract the optimal DAG from a PDG and serialise it to GraphML.

    Args:
        pdg: PDG to extract the optimal DAG from.
        threshold: Minimum edge probability for an edge to be included.

    Returns:
        Tuple of (extraction result, DAG GraphML content).

    Raises:
        ActionExecutionError: If the extraction fails.

    """
    from causaliq_core.graph.io import graphml

    try:
        result = pdg.to_dag_greedy(threshold=threshold)
    except Exception as e:
        raise ActionExecutionError(f"DAG extraction failed: {e}") from e
    buffer = StringIO()
    graphml.write(result.dag, buffer)
    return result, buffer.getvalue()


def _log_extraction(
    source_info: str,
    result: Any,
    logger: Optional[Any],
) -> None:
    """Report the extraction result when terminal logging is enabled.

    Args:
        source_info: Description of the PDG source.
        result: Extraction result holding the edge counters.
        logger: Logger for reporting.

    """
    if logger and logger.is_terminal_logging:
        print(
            f"Extracted DAG from {source_info}: "
            f"{result.edges_included} edges, "
            f"{result.edges_skipped_cycle} skipped (cycle), "
            f"{result.tie_breaks_applied} tie-breaks"
        )


def _success_result(
    request: Dict[str, Any],
    result: Any,
    content: str,
) -> ActionResult:
    """Build the successful action result.

    Args:
        request: Extraction request.
        result: Extraction result holding the edge counters.
        content: DAG GraphML content.

    Returns:
        ActionResult tuple with status "success".

    """
    metadata = _success_metadata(request, result)
    return ("success", metadata, _dag_objects(content))


def _success_metadata(
    request: Dict[str, Any],
    result: Any,
) -> Dict[str, Any]:
    """Build the success metadata for an extraction.

    Args:
        request: Extraction request.
        result: Extraction result holding the edge counters.

    Returns:
        Action metadata describing the extracted DAG.

    """
    input_path = request["input"]
    metadata: Dict[str, Any] = {
        "action": "best_graph",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "input_source": input_path if input_path else "update",
        "input": {"type": "pdg"},
        "output": {"type": "dag", "format": "graphml"},
        "threshold": request["threshold"],
        "edges_included": result.edges_included,
        "edges_skipped_cycle": result.edges_skipped_cycle,
        "edges_skipped_threshold": result.edges_skipped_threshold,
        "tie_breaks_applied": result.tie_breaks_applied,
    }
    return metadata


def _dag_objects(content: str) -> List[Dict[str, Any]]:
    """Build the DAG object returned to the workflow cache.

    Args:
        content: DAG GraphML content.

    Returns:
        Single-element list holding the DAG object.

    """
    return [
        {
            "type": "dag",
            "format": "graphml",
            "action": "best_graph",
            "content": content,
        }
    ]
