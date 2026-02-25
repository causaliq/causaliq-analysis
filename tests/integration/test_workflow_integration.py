"""
Integration tests for causaliq-analysis workflow action functionality.

These tests verify that the AnalysisActionProvider works correctly when
causaliq-workflow is available, testing the full integration between
the two packages.
"""

from pathlib import Path

import pytest

# Test markers
pytestmark = pytest.mark.integration


# Test that workflow action can be imported when workflow is available.
def test_workflow_action_import():
    """Test that workflow action can be imported when workflow is available."""
    # Skip if workflow package not available
    pytest.importorskip("causaliq_workflow")

    from causaliq_analysis.workflow_action import AnalysisActionProvider

    action = AnalysisActionProvider()
    assert action.name == "causaliq-analysis"
    assert action.version == "0.3.0"
    assert "causal graph" in action.description


# Test that workflow action has proper input specifications.
def test_workflow_action_inputs_specification():
    """Test that workflow action has proper input specifications."""
    pytest.importorskip("causaliq_workflow")

    from causaliq_analysis.workflow_action import AnalysisActionProvider

    action = AnalysisActionProvider()

    # Check required inputs
    assert "action" in action.inputs
    assert action.inputs["action"].required is True

    # Check optional inputs with defaults
    assert action.inputs["root_dir"].default == "experiments"


# Test that workflow action has proper output specifications.
def test_workflow_action_outputs_specification():
    """Test that workflow action has proper output specifications."""
    pytest.importorskip("causaliq_workflow")

    from causaliq_analysis.workflow_action import AnalysisActionProvider

    action = AnalysisActionProvider()

    # Check core outputs exist
    core_outputs = {"num_graphs", "status", "skipped"}
    assert core_outputs.issubset(set(action.outputs.keys()))


# Test sample size parsing with various input formats.
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


# Test sample size parsing with invalid formats.
def test_parse_sample_size_invalid_formats():
    """Test sample size parsing with invalid formats."""
    pytest.importorskip("causaliq_workflow")

    from causaliq_analysis.validation import parse_sample_size

    with pytest.raises(ValueError):
        parse_sample_size("invalid")

    with pytest.raises(ValueError):
        parse_sample_size([1000])


# Test seeds parsing with various input formats.
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


# Test seeds parsing with invalid formats.
def test_parse_seeds_invalid_formats():
    """Test seeds parsing with invalid formats."""
    pytest.importorskip("causaliq_workflow")

    from causaliq_analysis.validation import parse_seeds_workflow

    with pytest.raises(ValueError):
        parse_seeds_workflow("invalid,seeds")

    with pytest.raises(ValueError):
        parse_seeds_workflow({"not": "valid"})


# Test workflow action with unknown action.
def test_workflow_action_unknown_action():
    """Test workflow action with unknown action."""
    pytest.importorskip("causaliq_workflow")

    from causaliq_analysis.workflow_action import (
        ActionExecutionError,
        AnalysisActionProvider,
    )

    action = AnalysisActionProvider()

    with pytest.raises(ActionExecutionError, match="Unknown action"):
        action.run("unknown-action", {}, mode="run")


# Test workflow action with missing required parameters.
def test_workflow_action_missing_required_parameters():
    """Test workflow action with missing required parameters."""
    pytest.importorskip("causaliq_workflow")

    from causaliq_analysis.workflow_action import (
        ActionExecutionError,
        AnalysisActionProvider,
    )

    action = AnalysisActionProvider()

    # Missing required parameters for migrate_trace
    with pytest.raises(ActionExecutionError, match="Must provide"):
        action.run("migrate_trace", {}, mode="run")


# Test that CausalIQActionProvider base class is imported correctly.
def test_causaliq_action_provider_class():
    """Test that CausalIQActionProvider base class is imported from core."""
    pytest.importorskip("causaliq_workflow")

    from causaliq_core import CausalIQActionProvider

    from causaliq_analysis.workflow_action import AnalysisActionProvider

    # Verify AnalysisActionProvider inherits from CausalIQActionProvider
    assert issubclass(AnalysisActionProvider, CausalIQActionProvider)


# Test that workflow action is exported from main package when available.
def test_workflow_action_in_package_exports():
    """Test that ActionProvider is exported from main package."""
    pytest.importorskip("causaliq_workflow")

    import causaliq_analysis

    # Should be available in __all__ when workflow is installed
    assert "ActionProvider" in causaliq_analysis.__all__
    assert hasattr(causaliq_analysis, "ActionProvider")
    assert "AnalysisActionProvider" in causaliq_analysis.__all__
    assert hasattr(causaliq_analysis, "AnalysisActionProvider")


# Test migrate_trace in dry-run mode via workflow action.
def test_migrate_trace_workflow_dry_run():
    """Test migrate_trace action in dry-run mode."""
    pytest.importorskip("causaliq_workflow")

    from causaliq_analysis.workflow_action import AnalysisActionProvider

    action = AnalysisActionProvider()

    parameters = {
        "series": "TABU/STD",
        "network": "asia",
    }

    class MockLogger:
        is_terminal_logging = True

    result = action.run(
        "migrate_trace", parameters, mode="dry-run", logger=MockLogger()
    )
    status, metadata, objects = result

    assert status == "skipped"
    assert "Dry-run mode" in metadata["message"]


# Test migrate_trace workflow action with real trace data.
def test_migrate_trace_workflow_real_data():
    """Test migrate_trace action with real trace files."""
    pytest.importorskip("causaliq_workflow")

    from causaliq_analysis.workflow_action import AnalysisActionProvider

    action = AnalysisActionProvider()

    # Use tracked test data
    test_data_dir = (
        Path(__file__).parent.parent / "data" / "functional" / "trace"
    )

    parameters = {
        "root_dir": str(test_data_dir),
        "series": "TABU/STD",
        "network": "asia",
        "sample_size": 1000,
    }

    class MockLogger:
        is_terminal_logging = True

    result = action.run(
        "migrate_trace", parameters, mode="run", logger=MockLogger()
    )
    status, metadata, objects = result

    assert status == "success"
    assert metadata["num_graphs"] > 0
    assert len(objects) > 0
    assert objects[0]["type"] == "graphml"
