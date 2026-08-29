"""Functional tests for action parameter name and value validation.

These tests verify that the AnalysisActionProvider correctly validates
parameter names and values for migrate_trace, evaluate_graph, and other
actions, ensuring clear error messages for invalid configurations.
"""

import pytest
from causaliq_core import ActionValidationError

from causaliq_analysis.workflow_action import AnalysisActionProvider

# =============================================================================
# migrate_trace parameter name validation
# =============================================================================


# Test migrate_trace rejects unknown parameter names.
def test_migrate_trace_rejects_unknown_parameter() -> None:
    """migrate_trace rejects unknown parameter names with clear error."""
    provider = AnalysisActionProvider()

    with pytest.raises(ActionValidationError) as exc_info:
        provider.validate_parameters(
            "migrate_trace",
            {
                "series": "TABU/BASE",
                "network": "asia",
                "unknown_param": "value",
            },
        )

    assert "Unknown parameter" in str(exc_info.value)
    assert "unknown_param" in str(exc_info.value)


# Test migrate_trace rejects multiple unknown parameters.
def test_migrate_trace_rejects_multiple_unknown_parameters() -> None:
    """migrate_trace lists all unknown parameters in error message."""
    provider = AnalysisActionProvider()

    with pytest.raises(ActionValidationError) as exc_info:
        provider.validate_parameters(
            "migrate_trace",
            {
                "series": "TABU/BASE",
                "network": "asia",
                "bad_param1": "value1",
                "bad_param2": "value2",
            },
        )

    error_msg = str(exc_info.value)
    assert "Unknown parameter" in error_msg
    assert "bad_param1" in error_msg
    assert "bad_param2" in error_msg


# Test migrate_trace accepts all valid parameter names.
def test_migrate_trace_accepts_all_valid_parameters() -> None:
    """migrate_trace accepts all documented parameter names."""
    provider = AnalysisActionProvider()

    # Should not raise - all parameters are valid
    provider.validate_parameters(
        "migrate_trace",
        {
            "traces": "/path/to/traces",
            "series": "TABU/BASE",
            "network": "asia",
            "sample_size": 1000,
            "seed": "0-2",  # Range syntax
            "root_dir": "/experiments",
            "output": "/output/results.db",
        },
    )


# =============================================================================
# migrate_trace parameter value validation
# =============================================================================


# Test migrate_trace validates sample_size must be numeric.
def test_migrate_trace_sample_size_must_be_numeric() -> None:
    """migrate_trace rejects non-numeric sample_size values."""
    provider = AnalysisActionProvider()

    with pytest.raises(ActionValidationError) as exc_info:
        provider.validate_parameters(
            "migrate_trace",
            {
                "traces": "/path",
                "sample_size": "not_a_number",
            },
        )

    assert "Invalid sample size" in str(exc_info.value)


# Test migrate_trace accepts various sample_size formats.
def test_migrate_trace_sample_size_formats() -> None:
    """migrate_trace accepts integer, string, and k/m suffix formats."""
    provider = AnalysisActionProvider()

    # Integer
    provider.validate_parameters(
        "migrate_trace", {"traces": "/path", "sample_size": 1000}
    )

    # String integer
    provider.validate_parameters(
        "migrate_trace", {"traces": "/path", "sample_size": "1000"}
    )

    # k suffix
    provider.validate_parameters(
        "migrate_trace", {"traces": "/path", "sample_size": "10k"}
    )

    # K suffix (uppercase)
    provider.validate_parameters(
        "migrate_trace", {"traces": "/path", "sample_size": "10K"}
    )


# Test migrate_trace validates seed format.
def test_migrate_trace_seed_must_be_valid_format() -> None:
    """migrate_trace rejects comma-separated seed formats."""
    provider = AnalysisActionProvider()

    with pytest.raises(ActionValidationError) as exc_info:
        provider.validate_parameters(
            "migrate_trace",
            {
                "traces": "/path",
                "seed": "0,1,2",
            },
        )

    assert "contains comma" in str(exc_info.value)


