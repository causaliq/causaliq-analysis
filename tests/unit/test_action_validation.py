"""Unit tests for validate_parameters method with mocked dependencies."""

from unittest.mock import MagicMock

import pytest


def test_validate_parameters_unsupported_action() -> None:
    """Unsupported action name raises ActionValidationError."""
    from causaliq_core import ActionValidationError

    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()

    with pytest.raises(ActionValidationError, match="does not support"):
        provider.validate_parameters("unknown_action", {})


# Test migrate_trace validation requires traces or series+network.
def test_validate_migrate_trace_requires_input() -> None:
    """migrate_trace requires traces OR (series AND network)."""
    from causaliq_core import ActionValidationError

    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()

    with pytest.raises(ActionValidationError, match="requires either"):
        provider.validate_parameters("migrate_trace", {})


# Test migrate_trace accepts traces parameter.
def test_validate_migrate_trace_with_traces() -> None:
    """migrate_trace passes validation with traces parameter."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    # Should not raise
    provider.validate_parameters("migrate_trace", {"traces": "/path/to/dir"})


# Test migrate_trace accepts series and network.
def test_validate_migrate_trace_with_series_network() -> None:
    """migrate_trace passes validation with series and network."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    # Should not raise
    provider.validate_parameters(
        "migrate_trace",
        {"series": "TABU/BASE", "network": "asia"},
    )


# Test migrate_trace validates sample_size format.
def test_validate_migrate_trace_invalid_sample_size() -> None:
    """migrate_trace rejects invalid sample_size format."""
    from causaliq_core import ActionValidationError

    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()

    with pytest.raises(ActionValidationError, match="Invalid sample size"):
        provider.validate_parameters(
            "migrate_trace",
            {"traces": "/path", "sample_size": "invalid"},
        )


# Test migrate_trace validates seed format.
def test_validate_migrate_trace_invalid_seed() -> None:
    """migrate_trace rejects invalid seed format (comma-separated)."""
    from causaliq_core import ActionValidationError

    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()

    with pytest.raises(ActionValidationError, match="contains comma"):
        provider.validate_parameters(
            "migrate_trace",
            {"traces": "/path", "seed": "0,1,2"},
        )


# Test merge_graphs validation requires aggregation entries or input.
def test_validate_merge_graphs_requires_input() -> None:
    """merge_graphs requires _aggregation_entries OR input."""
    from causaliq_core import ActionValidationError

    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()

    with pytest.raises(ActionValidationError, match="requires either"):
        provider.validate_parameters("merge_graphs", {})


# Test merge_graphs accepts aggregation entries.
def test_validate_merge_graphs_with_aggregation() -> None:
    """merge_graphs passes validation with aggregation entries."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    # Should not raise
    provider.validate_parameters(
        "merge_graphs",
        {"_aggregation_entries": [{"entry": MagicMock()}]},
    )


# Test merge_graphs validates filter syntax.
def test_validate_merge_graphs_invalid_filter() -> None:
    """merge_graphs rejects invalid filter expression syntax."""
    from causaliq_core import ActionValidationError

    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()

    with pytest.raises(ActionValidationError, match="Invalid filter"):
        provider.validate_parameters(
            "merge_graphs",
            {"_aggregation_entries": [], "filter": "x =="},
        )


# Test merge_graphs validates weight spec.
def test_validate_merge_graphs_invalid_weights() -> None:
    """merge_graphs rejects invalid weight specification."""
    from causaliq_core import ActionValidationError

    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()

    with pytest.raises(ActionValidationError, match="Invalid weight"):
        provider.validate_parameters(
            "merge_graphs",
            {"_aggregation_entries": [], "weights": {"field": "not_a_dict"}},
        )


# Test evaluate_graph validation requires reference.
def test_validate_evaluate_graph_requires_reference() -> None:
    """evaluate_graph requires reference parameter."""
    from causaliq_core import ActionValidationError

    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()

    with pytest.raises(ActionValidationError, match="requires 'reference'"):
        provider.validate_parameters("evaluate_graph", {})


# Test evaluate_graph validation requires metric.
def test_validate_evaluate_graph_requires_metric() -> None:
    """evaluate_graph requires metric parameter."""
    from causaliq_core import ActionValidationError

    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()

    with pytest.raises(ActionValidationError, match="requires 'metric'"):
        provider.validate_parameters(
            "evaluate_graph", {"reference": "ground_truth.graphml"}
        )


# Test evaluate_graph passes with reference and metric.
def test_validate_evaluate_graph_with_reference() -> None:
    """evaluate_graph passes validation with reference and metric."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    # Should not raise
    provider.validate_parameters(
        "evaluate_graph",
        {"reference": "ground_truth.graphml", "metric": ["f1"]},
    )


# Test best_graph validation requires input.
def test_validate_best_graph_requires_input() -> None:
    """best_graph requires input parameter."""
    from causaliq_core import ActionValidationError

    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()

    with pytest.raises(ActionValidationError, match="requires 'input'"):
        provider.validate_parameters("best_graph", {})


# Test best_graph validates threshold type.
def test_validate_best_graph_invalid_threshold() -> None:
    """best_graph rejects non-numeric threshold."""
    from causaliq_core import ActionValidationError

    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()

    with pytest.raises(ActionValidationError, match="must be a number"):
        provider.validate_parameters(
            "best_graph",
            {"input": "pdg.graphml", "threshold": "invalid"},
        )


