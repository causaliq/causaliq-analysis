"""
Functional tests for causaliq-analysis workflow functionality.

These tests verify the workflow action behaves correctly in typical usage
scenarios, focusing on migrate_trace integration and workflow file processing.
"""

import pytest

# Test markers
pytestmark = pytest.mark.functional


# Test workflow action metadata is correctly defined.
def test_workflow_action_metadata():
    """Test workflow action metadata is correctly defined."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    action = AnalysisActionProvider()

    # Verify metadata
    assert action.name == "causaliq-analysis"
    assert action.version is not None
    assert action.description is not None
    assert action.author == "CausalIQ"

    # Verify input/output specifications exist
    assert isinstance(action.inputs, dict)
    assert isinstance(action.outputs, dict)
    assert len(action.inputs) > 0
    assert len(action.outputs) > 0


# Test that workflow action validates inputs correctly.
def test_workflow_action_input_validation():
    """Test that workflow action validates inputs correctly."""
    from causaliq_analysis.workflow_action import (
        ActionExecutionError,
        AnalysisActionProvider,
    )

    action = AnalysisActionProvider()

    # Test invalid action
    with pytest.raises(ActionExecutionError, match="Unknown action"):
        action.run("invalid-op", {}, mode="dry-run")


# Test migrate_trace action requires traces or series/network.
def test_migrate_trace_missing_parameters():
    """Test migrate_trace action requires traces or series/network."""
    from causaliq_analysis.workflow_action import (
        ActionExecutionError,
        AnalysisActionProvider,
    )

    action = AnalysisActionProvider()

    # Test missing both traces and series/network
    with pytest.raises(
        ActionExecutionError, match="Must provide either 'traces'"
    ):
        action.run("migrate_trace", {}, mode="run")


# Test migrate_trace dry-run mode.
def test_migrate_trace_dry_run():
    """Test migrate_trace action dry-run mode."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    action = AnalysisActionProvider()

    parameters = {
        "series": "TABU/STD",
        "network": "asia",
    }

    status, metadata, objects = action.run(
        "migrate_trace", parameters, mode="dry-run"
    )

    assert status == "skipped"
    assert "Dry-run mode" in metadata["message"]
    assert objects == []


# Test migrate_trace action with real trace files.
def test_migrate_trace_functional():
    """Test migrate_trace action with real trace files."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    action = AnalysisActionProvider()

    parameters = {
        "series": "TABU/STD",
        "network": "asia",
        "root_dir": "tests/data/functional/trace",
    }

    status, metadata, objects = action.run(
        "migrate_trace", parameters, mode="run"
    )

    assert status == "success"
    assert metadata["num_graphs"] > 0

    # Check objects returned for cache storage (GraphML only, no JSON)
    graphml_objects = [o for o in objects if o["type"] == "graphml"]
    json_objects = [o for o in objects if o["type"] == "json"]

    assert len(graphml_objects) > 0
    assert (
        len(json_objects) == 0
    )  # Per-graph metadata in metadata dict, not objects

    # Check per-graph metadata is in metadata dict keyed by object name
    for obj in graphml_objects:
        assert obj["name"] in metadata
        assert "N" in metadata[obj["name"]]


# Test migrate_trace with sample_size filter.
def test_migrate_trace_with_sample_size_filter():
    """Test migrate_trace action with sample_size filter."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    action = AnalysisActionProvider()

    parameters = {
        "series": "TABU/STD",
        "network": "asia",
        "root_dir": "tests/data/functional/trace",
        "sample_size": 1000,  # Filter to N=1000 only
    }

    status, metadata, objects = action.run(
        "migrate_trace", parameters, mode="run"
    )

    assert status == "success"
    # Should have filtered to only N=1000 traces
    assert metadata["num_graphs"] >= 1


# Test migrate_trace full-circle: objects returned can be parsed correctly.
def test_migrate_trace_full_circle():
    """Test that migrated GraphML objects can be read back correctly."""
    from io import StringIO

    from causaliq_core.graph.io import graphml

    from causaliq_analysis.migrate import trace_to_dag
    from causaliq_analysis.trace import Trace
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    action = AnalysisActionProvider()

    parameters = {
        "series": "TABU/STD",
        "network": "asia",
        "root_dir": "tests/data/functional/trace",
        "sample_size": 1000,
    }

    status, metadata, objects = action.run(
        "migrate_trace", parameters, mode="run"
    )

    assert status == "success"

    # Read the original trace
    traces = Trace.read("TABU/STD/asia", "tests/data/functional/trace")
    assert traces is not None
    original_dag = trace_to_dag(traces["N1000"])

    # Find the GraphML object for N1000
    graphml_objects = [o for o in objects if o["type"] == "graphml"]
    n1000_graphml = [o for o in graphml_objects if "N1000" in o["name"]]
    assert len(n1000_graphml) >= 1

    # Parse the GraphML content
    graphml_content = n1000_graphml[0]["content"]
    buffer = StringIO(graphml_content)
    restored_graph = graphml.read(buffer)

    # Verify structure matches
    assert set(restored_graph.nodes) == set(original_dag.nodes)
    assert set(restored_graph.edges.keys()) == set(original_dag.edges.keys())

    # Check per-graph metadata is in metadata dict (not as separate object)
    object_name = n1000_graphml[0]["name"]
    assert object_name in metadata
    graph_metadata = metadata[object_name]
    assert "N" in graph_metadata
    assert graph_metadata["N"] == 1000


