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
    from causaliq_analysis.workflow_action import CausalIQAnalysisAction

    action = CausalIQAnalysisAction()

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
        CausalIQAnalysisAction,
    )

    action = CausalIQAnalysisAction()

    # Test missing operation
    with pytest.raises(ActionExecutionError):
        action.run({}, mode="dry-run")

    # Test invalid operation
    with pytest.raises(ActionExecutionError, match="Unknown operation"):
        action.run({"operation": "invalid-op"}, mode="dry-run")

    # Test missing required parameters for graph-average
    with pytest.raises(ActionExecutionError):
        action.run({"operation": "graph-average"}, mode="dry-run")


# Test sample_size validation in workflow action
def test_workflow_action_sample_size_required():
    """Test that workflow action requires sample_size parameter."""
    from causaliq_analysis.workflow_action import (
        ActionExecutionError,
        CausalIQAnalysisAction,
    )

    action = CausalIQAnalysisAction()

    # Test missing sample_size (None) - should trigger the specific error
    inputs = {
        "operation": "graph-average",
        "series": "test_series",
        "network": "test_network",
        # sample_size is missing/None
    }

    with pytest.raises(ActionExecutionError, match="sample_size is required"):
        action.run(inputs, mode="dry-run")


# Test traces not found error in workflow action
def test_workflow_action_traces_not_found():
    """Test that workflow action handles case when no traces are found."""
    from unittest.mock import patch

    from causaliq_analysis.workflow_action import (
        ActionExecutionError,
        CausalIQAnalysisAction,
    )

    action = CausalIQAnalysisAction()

    # Valid inputs but traces won't be found
    inputs = {
        "operation": "graph-average",
        "series": "nonexistent_series",
        "network": "nonexistent_network",
        "sample_size": 1000,
        "seeds": "0",
    }

    # Mock Trace.read to return None (no traces found)
    with patch(
        "causaliq_analysis.workflow_action.Trace.read", return_value=None
    ):
        with pytest.raises(
            ActionExecutionError,
            match="No traces found for nonexistent_series/nonexistent_network",
        ):
            # Use "run" mode to actually try loading traces
            action.run(inputs, mode="run")


# Test different ways to specify trace file patterns
def test_workflow_traces_pattern_building(monkeypatch):
    """Test different ways to specify trace file patterns."""
    from causaliq_analysis.workflow_action import CausalIQAnalysisAction

    action = CausalIQAnalysisAction()

    class MockLogger:
        def log_task(self, message):
            pass

    mock_logger = MockLogger()

    # Test with direct traces pattern
    inputs = {
        "operation": "graph-average",
        "traces": "TABU/SAMPLE/BASE/asia.pkl.gz",
        "sample_size": "10k",
        "seeds": "0,1",
    }

    result = action.run(inputs, mode="dry-run", logger=mock_logger)
    assert result["status"] == "dry-run"

    # Test with series + network
    inputs = {
        "operation": "graph-average",
        "series": "TABU/SAMPLE/BASE",
        "network": "asia",
        "sample_size": "10k",
        "seeds": "0,1",
    }

    result = action.run(inputs, mode="dry-run", logger=mock_logger)
    assert result["status"] == "dry-run"


# Test automatic result path generation
def test_workflow_result_path_generation():
    """Test automatic result path generation."""
    from causaliq_analysis.workflow_action import CausalIQAnalysisAction

    action = CausalIQAnalysisAction()

    class MockLogger:
        def log_task(self, message):
            pass

    mock_logger = MockLogger()

    inputs = {
        "operation": "graph-average",
        "root_dir": "/test/experiments",
        "series": "TABU/SAMPLE/BASE",
        "network": "asia",
        "sample_size": "10k",
        "seeds": "0,1",
    }

    result = action.run(inputs, mode="dry-run", logger=mock_logger)

    # Should generate default output path
    # (normalize path separators for Windows)
    expected_path = "/test/experiments/TABU/SAMPLE/BASE/asia_10000.csv"
    actual_path = result["result_file"].replace("\\", "/")
    assert actual_path == expected_path


# Test that parameter values work with typical workflow templating
def test_workflow_parameter_expansion_compatibility():
    """Test that parameter values work with typical workflow templating."""
    from causaliq_analysis.workflow_action import CausalIQAnalysisAction

    action = CausalIQAnalysisAction()

    # Simulate template expansion
    expanded_inputs = {
        "operation": "graph-average",
        "series": "TABU/SAMPLE/BASE",
        "network": "asia",
        "sample_size": "10k",
        "result": "experiments/TABU/SAMPLE/BASE/asia_10k.csv",
        "seeds": "0,1",
    }

    class MockLogger:
        def log_task(self, message):
            pass

    mock_logger = MockLogger()

    result = action.run(expanded_inputs, mode="dry-run", logger=mock_logger)
    assert result["status"] == "dry-run"
    assert "asia_10k.csv" in result["result_file"]


# Test conservative execution behavior (skip if output exists)
def test_workflow_conservative_execution(monkeypatch):
    """Test conservative execution behavior (skip if output exists)."""
    import pandas as pd

    from causaliq_analysis.workflow_action import CausalIQAnalysisAction

    action = CausalIQAnalysisAction()

    with tempfile.TemporaryDirectory() as temp_dir:
        result_file = Path(temp_dir) / "existing_result.csv"
        result_file.write_text("existing,data\n1,2")

        inputs = {
            "operation": "graph-average",
            "series": "TABU/SAMPLE/BASE",
            "network": "asia",
            "sample_size": "10k",
            "seeds": "0,1",
            "result": str(result_file),
        }

        class MockLogger:
            def __init__(self):
                self.calls = []

            def log_task(self, message):
                self.calls.append(message)

        mock_logger = MockLogger()

        # Run mode should skip if output exists
        result = action.run(inputs, mode="run", logger=mock_logger)
        assert result["status"] == "skipped"

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

        from causaliq_analysis import workflow_action  # noqa: F401
        from causaliq_analysis.workflow_action import (
            CausalIQAnalysisAction as ReloadedAction,
        )

        action_reloaded = ReloadedAction()

        # Provide root_dir to avoid path validation before mock intercepts
        inputs["root_dir"] = temp_dir

        result = action_reloaded.run(
            inputs, mode="compare", logger=mock_logger
        )
        assert result["status"] == "success"
        assert result["num_graphs"] == 5  # Length of mock traces dict


# Test error handling in workflow execution
def test_workflow_error_handling():
    """Test error handling in workflow execution."""
    from causaliq_analysis.workflow_action import (
        ActionExecutionError,
        CausalIQAnalysisAction,
    )

    action = CausalIQAnalysisAction()

    # Test with invalid sample size formats
    inputs = {
        "operation": "graph-average",
        "series": "TABU/SAMPLE/BASE",
        "network": "asia",
        "sample_size": "invalid_size",
        "seeds": "0,1",
    }

    with pytest.raises(ActionExecutionError):
        action.run(inputs, mode="dry-run")

    # Test with invalid seeds format
    inputs = {
        "operation": "graph-average",
        "series": "TABU/SAMPLE/BASE",
        "network": "asia",
        "sample_size": "10k",
        "seeds": "invalid,seeds",
    }

    with pytest.raises(ActionExecutionError):
        action.run(inputs, mode="dry-run")


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
                assert step["with"]["operation"] == "graph-average"
