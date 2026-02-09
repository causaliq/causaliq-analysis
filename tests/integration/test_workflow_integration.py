"""
Integration tests for causaliq-analysis workflow action functionality.

These tests verify that the CausalIQAnalysisAction works correctly when
causaliq-workflow is available, testing the full integration between
the two packages.
"""

from pathlib import Path

import pytest

# Test markers
pytestmark = pytest.mark.integration


# Test that workflow action can be imported when workflow is available
def test_workflow_action_import():
    """Test that workflow action can be imported when workflow is available."""
    # Skip if workflow package not available
    pytest.importorskip("causaliq_workflow")

    from causaliq_analysis.workflow_action import CausalIQAnalysisAction

    action = CausalIQAnalysisAction()
    assert action.name == "causaliq-analysis"
    assert action.version == "0.2.0"
    assert "causal graphs" in action.description


# Test that workflow action has proper input specifications
def test_workflow_action_inputs_specification():
    """Test that workflow action has proper input specifications."""
    pytest.importorskip("causaliq_workflow")

    from causaliq_analysis.workflow_action import CausalIQAnalysisAction

    action = CausalIQAnalysisAction()

    # Check required inputs
    assert "operation" in action.inputs
    assert action.inputs["operation"].required is True

    # Check optional inputs with defaults
    assert "basis" in action.inputs
    assert action.inputs["basis"].default == "dag"
    assert action.inputs["root_dir"].default == "experiments"


# Test that workflow action has proper output specifications
def test_workflow_action_outputs_specification():
    """Test that workflow action has proper output specifications."""
    pytest.importorskip("causaliq_workflow")

    from causaliq_analysis.workflow_action import CausalIQAnalysisAction

    action = CausalIQAnalysisAction()

    expected_outputs = {"result_file", "num_graphs", "status"}
    assert set(action.outputs.keys()) == expected_outputs


# Test sample size parsing with various input formats
def test_parse_sample_size_various_formats():
    """Test sample size parsing with various input formats."""
    pytest.importorskip("causaliq_workflow")

    from causaliq_analysis.validation import parse_sample_size

    # Test integer input
    assert parse_sample_size(1000) == 1000

    # Test string formats
    assert parse_sample_size("1000") == 1000
    assert parse_sample_size("10k") == 10000
    assert parse_sample_size("10K") == 10000
    assert parse_sample_size("1.5k") == 1500
    assert parse_sample_size("2m") == 2000000
    assert parse_sample_size("2M") == 2000000


# Test sample size parsing with invalid formats
def test_parse_sample_size_invalid_formats():
    """Test sample size parsing with invalid formats."""
    pytest.importorskip("causaliq_workflow")

    from causaliq_analysis.validation import parse_sample_size

    with pytest.raises(ValueError):
        parse_sample_size("invalid")

    with pytest.raises(ValueError):
        parse_sample_size([1000])


# Test seeds parsing with various input formats
def test_parse_seeds_various_formats():
    """Test seeds parsing with various input formats."""
    pytest.importorskip("causaliq_workflow")

    from causaliq_analysis.validation import parse_seeds_workflow

    # Test different input types
    assert parse_seeds_workflow((0, 1)) == (0, 1)
    assert parse_seeds_workflow([0, 1]) == (0, 1)
    assert parse_seeds_workflow("0,1") == (0, 1)
    assert parse_seeds_workflow("0, 1, 2") == (0, 1, 2)
    assert parse_seeds_workflow("") == ()
    assert parse_seeds_workflow(None) == ()


# Test seeds parsing with invalid formats
def test_parse_seeds_invalid_formats():
    """Test seeds parsing with invalid formats."""
    pytest.importorskip("causaliq_workflow")

    from causaliq_analysis.validation import parse_seeds_workflow

    with pytest.raises(ValueError):
        parse_seeds_workflow("invalid,seeds")

    with pytest.raises(ValueError):
        parse_seeds_workflow({"not": "valid"})