# Test migrate_trace accepts various seed formats.
def test_migrate_trace_seed_formats() -> None:
    """migrate_trace accepts single, list, and range seed formats."""
    provider = AnalysisActionProvider()

    # Single seed (integer)
    provider.validate_parameters(
        "migrate_trace", {"traces": "/path", "seed": 42}
    )

    # Range string
    provider.validate_parameters(
        "migrate_trace", {"traces": "/path", "seed": "0-24"}
    )

    # List of integers
    provider.validate_parameters(
        "migrate_trace", {"traces": "/path", "seed": [1, 2, 3]}
    )


# Test migrate_trace requires input source.
def test_migrate_trace_requires_input_source() -> None:
    """migrate_trace requires traces OR (series AND network)."""
    provider = AnalysisActionProvider()

    with pytest.raises(ActionValidationError) as exc_info:
        provider.validate_parameters("migrate_trace", {})

    assert "requires either" in str(exc_info.value)


# Test migrate_trace series without network is invalid.
def test_migrate_trace_series_requires_network() -> None:
    """migrate_trace with series requires network parameter."""
    provider = AnalysisActionProvider()

    with pytest.raises(ActionValidationError) as exc_info:
        provider.validate_parameters("migrate_trace", {"series": "TABU/BASE"})

    assert "requires either" in str(exc_info.value)


# =============================================================================
# evaluate_graph parameter name validation
# =============================================================================


# Test evaluate_graph rejects unknown parameter names.
def test_evaluate_graph_rejects_unknown_parameter() -> None:
    """evaluate_graph rejects unknown parameter names with clear error."""
    provider = AnalysisActionProvider()

    with pytest.raises(ActionValidationError) as exc_info:
        provider.validate_parameters(
            "evaluate_graph",
            {
                "reference": "ground_truth.graphml",
                "metric": ["f1"],
                "unknown_param": "value",
            },
        )

    assert "Unknown parameter" in str(exc_info.value)
    assert "unknown_param" in str(exc_info.value)


# Test evaluate_graph rejects bayesys parameter (removed).
def test_evaluate_graph_rejects_bayesys_parameter() -> None:
    """evaluate_graph no longer supports bayesys parameter."""
    provider = AnalysisActionProvider()

    with pytest.raises(ActionValidationError) as exc_info:
        provider.validate_parameters(
            "evaluate_graph",
            {
                "reference": "ground_truth.graphml",
                "metric": ["f1"],
                "bayesys": "3.0",
            },
        )

    assert "Unknown parameter" in str(exc_info.value)
    assert "bayesys" in str(exc_info.value)


# Test evaluate_graph accepts all valid parameter names.
def test_evaluate_graph_accepts_all_valid_parameters() -> None:
    """evaluate_graph accepts all documented parameter names."""
    provider = AnalysisActionProvider()

    # Should not raise - all parameters are valid
    provider.validate_parameters(
        "evaluate_graph",
        {
            "input": "results.db",
            "filter": "network == 'asia'",
            "metric": ["f1", "shd"],
            "reference": "ground_truth.graphml",
        },
    )


# =============================================================================
# evaluate_graph parameter value validation
# =============================================================================


# Test evaluate_graph requires reference parameter.
def test_evaluate_graph_requires_reference() -> None:
    """evaluate_graph requires reference parameter."""
    provider = AnalysisActionProvider()

    with pytest.raises(ActionValidationError) as exc_info:
        provider.validate_parameters(
            "evaluate_graph",
            {"metric": ["f1"]},
        )

    assert "requires 'reference'" in str(exc_info.value)


# Test evaluate_graph requires metric parameter.
def test_evaluate_graph_requires_metric() -> None:
    """evaluate_graph requires metric parameter."""
    provider = AnalysisActionProvider()

    with pytest.raises(ActionValidationError) as exc_info:
        provider.validate_parameters(
            "evaluate_graph",
            {"reference": "ground_truth.graphml"},
        )

    assert "requires 'metric'" in str(exc_info.value)


# Test evaluate_graph rejects invalid metric name.
def test_evaluate_graph_rejects_invalid_metric_name() -> None:
    """evaluate_graph rejects unknown metric names."""
    provider = AnalysisActionProvider()

    with pytest.raises(ActionValidationError) as exc_info:
        provider.validate_parameters(
            "evaluate_graph",
            {
                "reference": "ground_truth.graphml",
                "metric": "invalid_metric",
            },
        )

    assert "Invalid metric" in str(exc_info.value)


