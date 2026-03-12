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
    assert action.version == "0.4.0"
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

    from causaliq_core import ActionValidationError

    from causaliq_analysis.workflow_action import AnalysisActionProvider

    action = AnalysisActionProvider()

    with pytest.raises(ActionValidationError, match="does not support action"):
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


# Test merge_graphs with aggregation mode end-to-end.
def test_merge_graphs_aggregation_end_to_end(
    tmp_path: "pytest.TempPathFactory",
) -> None:
    """Test merge_graphs aggregation with workflow cache input."""
    pytest.importorskip("causaliq_workflow")

    from io import StringIO

    from causaliq_core.graph import DAG
    from causaliq_core.graph.io import graphml
    from causaliq_workflow.cache import CacheEntry, WorkflowCache

    from causaliq_analysis.workflow_action import AnalysisActionProvider

    # Create cache with multiple graph entries
    cache_path = tmp_path / "graphs.db"
    dag1 = DAG(["A", "B"], [("A", "->", "B")])
    dag2 = DAG(["A", "B"], [("B", "->", "A")])

    with WorkflowCache(cache_path) as cache:
        # Entry 1: A -> B
        buffer = StringIO()
        graphml.write(dag1, buffer)
        entry1 = CacheEntry(
            metadata={"algorithm": "pc", "sample_size": 1000},
        )
        entry1.add_object("graph", "graphml", buffer.getvalue())
        cache.put({"network": "asia", "seed": 1}, entry1)

        # Entry 2: B -> A
        buffer = StringIO()
        graphml.write(dag2, buffer)
        entry2 = CacheEntry(
            metadata={"algorithm": "pc", "sample_size": 1000},
        )
        entry2.add_object("graph", "graphml", buffer.getvalue())
        cache.put({"network": "asia", "seed": 2}, entry2)

    # Build aggregation entries as workflow would
    aggregation_entries = []
    with WorkflowCache(cache_path) as cache:
        for entry_info in cache.list_entries():
            matrix_values = entry_info.get("matrix_values", {})
            entry = cache.get(matrix_values)
            aggregation_entries.append(
                {
                    "matrix_values": matrix_values,
                    "metadata": dict(entry.metadata),
                    "cache_path": str(cache_path),
                    "entry": entry,
                }
            )

    action = AnalysisActionProvider()
    parameters = {
        "input": [str(cache_path)],
        "_aggregation_entries": aggregation_entries,
    }

    status, metadata, objects = action.run(
        "merge_graphs", parameters, mode="run"
    )

    assert status == "success"
    assert metadata["num_graphs"] == 2
    assert metadata["aggregation_mode"] is True
    assert metadata["source_count"] == 2
    assert metadata["action"] == "merge_graphs"
    assert "timestamp" in metadata

    # Verify merged PDG
    pdg = graphml.read_pdg(StringIO(objects[0]["content"]))
    probs = pdg.get_probabilities("A", "B")
    assert probs.forward == pytest.approx(0.5)
    assert probs.backward == pytest.approx(0.5)


# Test merge_graphs aggregation with filter.
def test_merge_graphs_aggregation_with_filter(
    tmp_path: "pytest.TempPathFactory",
) -> None:
    """Test merge_graphs aggregation respects pre-filtered entries."""
    pytest.importorskip("causaliq_workflow")

    from io import StringIO

    from causaliq_core.graph import DAG
    from causaliq_core.graph.io import graphml
    from causaliq_workflow.cache import CacheEntry, WorkflowCache

    from causaliq_analysis.workflow_action import AnalysisActionProvider

    cache_path = tmp_path / "graphs.db"
    dag = DAG(["A", "B"], [("A", "->", "B")])

    with WorkflowCache(cache_path) as cache:
        for status in ["completed", "completed", "failed"]:
            buffer = StringIO()
            graphml.write(dag, buffer)
            entry = CacheEntry(metadata={"status": status})
            entry.add_object("graph", "graphml", buffer.getvalue())
            cache.put(
                {"network": "asia", "run": len(cache.list_entries())},
                entry,
            )

    # Simulate workflow filtering - only completed entries
    aggregation_entries = []
    with WorkflowCache(cache_path) as cache:
        for entry_info in cache.list_entries():
            matrix_values = entry_info.get("matrix_values", {})
            entry = cache.get(matrix_values)
            if entry.metadata.get("status") == "completed":
                aggregation_entries.append(
                    {
                        "matrix_values": matrix_values,
                        "metadata": dict(entry.metadata),
                        "cache_path": str(cache_path),
                        "entry": entry,
                    }
                )

    action = AnalysisActionProvider()
    parameters = {
        "input": [str(cache_path)],
        "filter": "status == 'completed'",
        "_aggregation_entries": aggregation_entries,
    }

    status, metadata, objects = action.run(
        "merge_graphs", parameters, mode="run"
    )

    assert status == "success"
    # Only 2 completed entries, not 3
    assert metadata["num_graphs"] == 2
    assert metadata["filter"] == "status == 'completed'"