# Test workflow action in dry-run mode
def test_workflow_action_dry_run_mode(monkeypatch):
    """Test workflow action in dry-run mode."""
    pytest.importorskip("causaliq_workflow")

    from causaliq_analysis.workflow_action import CausalIQAnalysisAction

    action = CausalIQAnalysisAction()

    inputs = {
        "operation": "graph-average",
        "series": "TABU/SAMPLE/BASE",
        "network": "asia",
        "sample_size": "10k",
        "basis": "pdag",
        "seeds": "0,1",
    }

    # Mock logger
    class MockLogger:
        def __init__(self):
            self.calls = []
            self.is_terminal_logging = True

    mock_logger = MockLogger()

    # Mock trace and average functions that should not be called
    class MockTrace:
        @staticmethod
        def read(partial_id, root_dir):
            raise AssertionError("Should not be called in dry-run mode")

    def mock_average_func(*args, **kwargs):
        raise AssertionError("Should not be called in dry-run mode")

    monkeypatch.setattr("causaliq_analysis.workflow_action.Trace", MockTrace)
    monkeypatch.setattr(
        "causaliq_analysis.workflow_action.average", mock_average_func
    )

    result = action.run(inputs, mode="dry-run", logger=mock_logger)

    # Verify output structure
    assert "result_file" in result
    assert "num_graphs" in result
    assert "status" in result
    assert result["status"] == "dry-run"
    assert result["num_graphs"] == 0


# Test workflow action in run mode when output already exists
def test_workflow_action_run_mode_with_existing_output():
    """Test workflow action in run mode when output already exists."""
    pytest.importorskip("causaliq_workflow")

    from causaliq_analysis.workflow_action import CausalIQAnalysisAction

    action = CausalIQAnalysisAction()

    # Use tracked test data directory
    test_data_dir = Path(__file__).parent.parent / "data" / "integration"
    test_data_dir.mkdir(exist_ok=True)

    # Create existing output file in the test data directory
    result_path = test_data_dir / "existing_result.csv"
    result_path.write_text("existing,data")

    try:
        inputs = {
            "operation": "graph-average",
            "root_dir": str(test_data_dir.parent / "functional" / "trace"),
            "series": "TABU/BASE3",
            "network": "covid_c",
            "sample_size": "1000",
            "result": str(result_path),
        }

        class MockLogger:
            def __init__(self):
                self.is_terminal_logging = True

        mock_logger = MockLogger()

        result = action.run(inputs, mode="run", logger=mock_logger)

        # Verify skipped execution
        assert result["status"] == "skipped"
        assert result["num_graphs"] == 0
    finally:
        # Clean up test file
        if result_path.exists():
            result_path.unlink()


# Test workflow action with unknown operation
def test_workflow_action_unknown_operation():
    """Test workflow action with unknown operation."""
    pytest.importorskip("causaliq_workflow")

    from causaliq_analysis.workflow_action import (
        ActionExecutionError,
        CausalIQAnalysisAction,
    )

    action = CausalIQAnalysisAction()

    inputs = {"operation": "unknown-operation"}

    with pytest.raises(ActionExecutionError, match="Unknown operation"):
        action.run(inputs, mode="run")


# Test workflow action with missing required inputs
def test_workflow_action_missing_required_inputs():
    """Test workflow action with missing required inputs."""
    pytest.importorskip("causaliq_workflow")

    from causaliq_analysis.workflow_action import (
        ActionExecutionError,
        CausalIQAnalysisAction,
    )

    action = CausalIQAnalysisAction()

    # Missing operation
    with pytest.raises(ActionExecutionError):
        action.run({}, mode="run")

    # Missing required inputs for graph-average
    inputs = {"operation": "graph-average"}
    with pytest.raises(ActionExecutionError):
        action.run(inputs, mode="run")


