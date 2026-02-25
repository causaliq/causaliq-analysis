"""
Functional tests for causaliq-analysis workflow functionality.

These tests verify the workflow action behaves correctly in typical usage
scenarios, focusing on CLI integration and workflow file processing.
"""

import tempfile
from pathlib import Path

import pytest
import yaml

from tests.fixtures.workflows import (
    MATRIX_WORKFLOW,
    PARAMETERIZED_WORKFLOW,
    SIMPLE_WORKFLOW,
)

# Test markers
pytestmark = pytest.mark.functional


# Test that workflow YAML definitions are valid and parseable
def test_workflow_yaml_parsing():
    """Test that workflow YAML definitions are valid."""
    # Test simple workflow
    workflow_data = yaml.safe_load(SIMPLE_WORKFLOW)
    assert (
        workflow_data["description"] == "Simple graph averaging test workflow"
    )
    assert len(workflow_data["steps"]) == 1
    assert workflow_data["steps"][0]["uses"] == "causaliq-analysis"

    # Test matrix workflow
    matrix_data = yaml.safe_load(MATRIX_WORKFLOW)
    assert "matrix" in matrix_data
    assert "network" in matrix_data["matrix"]
    assert "sample_size" in matrix_data["matrix"]


# Test workflow action metadata is correctly defined
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


# Test that workflow action validates inputs correctly
def test_workflow_action_input_validation(monkeypatch):
    """Test that workflow action validates inputs correctly."""
    from causaliq_analysis.workflow_action import (
        ActionExecutionError,
        AnalysisActionProvider,
    )

    action = AnalysisActionProvider()

    # Test invalid action
    with pytest.raises(ActionExecutionError, match="Unknown action"):
        action.run("invalid-op", {}, mode="dry-run")

    # Test missing required parameters for graph-average
    with pytest.raises(ActionExecutionError):
        action.run("graph-average", {}, mode="dry-run")


# Test sample_size validation in workflow action
def test_workflow_action_sample_size_required():
    """Test that workflow action requires sample_size parameter."""
    from causaliq_analysis.workflow_action import (
        ActionExecutionError,
        AnalysisActionProvider,
    )

    action = AnalysisActionProvider()

    # Test missing sample_size (None) - should trigger the specific error
    parameters = {
        "series": "test_series",
        "network": "test_network",
        # sample_size is missing/None
    }

    with pytest.raises(ActionExecutionError, match="sample_size is required"):
        action.run("graph-average", parameters, mode="dry-run")


# Test traces not found error in workflow action
def test_workflow_action_traces_not_found(monkeypatch):
    """Test that workflow action handles case when no traces are found."""
    from causaliq_analysis.workflow_action import (
        ActionExecutionError,
        AnalysisActionProvider,
    )

    action = AnalysisActionProvider()

    # Valid parameters but traces won't be found
    parameters = {
        "series": "nonexistent_series",
        "network": "nonexistent_network",
        "sample_size": 1000,
        "seeds": "0",
    }

    # Mock Trace.read to return None (no traces found)
    monkeypatch.setattr(
        "causaliq_analysis.workflow_action.Trace.read",
        lambda partial_id, root_dir: None,
    )
    with pytest.raises(
        ActionExecutionError,
        match="No traces found for nonexistent_series/nonexistent_network",
    ):
        # Use "run" mode to actually try loading traces
        action.run("graph-average", parameters, mode="run")


# Test different ways to specify trace file patterns
def test_workflow_traces_pattern_building(monkeypatch):
    """Test different ways to specify trace file patterns."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    action = AnalysisActionProvider()

    class MockLogger:
        is_terminal_logging = True

    mock_logger = MockLogger()

    # Test with direct traces pattern
    parameters = {
        "traces": "TABU/SAMPLE/BASE/asia.pkl.gz",
        "sample_size": "10k",
        "seeds": "0,1",
    }

    result = action.run(
        "graph-average", parameters, mode="dry-run", logger=mock_logger
    )
    status, metadata, objects = result
    assert status == "skipped"

    # Test with series + network
    parameters = {
        "series": "TABU/SAMPLE/BASE",
        "network": "asia",
        "sample_size": "10k",
        "seeds": "0,1",
    }

    result = action.run(
        "graph-average", parameters, mode="dry-run", logger=mock_logger
    )
    status, metadata, objects = result
    assert status == "skipped"


# Test automatic result path generation
def test_workflow_result_path_generation():
    """Test automatic result path generation."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    action = AnalysisActionProvider()

    class MockLogger:
        is_terminal_logging = True

    mock_logger = MockLogger()

    parameters = {
        "root_dir": "/test/experiments",
        "series": "TABU/SAMPLE/BASE",
        "network": "asia",
        "sample_size": "10k",
        "seeds": "0,1",
    }

    result = action.run(
        "graph-average", parameters, mode="dry-run", logger=mock_logger
    )
    status, metadata, objects = result

    # Should generate default output path
    # (normalize path separators for Windows)
    expected_path = "/test/experiments/TABU/SAMPLE/BASE/asia_10000.csv"
    actual_path = metadata["result_file"].replace("\\", "/")
    assert actual_path == expected_path


