"""Unit tests for evaluate_graph reference context values."""

import json
from typing import Any

import pytest
from causaliq_core.graph import EdgeType

from causaliq_analysis.workflow_action.actions.evaluate_graph import (
    action,
    metric_values,
)
from causaliq_analysis.workflow_action.actions.evaluate_graph.context import (
    _context_values,
)
from causaliq_analysis.workflow_action.types import ActionExecutionError


def test_context_values_keep_raw_provenance(tmp_path: Any) -> None:
    """Context metrics keep the raw domain and repository values."""
    path = tmp_path / "asia_context.json"
    path.write_text(
        json.dumps(
            {
                "domain": "respiratory_diagnosis",
                "provenance": {"source_repository": "bnlearn"},
            }
        ),
        encoding="utf-8",
    )

    assert _context_values(str(path)) == {
        "domain": "respiratory_diagnosis",
        "source_repository": "bnlearn",
    }


def test_context_values_missing_path() -> None:
    """No context path reports empty values."""
    assert _context_values(None) == {
        "domain": "",
        "source_repository": "",
    }


def test_reference_arc_count_counts_directed_edges() -> None:
    """The reference arc count ignores non-directed edge states."""
    reference = type(
        "Reference",
        (),
        {
            "edges": {
                ("A", "B"): EdgeType.DIRECTED,
                ("B", "C"): EdgeType.UNDIRECTED,
                ("A", "C"): EdgeType.DIRECTED,
            }
        },
    )()
    assert metric_values._reference_arc_count(reference) == 2


# Test context-file error branches.
def test_context_values_missing_file(tmp_path: Any) -> None:
    """A missing context file is reported."""
    with pytest.raises(ActionExecutionError, match="not found"):
        _context_values(str(tmp_path / "missing.json"))


# Test invalid context JSON is reported.
def test_context_values_invalid_json(tmp_path: Any) -> None:
    """Invalid JSON is reported as a context error."""
    path = tmp_path / "context.json"
    path.write_text("{", encoding="utf-8")
    with pytest.raises(ActionExecutionError, match="Failed to read"):
        _context_values(str(path))


# Test a context file must hold an object.
def test_context_values_requires_object(tmp_path: Any) -> None:
    """A non-object context is rejected."""
    path = tmp_path / "context.json"
    path.write_text("[]", encoding="utf-8")
    with pytest.raises(ActionExecutionError, match="JSON object"):
        _context_values(str(path))


# Test missing provenance returns an empty repository.
def test_context_values_without_provenance(tmp_path: Any) -> None:
    """A context without provenance has an empty repository value."""
    path = tmp_path / "context.json"
    path.write_text('{"domain": "d", "provenance": []}', encoding="utf-8")
    assert _context_values(str(path)) == {
        "domain": "d",
        "source_repository": "",
    }


# Test reference arc counts for missing and list-valued edges.
def test_reference_arc_count_without_edges() -> None:
    """A reference without an edges attribute has zero arcs."""
    assert metric_values._reference_arc_count(object()) == 0
    reference = type("Reference", (), {"edges": [("A", "B")]})()
    assert metric_values._reference_arc_count(reference) == 1


# Test context metrics require and read a context path.
def test_add_context_metrics(tmp_path: Any) -> None:
    """Context metrics require a path and copy its raw values."""
    with pytest.raises(ActionExecutionError, match="require a 'context'"):
        metric_values._add_context_metrics({}, ["domain"], {})
    path = tmp_path / "context.json"
    path.write_text(
        '{"domain": "d", "provenance": {"source_repository": "r"}}',
        encoding="utf-8",
    )
    metrics: dict = {}
    metric_values._add_context_metrics(
        metrics,
        ["domain", "source_repository"],
        {"context": str(path)},
    )
    assert metrics == {"domain": "d", "source_repository": "r"}


# Test a non-string context path is rejected.
def test_context_path_must_be_text() -> None:
    """A non-string context path is rejected during validation."""
    with pytest.raises(ValueError, match="path string"):
        action._require_context({"context": 1})


# Test the reference arc metric is added only when requested.
def test_all_metrics_reference_arc_count() -> None:
    """The reference arc count is added to the requested metric map."""
    graph = type("Graph", (), {"nodes": ["A", "B"]})()
    reference = type(
        "Reference", (), {"edges": {("A", "B"): EdgeType.DIRECTED}}
    )()
    result = metric_values._all_metrics(
        {"p": 1.0, "r": 1.0, "f1": 1.0, "shd": 0},
        {},
        ["reference_arc_count"],
        graph,
        reference,
        {},
    )
    assert result["reference_arc_count"] == 1