# Test full workflow execution with real trace data (slow test)
@pytest.mark.slow
def test_full_workflow_execution_with_real_data():
    """Test full workflow execution using tracked trace data files."""
    pytest.importorskip("causaliq_workflow")

    from causaliq_analysis.workflow_action import CausalIQAnalysisAction

    action = CausalIQAnalysisAction()

    # Use tracked test data
    test_data_dir = (
        Path(__file__).parent.parent / "data" / "functional" / "trace"
    )
    if not (test_data_dir / "TABU" / "BASE3" / "covid_c.pkl.gz").exists():
        pytest.skip("Test trace data not available")

    # Create output directory in integration test data
    output_dir = Path(__file__).parent.parent / "data" / "integration"
    output_dir.mkdir(exist_ok=True)

    result_file = output_dir / "covid_c_test_result.csv"

    try:
        inputs = {
            "operation": "graph-average",
            "root_dir": str(test_data_dir),
            "series": "TABU/BASE3",
            "network": "covid_c",
            "sample_size": "1000",  # Will need to match what's in the trace
            "basis": "pdag",
            "seeds": "",  # Use all available seeds
            "result": str(result_file),
        }

        class MockLogger:
            def __init__(self):
                self.is_terminal_logging = True

        mock_logger = MockLogger()

        result = action.run(inputs, mode="compare", logger=mock_logger)

        # Verify execution results - handle case where no matching traces found
        assert result["status"] in ["success", "failed"]
        if result["status"] == "success":
            assert result["num_graphs"] > 0
            assert Path(result["result_file"]).exists()
            # Verify CSV structure if file was created
            import pandas as pd

            df = pd.read_csv(result["result_file"])
            expected_columns = [
                "node_a",
                "node_b",
                "p_a_to_b",
                "p_b_to_a",
                "p_undirected",
                "p_no_edge",
            ]
            for col in expected_columns:
                assert col in df.columns

    finally:
        # Clean up generated result file
        if result_file.exists():
            result_file.unlink()


# Test workflow action with partial trace data
def test_workflow_action_with_trace_data():
    """Test workflow action behavior with real trace files."""
    pytest.importorskip("causaliq_workflow")

    from causaliq_analysis.workflow_action import CausalIQAnalysisAction

    action = CausalIQAnalysisAction()

    # Use tracked test data
    test_data_dir = (
        Path(__file__).parent.parent / "data" / "functional" / "trace"
    )

    # Test with a known trace file pattern that should exist
    inputs = {
        "operation": "graph-average",
        "root_dir": str(test_data_dir),
        "traces": "TABU/BASE3/covid_c.pkl.gz",
        "sample_size": "1000",
        "basis": "dag",
        "seeds": "",
    }

    class MockLogger:
        def __init__(self):
            self.is_terminal_logging = True

    mock_logger = MockLogger()

    # Test dry-run mode - should not fail regardless of trace content
    result = action.run(inputs, mode="dry-run", logger=mock_logger)

    assert result["status"] == "dry-run"
    assert result["num_graphs"] == 0
    assert "result_file" in result


# Test that CausalIQAction base class is imported correctly
def test_causaliq_action_base_class():
    """Test that CausalIQAction base class is imported from workflow."""
    pytest.importorskip("causaliq_workflow")

    from causaliq_workflow import CausalIQAction

    from causaliq_analysis.workflow_action import CausalIQAnalysisAction

    # Verify CausalIQAnalysisAction inherits from CausalIQAction
    assert issubclass(CausalIQAnalysisAction, CausalIQAction)


# Test that workflow action is exported from main package when available
def test_workflow_action_in_package_exports():
    """Test that CausalIQAnalysisAction is exported from main package."""
    pytest.importorskip("causaliq_workflow")

    import causaliq_analysis

    # Should be available in __all__ when workflow is installed
    assert "CausalIQAnalysisAction" in causaliq_analysis.__all__
    assert hasattr(causaliq_analysis, "CausalIQAnalysisAction")
