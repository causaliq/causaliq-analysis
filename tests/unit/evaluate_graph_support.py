"""Shared helpers for the evaluate_graph action tests."""

import json
from typing import Any, Dict
from unittest.mock import MagicMock, patch

from .conftest import (
    create_mock_graphml_entry,
)


def _metric(result: Any, name: str) -> Any:
    """Return a metric value from the returned metrics object."""
    return json.loads(result[2][0]["content"])[name]


def _metric_keys(result: Any) -> set:
    """Return the metric names held in the returned metrics object."""
    return set(json.loads(result[2][0]["content"]))


def _block(result: Any, name: str) -> Any:
    """Return a named metadata block from the action result."""
    return result[1][name]


def _run_evaluate(parameters: Dict[str, Any], context: Any = None) -> Any:
    """Run evaluate_graph with mocked graph reads and comparisons."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False
    entry = {
        "matrix_values": {"seed": 42},
        "metadata": {},
        "entry": create_mock_graphml_entry(),
    }
    mock_metrics = {"p": 1.0, "r": 1.0, "f1": 1.0, "shd": 0}
    with patch(
        "causaliq_analysis.metrics.pdag_compare",
        return_value=mock_metrics,
    ):
        with patch(
            "causaliq_core.graph.io.graphml.read",
            return_value=MagicMock(),
        ):
            return provider.run(
                action="evaluate_graph",
                parameters={
                    "_aggregation_entries": [entry],
                    **parameters,
                },
                mode="run",
                context=context,
                logger=mock_logger,
            )