# Test merge_graphs aggregation with metadata-driven weights.
def test_merge_graphs_aggregation_with_weights(
    tmp_path: "pytest.TempPathFactory",
) -> None:
    """Test merge_graphs with metadata-driven weighting."""
    pytest.importorskip("causaliq_workflow")

    from io import StringIO

    from causaliq_core.graph import DAG
    from causaliq_core.graph.io import graphml
    from causaliq_workflow.cache import CacheEntry, WorkflowCache

    from causaliq_analysis.workflow_action import AnalysisActionProvider

    cache_path = tmp_path / "graphs.db"
    dag1 = DAG(["A", "B"], [("A", "->", "B")])
    dag2 = DAG(["A", "B"], [("B", "->", "A")])

    with WorkflowCache(cache_path) as cache:
        # PC algorithm - weight 1.0
        buffer = StringIO()
        graphml.write(dag1, buffer)
        entry1 = CacheEntry(metadata={"algorithm": "pc"})
        entry1.add_object("graph", "graphml", buffer.getvalue())
        cache.put({"network": "asia", "seed": 1}, entry1)

        # FCI algorithm - weight 0.5
        buffer = StringIO()
        graphml.write(dag2, buffer)
        entry2 = CacheEntry(metadata={"algorithm": "fci"})
        entry2.add_object("graph", "graphml", buffer.getvalue())
        cache.put({"network": "asia", "seed": 2}, entry2)

    aggregation_entries = []
    with WorkflowCache(cache_path) as cache:
        for entry_info in cache.list_entries():
            matrix_values = entry_info.get("matrix_values", {})
            entry = cache.get(matrix_values)
            aggregation_entries.append(
                {
                    "matrix_values": matrix_values,
                    "metadata": dict(entry.metadata),
                    "cache_path": str(cache_path),
                    "entry": entry,
                }
            )

    action = AnalysisActionProvider()
    # Weight spec: pc=1.0, fci=0.5 -> normalised: 0.667, 0.333
    weight_spec = {"algorithm": {"pc": 1.0, "fci": 0.5}}
    parameters = {
        "input": [str(cache_path)],
        "weights": weight_spec,
        "_aggregation_entries": aggregation_entries,
    }

    status, metadata, objects = action.run(
        "merge_graphs", parameters, mode="run"
    )

    assert status == "success"
    assert metadata["weights_spec"] == weight_spec
    assert "weights_computed" in metadata

    # pc (A->B) has weight 2/3, fci (B->A) has weight 1/3
    pdg = graphml.read_pdg(StringIO(objects[0]["content"]))
    probs = pdg.get_probabilities("A", "B")
    assert probs.forward == pytest.approx(2.0 / 3.0, abs=1e-3)
    assert probs.backward == pytest.approx(1.0 / 3.0, abs=1e-3)


# Test merge_graphs provenance tracks source caches.
def test_merge_graphs_provenance_source_caches(
    tmp_path: "pytest.TempPathFactory",
) -> None:
    """Test provenance metadata includes source cache information."""
    pytest.importorskip("causaliq_workflow")

    from io import StringIO

    from causaliq_core.graph import DAG
    from causaliq_core.graph.io import graphml
    from causaliq_workflow.cache import CacheEntry, WorkflowCache

    from causaliq_analysis.workflow_action import AnalysisActionProvider

    # Create two separate caches
    cache1_path = tmp_path / "pc_results.db"
    cache2_path = tmp_path / "ges_results.db"

    dag = DAG(["A", "B"], [("A", "->", "B")])

    for cache_path in [cache1_path, cache2_path]:
        with WorkflowCache(cache_path) as cache:
            buffer = StringIO()
            graphml.write(dag, buffer)
            entry = CacheEntry(metadata={"source": str(cache_path.name)})
            entry.add_object("graph", "graphml", buffer.getvalue())
            cache.put({"network": "asia"}, entry)

    # Combine entries from both caches
    aggregation_entries = []
    for cache_path in [cache1_path, cache2_path]:
        with WorkflowCache(cache_path) as cache:
            for entry_info in cache.list_entries():
                matrix_values = entry_info.get("matrix_values", {})
                entry = cache.get(matrix_values)
                aggregation_entries.append(
                    {
                        "matrix_values": matrix_values,
                        "metadata": dict(entry.metadata),
                        "cache_path": str(cache_path),
                        "entry": entry,
                    }
                )

    action = AnalysisActionProvider()
    parameters = {
        "input": [str(cache1_path), str(cache2_path)],
        "_aggregation_entries": aggregation_entries,
    }

    status, metadata, objects = action.run(
        "merge_graphs", parameters, mode="run"
    )

    assert status == "success"
    assert metadata["source_count"] == 2
    assert "source_caches" in metadata
    assert len(metadata["source_caches"]) == 2