# Test migrate_trace with traces parameter instead of series/network.
def test_migrate_trace_with_traces_pattern() -> None:
    """Test migrate_trace using traces parameter directly."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    action = AnalysisActionProvider()

    parameters = {
        "traces": "TABU/STD/asia.pkl.gz",  # Use traces pattern
        "root_dir": "tests/data/functional/trace",
    }

    status, metadata, objects = action.run(
        "migrate_trace", parameters, mode="run"
    )

    assert status == "success"
    assert metadata["num_graphs"] > 0


# Test migrate_trace dry-run with terminal logging.
def test_migrate_trace_dry_run_with_logger(
    capsys: pytest.CaptureFixture,
) -> None:
    """Test migrate_trace dry-run prints when logger.is_terminal_logging."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    action = AnalysisActionProvider()

    # Create a mock logger with is_terminal_logging=True
    class MockLogger:
        is_terminal_logging = True

    parameters = {
        "series": "TABU/STD",
        "network": "asia",
    }

    status, metadata, objects = action.run(
        "migrate_trace", parameters, mode="dry-run", logger=MockLogger()
    )

    assert status == "skipped"
    captured = capsys.readouterr()
    assert "Would migrate traces from TABU/STD/asia" in captured.out


# Test migrate_trace run mode with terminal logging.
def test_migrate_trace_run_with_logger(capsys: pytest.CaptureFixture) -> None:
    """Test migrate_trace run prints when logger.is_terminal_logging."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    action = AnalysisActionProvider()

    # Create a mock logger with is_terminal_logging=True
    class MockLogger:
        is_terminal_logging = True

    parameters = {
        "series": "TABU/STD",
        "network": "asia",
        "root_dir": "tests/data/functional/trace",
    }

    status, metadata, objects = action.run(
        "migrate_trace", parameters, mode="run", logger=MockLogger()
    )

    assert status == "success"
    captured = capsys.readouterr()
    # Should have printed logging messages
    assert "Loading traces" in captured.out or len(captured.out) > 0


# Test migrate_trace raises ActionExecutionError on general exception.
def test_migrate_trace_general_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test migrate_trace wraps general exceptions in ActionExecutionError."""
    from causaliq_analysis.workflow_action import (
        ActionExecutionError,
        AnalysisActionProvider,
    )

    action = AnalysisActionProvider()

    # Mock run_migrate_trace to raise a general exception
    def mock_run_migrate_trace(*args, **kwargs):
        raise RuntimeError("Unexpected error")

    monkeypatch.setattr(
        "causaliq_analysis.workflow_action.run_migrate_trace",
        mock_run_migrate_trace,
    )

    parameters = {
        "series": "TABU/STD",
        "network": "asia",
        "root_dir": "tests/data/functional/trace",
    }

    with pytest.raises(ActionExecutionError, match="Trace migration failed"):
        action.run("migrate_trace", parameters, mode="run")


# Test migrate_trace raises ActionExecutionError on ValueError.
def test_migrate_trace_value_error_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test migrate_trace wraps ValueError in ActionExecutionError."""
    from causaliq_analysis.workflow_action import (
        ActionExecutionError,
        AnalysisActionProvider,
    )

    action = AnalysisActionProvider()

    # Mock run_migrate_trace to raise a ValueError
    def mock_run_migrate_trace(*args, **kwargs):
        raise ValueError("No traces found for pattern")

    monkeypatch.setattr(
        "causaliq_analysis.workflow_action.run_migrate_trace",
        mock_run_migrate_trace,
    )

    parameters = {
        "series": "TABU/STD",
        "network": "asia",
        "root_dir": "tests/data/functional/trace",
    }

    with pytest.raises(ActionExecutionError, match="Trace migration failed"):
        action.run("migrate_trace", parameters, mode="run")
