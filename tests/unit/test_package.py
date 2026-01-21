"""
Unit tests for causaliq-analysis package behavior and imports.

These tests verify package-level functionality including graceful
degradation when optional dependencies are not available.
"""

import sys

import pytest


# Test package gracefully handles missing causaliq-workflow dependency
def test_package_graceful_degradation_without_workflow(monkeypatch):
    """Test package works without causaliq-workflow installed."""

    # Mock the import to make workflow_action import fail
    import builtins

    original_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        # Make the workflow_action module import fail to simulate \
        # missing causaliq-workflow
        if name == "causaliq_analysis.workflow_action":
            raise ImportError("No module named 'causaliq_workflow'")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", mock_import)

    # Remove causaliq_analysis modules from cache to force fresh import
    modules_to_remove = [
        m for m in sys.modules.keys() if m.startswith("causaliq_analysis")
    ]
    for module in modules_to_remove:
        monkeypatch.delitem(sys.modules, module)

    # Import should succeed but without workflow integration
    import causaliq_analysis

    # Core functionality should be available
    assert hasattr(causaliq_analysis, "average")
    assert hasattr(causaliq_analysis, "_validate_average_params")
    assert "average" in causaliq_analysis.__all__
    assert "_validate_average_params" in causaliq_analysis.__all__

    # Workflow integration should not be available
    assert "CausalIQAction" not in causaliq_analysis.__all__
    assert not hasattr(causaliq_analysis, "CausalIQAction")


# Test package properly exports workflow integration when available
def test_package_includes_workflow_when_available():
    """Test package includes workflow integration when \
causaliq-workflow is available."""
    # This test runs when causaliq-workflow is actually available
    pytest.importorskip("causaliq_workflow")

    import causaliq_analysis

    # Core functionality should be available
    assert hasattr(causaliq_analysis, "average")
    assert hasattr(causaliq_analysis, "_validate_average_params")

    # Workflow integration should also be available
    assert hasattr(causaliq_analysis, "CausalIQAction")
    assert "CausalIQAction" in causaliq_analysis.__all__


# Test package version and metadata are always available
def test_package_metadata():
    """Test package metadata is always available."""
    import causaliq_analysis

    # Basic metadata should always be present
    assert hasattr(causaliq_analysis, "__version__")
    assert hasattr(causaliq_analysis, "__author__")
    assert hasattr(causaliq_analysis, "__email__")
    assert hasattr(causaliq_analysis, "VERSION")

    # Should be in __all__ exports
    assert "__version__" in causaliq_analysis.__all__
    assert "__author__" in causaliq_analysis.__all__
    assert "__email__" in causaliq_analysis.__all__
    assert "VERSION" in causaliq_analysis.__all__

    # Version should be a valid string
    assert isinstance(causaliq_analysis.__version__, str)
    assert len(causaliq_analysis.__version__) > 0

    # VERSION should be a tuple
    assert isinstance(causaliq_analysis.VERSION, tuple)
    assert len(causaliq_analysis.VERSION) >= 2


# Test core graph functionality is always available
def test_core_graph_functionality():
    """Test core graph functionality is always available."""
    import causaliq_analysis

    # Core graph functions should be available
    from causaliq_analysis import _validate_average_params, average

    # Should be callable
    assert callable(average)
    assert callable(_validate_average_params)

    # Should be in exports
    assert "average" in causaliq_analysis.__all__
    assert "_validate_average_params" in causaliq_analysis.__all__


# Test workflow_action module import with successful causaliq_workflow imports
def test_workflow_action_successful_imports(monkeypatch):
    """Test workflow_action module when causaliq_workflow imports succeed."""
    import sys
    from unittest.mock import MagicMock

    # Create mock classes
    mock_action = MagicMock()
    mock_action_execution_error = MagicMock()
    mock_action_input = MagicMock()
    mock_workflow_logger = MagicMock()
    mock_workflow_context = MagicMock()

    # Mock the causaliq_workflow modules to simulate successful imports
    monkeypatch.setitem(sys.modules, "causaliq_workflow", MagicMock())
    monkeypatch.setitem(
        sys.modules,
        "causaliq_workflow.action",
        MagicMock(
            Action=mock_action,
            ActionExecutionError=mock_action_execution_error,
            ActionInput=mock_action_input,
        ),
    )
    monkeypatch.setitem(
        sys.modules,
        "causaliq_workflow.logger",
        MagicMock(WorkflowLogger=mock_workflow_logger),
    )
    monkeypatch.setitem(
        sys.modules,
        "causaliq_workflow.registry",
        MagicMock(WorkflowContext=mock_workflow_context),
    )

    # Remove workflow_action from cache if it exists
    workflow_action_module = "causaliq_analysis.workflow_action"
    if workflow_action_module in sys.modules:
        monkeypatch.delitem(sys.modules, workflow_action_module)

    # Import should succeed with WORKFLOW_AVAILABLE = True
    import causaliq_analysis.workflow_action as workflow_action

    # Verify successful import path was taken (lines 36-39 covered)
    assert workflow_action.WORKFLOW_AVAILABLE is True

    # Verify the workflow action class is available
    assert hasattr(workflow_action, "CausalIQAnalysisAction")
    assert hasattr(workflow_action, "CausalIQAction")