# Test that parameter values work with typical workflow templating
def test_workflow_parameter_expansion_compatibility():
    """Test that parameter values work with typical workflow templating."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    action = AnalysisActionProvider()

    # Simulate template expansion
    expanded_parameters = {
        "series": "TABU/SAMPLE/BASE",
        "network": "asia",
        "sample_size": "10k",
        "result": "experiments/TABU/SAMPLE/BASE/asia_10k.csv",
        "seeds": "0,1",
    }

    class MockLogger:
        is_terminal_logging = True

    mock_logger = MockLogger()

    result = action.run(
        "graph-average",
        expanded_parameters,
        mode="dry-run",
        logger=mock_logger,
    )
    status, metadata, objects = result
    assert status == "skipped"
    assert "asia_10k.csv" in metadata["result_file"]


# Test conservative execution behavior (skip if output exists)
def test_workflow_conservative_execution(monkeypatch):
    """Test conservative execution behavior (skip if output exists)."""
    import pandas as pd

    from causaliq_analysis.workflow_action import AnalysisActionProvider

    action = AnalysisActionProvider()

    with tempfile.TemporaryDirectory() as temp_dir:
        result_file = Path(temp_dir) / "existing_result.csv"
        result_file.write_text("existing,data\n1,2")

        parameters = {
            "series": "TABU/SAMPLE/BASE",
            "network": "asia",
            "sample_size": "10k",
            "seeds": "0,1",
            "result": str(result_file),
        }

        class MockLogger:
            def __init__(self):
                self.is_terminal_logging = True

        mock_logger = MockLogger()

        # Run mode should skip if output exists
        result = action.run(
            "graph-average", parameters, mode="run", logger=mock_logger
        )
        status, metadata, objects = result
        assert status == "skipped"

        # Compare mode should re-run regardless
        class MockTrace:
            pass

        mock_traces_dict = {
            "trace1": MockTrace(),
            "trace2": MockTrace(),
            "trace3": MockTrace(),
            "trace4": MockTrace(),
            "trace5": MockTrace(),
        }

        class MockTraceReader:
            @staticmethod
            def read(partial_id, root_dir):
                return mock_traces_dict

        def mock_average_func(traces, sample_size, pdag, seeds):
            return pd.DataFrame({"col": [1, 2]})

        # Patch at the source modules first
        monkeypatch.setattr(
            "causaliq_analysis.trace.Trace.read", MockTraceReader.read
        )
        monkeypatch.setattr(
            "causaliq_analysis.graph.average", mock_average_func
        )

        # Force reload workflow_action to pick up the patched imports
        import sys

        # Remove from cache if present, then re-import
        if "causaliq_analysis.workflow_action" in sys.modules:
            del sys.modules["causaliq_analysis.workflow_action"]

        try:
            from causaliq_analysis import workflow_action  # noqa: F401
            from causaliq_analysis.workflow_action import (
                AnalysisActionProvider as ReloadedAction,
            )

            action_reloaded = ReloadedAction()

            # Provide root_dir to avoid path validation before mock intercepts
            parameters["root_dir"] = temp_dir

            result = action_reloaded.run(
                "graph-average", parameters, mode="compare", logger=mock_logger
            )
            status, metadata, objects = result
            assert status == "success"
            assert metadata["num_graphs"] == 5  # Length of mock traces dict
        finally:
            # Clean up reloaded module so subsequent tests get fresh import
            # without the mocked bindings
            if "causaliq_analysis.workflow_action" in sys.modules:
                del sys.modules["causaliq_analysis.workflow_action"]


# Test error handling in workflow execution
def test_workflow_error_handling():
    """Test error handling in workflow execution."""
    from causaliq_analysis.workflow_action import (
        ActionExecutionError,
        AnalysisActionProvider,
    )

    action = AnalysisActionProvider()

    # Test with invalid sample size formats
    parameters = {
        "series": "TABU/SAMPLE/BASE",
        "network": "asia",
        "sample_size": "invalid_size",
        "seeds": "0,1",
    }

    with pytest.raises(ActionExecutionError):
        action.run("graph-average", parameters, mode="dry-run")

    # Test with invalid seeds format
    parameters = {
        "series": "TABU/SAMPLE/BASE",
        "network": "asia",
        "sample_size": "10k",
        "seeds": "invalid,seeds",
    }

    with pytest.raises(ActionExecutionError):
        action.run("graph-average", parameters, mode="dry-run")


# Test that sample workflow definitions are functional
def test_sample_workflow_definitions():
    """Test that sample workflow definitions are functional."""
    # Test each workflow template can be parsed and contains expected elements
    workflows = [SIMPLE_WORKFLOW, MATRIX_WORKFLOW, PARAMETERIZED_WORKFLOW]

    for workflow_yaml in workflows:
        data = yaml.safe_load(workflow_yaml)

        # All workflows should have basic structure
        assert "description" in data
        assert "steps" in data
        assert len(data["steps"]) > 0

        # All steps should use causaliq-analysis
        for step in data["steps"]:
            if "uses" in step:
                assert step["uses"] == "causaliq-analysis"
            if "with" in step:
                assert step["with"]["action"] == "graph-average"


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