# Test evaluate_graph rejects invalid metric in list.
def test_evaluate_graph_rejects_invalid_metric_in_list() -> None:
    """evaluate_graph rejects unknown metric in a list of metrics."""
    provider = AnalysisActionProvider()

    with pytest.raises(ActionValidationError) as exc_info:
        provider.validate_parameters(
            "evaluate_graph",
            {
                "reference": "ground_truth.graphml",
                "metric": ["f1", "bad_metric", "shd"],
            },
        )

    assert "Invalid metric" in str(exc_info.value)
    assert "bad_metric" in str(exc_info.value)


# Test evaluate_graph rejects removed bayesys metrics.
def test_evaluate_graph_rejects_bayesys_metrics() -> None:
    """evaluate_graph rejects removed bayesys metric names."""
    provider = AnalysisActionProvider()

    bayesys_metrics = [
        "precision_b",
        "recall_b",
        "f1_b",
        "shd_b",
        "ddm",
        "bsf",
    ]

    for metric in bayesys_metrics:
        with pytest.raises(ActionValidationError) as exc_info:
            provider.validate_parameters(
                "evaluate_graph",
                {
                    "reference": "ground_truth.graphml",
                    "metric": metric,
                },
            )

        assert "Invalid metric" in str(exc_info.value)


# Test evaluate_graph accepts all valid metric names.
def test_evaluate_graph_accepts_all_valid_metrics() -> None:
    """evaluate_graph accepts all documented valid metric names."""
    provider = AnalysisActionProvider()

    valid_metrics = [
        "f1",
        "shd",
        "precision",
        "recall",
        "equiv.f1",
        "equiv.shd",
    ]

    # Test each individually
    for metric in valid_metrics:
        provider.validate_parameters(
            "evaluate_graph",
            {
                "reference": "ground_truth.graphml",
                "metric": metric,
            },
        )

    # Test all together as a list
    provider.validate_parameters(
        "evaluate_graph",
        {
            "reference": "ground_truth.graphml",
            "metric": valid_metrics,
        },
    )


# Test evaluate_graph metric can be string or list.
def test_evaluate_graph_metric_string_or_list() -> None:
    """evaluate_graph accepts metric as string or list."""
    provider = AnalysisActionProvider()

    # String
    provider.validate_parameters(
        "evaluate_graph",
        {
            "reference": "ground_truth.graphml",
            "metric": "f1",
        },
    )

    # List
    provider.validate_parameters(
        "evaluate_graph",
        {
            "reference": "ground_truth.graphml",
            "metric": ["f1", "shd"],
        },
    )


# =============================================================================
# merge_graphs parameter name validation
# =============================================================================


# Test merge_graphs rejects unknown parameter names.
def test_merge_graphs_rejects_unknown_parameter() -> None:
    """merge_graphs rejects unknown parameter names."""
    provider = AnalysisActionProvider()

    with pytest.raises(ActionValidationError) as exc_info:
        provider.validate_parameters(
            "merge_graphs",
            {
                "_aggregation_entries": [],
                "unknown_param": "value",
            },
        )

    assert "Unknown parameter" in str(exc_info.value)


# Test merge_graphs accepts all valid parameter names.
def test_merge_graphs_accepts_all_valid_parameters() -> None:
    """merge_graphs accepts all documented parameter names."""
    provider = AnalysisActionProvider()

    provider.validate_parameters(
        "merge_graphs",
        {
            "input": "results.db",
            "weights": {"score": {"bayesian_score": 1.0}},
            "object_type": "cpdag",
            "filter": "N >= 1000",
            "output": "pdg.db",
        },
    )


# =============================================================================
# best_graph parameter name validation
# =============================================================================


# Test best_graph rejects unknown parameter names.
def test_best_graph_rejects_unknown_parameter() -> None:
    """best_graph rejects unknown parameter names."""
    provider = AnalysisActionProvider()

    with pytest.raises(ActionValidationError) as exc_info:
        provider.validate_parameters(
            "best_graph",
            {
                "pdg_input": "pdg.graphml",
                "unknown_param": "value",
            },
        )

    assert "Unknown parameter" in str(exc_info.value)