# Test best_graph validates filter expression syntax.
def test_validate_best_graph_filter_expression() -> None:
    """best_graph validates filter expression syntax."""
    from causaliq_core import ActionValidationError

    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()

    with pytest.raises(
        ActionValidationError, match="Invalid filter expression"
    ):
        provider.validate_parameters(
            "best_graph",
            {"input": "cache.db", "filter": "invalid [ expression"},
        )


# Test migrate_trace output must be .db.
def test_validate_migrate_trace_output_must_be_db() -> None:
    """migrate_trace output must be a workflow cache (.db)."""
    from causaliq_core import ActionValidationError

    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()

    with pytest.raises(
        ActionValidationError, match="must be a workflow cache"
    ):
        provider.validate_parameters(
            "migrate_trace",
            {"traces": "/path", "output": "output.csv"},
        )


# Test merge_graphs output must be .db.
def test_validate_merge_graphs_output_must_be_db() -> None:
    """merge_graphs output must be a workflow cache (.db)."""
    from causaliq_core import ActionValidationError

    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()

    with pytest.raises(
        ActionValidationError, match="must be a workflow cache"
    ):
        provider.validate_parameters(
            "merge_graphs",
            {"input": "cache.db", "output": "output.graphml"},
        )


# Test merge_graphs rejects invalid strategy.
def test_validate_merge_graphs_invalid_strategy() -> None:
    """merge_graphs rejects an invalid strategy value."""
    from causaliq_core import ActionValidationError

    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()

    with pytest.raises(ActionValidationError, match="strategy must be"):
        provider.validate_parameters(
            "merge_graphs",
            {"input": "cache.db", "strategy": "bayesian"},
        )


# Test summarise validation requires metric.
def test_validate_summarise_requires_metric() -> None:
    """summarise requires metric parameter."""
    from causaliq_core import ActionValidationError

    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()

    with pytest.raises(ActionValidationError, match="At least one metric"):
        provider.validate_parameters("summarise", {"metric": []})


# Test summarise validates metric spec format.
def test_validate_summarise_invalid_metric_spec() -> None:
    """summarise rejects metric spec without dot."""
    from causaliq_core import ActionValidationError

    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()

    with pytest.raises(ActionValidationError, match="must be <field>.<stat>"):
        provider.validate_parameters(
            "summarise",
            {"metric": ["invalid_metric"]},
        )


# Test summarise requires output parameter.
def test_validate_summarise_requires_output() -> None:
    """summarise validation requires output parameter."""
    from causaliq_core import ActionValidationError

    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()

    with pytest.raises(ActionValidationError, match="requires 'output'"):
        provider.validate_parameters(
            "summarise",
            {"metric": ["f1.mean"], "_aggregation_entries": []},
        )


# Test summarise validates filter syntax.
def test_validate_summarise_invalid_filter() -> None:
    """summarise rejects invalid filter expression syntax."""
    from causaliq_core import ActionValidationError

    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()

    with pytest.raises(ActionValidationError, match="Invalid filter"):
        provider.validate_parameters(
            "summarise",
            {"metric": ["f1.mean"], "filter": "invalid =="},
        )


# Test unknown parameter raises validation error.
def test_validate_unknown_parameter_rejected() -> None:
    """Test that unknown parameters are rejected with clear error."""
    from causaliq_core import ActionValidationError

    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()

    with pytest.raises(ActionValidationError, match="Unknown parameter"):
        provider.validate_parameters(
            "migrate_trace",
            {"series": "TEST", "network": "asia", "unknown_param": "value"},
        )


# Test evaluate_graph rejects invalid metric names.
def test_validate_evaluate_graph_invalid_metric_name() -> None:
    """evaluate_graph rejects invalid metric names."""
    from causaliq_core import ActionValidationError

    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()

    with pytest.raises(ActionValidationError, match="Invalid metric"):
        provider.validate_parameters(
            "evaluate_graph",
            {"reference": "ground_truth.graphml", "metric": "invalid_metric"},
        )


# Test evaluate_graph rejects invalid metric in list.
def test_validate_evaluate_graph_invalid_metric_in_list() -> None:
    """evaluate_graph rejects invalid metric names in a list."""
    from causaliq_core import ActionValidationError

    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()

    with pytest.raises(ActionValidationError, match="Invalid metric.*eqx"):
        provider.validate_parameters(
            "evaluate_graph",
            {"reference": "ground_truth.graphml", "metric": ["f1", "eqx"]},
        )


# Test evaluate_graph accepts equiv.f1 metric.
def test_validate_evaluate_graph_equiv_f1() -> None:
    """evaluate_graph accepts equiv.f1 metric."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    # Should not raise
    provider.validate_parameters(
        "evaluate_graph",
        {"reference": "ground_truth.graphml", "metric": "equiv.f1"},
    )


# Test evaluate_graph accepts equiv.shd metric.
def test_validate_evaluate_graph_equiv_shd() -> None:
    """evaluate_graph accepts equiv.shd metric."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    # Should not raise
    provider.validate_parameters(
        "evaluate_graph",
        {"reference": "ground_truth.graphml", "metric": "equiv.shd"},
    )


# Test evaluate_graph accepts all valid metrics together.
def test_validate_evaluate_graph_all_valid_metrics() -> None:
    """evaluate_graph accepts all valid metrics in a list."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    # Should not raise
    provider.validate_parameters(
        "evaluate_graph",
        {
            "reference": "ground_truth.graphml",
            "metric": [
                "f1",
                "shd",
                "precision",
                "recall",
                "equiv.f1",
                "equiv.shd",
            ],
        },
    )