# Test best_graph requires input.
def test_best_graph_requires_input() -> None:
    """best_graph requires input parameter."""
    provider = AnalysisActionProvider()

    with pytest.raises(ActionValidationError) as exc_info:
        provider.validate_parameters("best_graph", {})

    assert "requires 'input'" in str(exc_info.value)


# Test best_graph validates threshold type.
def test_best_graph_threshold_must_be_numeric() -> None:
    """best_graph threshold must be numeric."""
    provider = AnalysisActionProvider()

    with pytest.raises(ActionValidationError) as exc_info:
        provider.validate_parameters(
            "best_graph",
            {
                "input": "pdg.graphml",
                "threshold": "not_a_number",
            },
        )

    assert "must be a number" in str(exc_info.value)


# =============================================================================
# summarise parameter name validation
# =============================================================================


# Test summarise rejects unknown parameter names.
def test_summarise_rejects_unknown_parameter() -> None:
    """summarise rejects unknown parameter names."""
    provider = AnalysisActionProvider()

    with pytest.raises(ActionValidationError) as exc_info:
        provider.validate_parameters(
            "summarise",
            {
                "metric": ["f1.mean"],
                "unknown_param": "value",
            },
        )

    assert "Unknown parameter" in str(exc_info.value)


# Test summarise requires metric.
def test_summarise_requires_metric() -> None:
    """summarise requires at least one metric spec."""
    provider = AnalysisActionProvider()

    with pytest.raises(ActionValidationError) as exc_info:
        provider.validate_parameters("summarise", {"metric": []})

    assert "At least one metric" in str(exc_info.value)


# Test summarise validates metric spec format.
def test_summarise_metric_spec_format() -> None:
    """summarise metric specs must be <field>.<stat> format."""
    provider = AnalysisActionProvider()

    with pytest.raises(ActionValidationError) as exc_info:
        provider.validate_parameters(
            "summarise",
            {"metric": ["invalid_format"]},
        )

    assert "<field>.<stat>" in str(exc_info.value)


# =============================================================================
# plot parameter name validation
# =============================================================================


def _valid_plot_parameters() -> dict:
    """Return valid plot parameters for validation tests."""
    return {
        "input": "results.csv",
        "output": "chart.png",
        "type": "line",
        "subplot": "network",
        "group": "series",
        "x": "sample_size",
        "y": "f1.mean",
        "properties": ["xaxis.label=Sample size"],
    }


# Test plot rejects unknown parameter names.
def test_plot_rejects_unknown_parameter() -> None:
    """plot rejects unknown parameter names."""
    provider = AnalysisActionProvider()

    parameters = _valid_plot_parameters()
    parameters["unknown_param"] = "value"

    with pytest.raises(ActionValidationError) as exc_info:
        provider.validate_parameters("plot", parameters)

    assert "Unknown parameter" in str(exc_info.value)


# Test plot accepts all valid parameters.
def test_plot_accepts_all_valid_parameters() -> None:
    """plot accepts all valid parameter names."""
    provider = AnalysisActionProvider()

    provider.validate_parameters("plot", _valid_plot_parameters())


# Test plot requires input parameter.
def test_plot_requires_input() -> None:
    """plot requires the input parameter."""
    provider = AnalysisActionProvider()

    parameters = _valid_plot_parameters()
    del parameters["input"]

    with pytest.raises(ActionValidationError) as exc_info:
        provider.validate_parameters("plot", parameters)

    assert "requires 'input'" in str(exc_info.value)


# =============================================================================
# Cross-action validation
# =============================================================================

# =============================================================================
# Cross-action validation
# =============================================================================


# Test unsupported action raises clear error.
def test_unsupported_action_raises_clear_error() -> None:
    """Unsupported action names raise clear error message."""
    provider = AnalysisActionProvider()

    with pytest.raises(ActionValidationError) as exc_info:
        provider.validate_parameters("nonexistent_action", {})

    assert "does not support" in str(exc_info.value)


# Test action parameter is not counted as unknown.
def test_action_parameter_not_counted_as_unknown() -> None:
    """The 'action' parameter itself is not flagged as unknown."""
    provider = AnalysisActionProvider()

    # 'action' is passed by the workflow system but should not be
    # flagged as unknown
    provider.validate_parameters(
        "migrate_trace",
        {
            "action": "migrate_trace",
            "traces": "/path/to/traces",
        },
    )
