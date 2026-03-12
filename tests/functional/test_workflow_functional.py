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
    from causaliq_core import ActionValidationError

    from causaliq_analysis.workflow_action import AnalysisActionProvider

    action = AnalysisActionProvider()

    # Test invalid action
    with pytest.raises(ActionValidationError, match="does not support action"):
        action.run("invalid-op", {}, mode="dry-run")


# Test migrate_trace action requires traces or series/network.
def test_migrate_trace_missing_parameters():
    """Test migrate_trace action requires traces or series/network."""
    from causaliq_core import ActionValidationError

    from causaliq_analysis.workflow_action import AnalysisActionProvider

    action = AnalysisActionProvider()

    # Test missing both traces and series/network
    with pytest.raises(
        ActionValidationError, match="requires either 'traces'"
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


# Test merge_graphs with terminal logging in dry-run mode.
def test_merge_graphs_dry_run_with_logging(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test merge_graphs dry-run mode with terminal logging."""

    class MockLogger:
        is_terminal_logging = True

    from causaliq_analysis.workflow_action import AnalysisActionProvider

    action = AnalysisActionProvider()

    parameters = {
        "input": ["graph1.graphml", "graph2.graphml"],
    }

    status, metadata, objects = action.run(
        "merge_graphs", parameters, mode="dry-run", logger=MockLogger()
    )

    assert status == "skipped"
    captured = capsys.readouterr()
    assert "Would merge from 2 input files" in captured.out


# Test merge_graphs with terminal logging during merge.
def test_merge_graphs_with_terminal_logging(
    tmp_path: "pytest.TempPathFactory",
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test merge_graphs with terminal logging enabled."""

    class MockLogger:
        is_terminal_logging = True

    from causaliq_core.graph import DAG
    from causaliq_core.graph.io import graphml

    from causaliq_analysis.workflow_action import AnalysisActionProvider

    # Create two DAGs
    dag1 = DAG(["A", "B"], [("A", "->", "B")])
    dag2 = DAG(["A", "B"], [("B", "->", "A")])

    graph1_path = tmp_path / "graph1.graphml"
    graph2_path = tmp_path / "graph2.graphml"

    with open(graph1_path, "w") as f:
        graphml.write(dag1, f)
    with open(graph2_path, "w") as f:
        graphml.write(dag2, f)

    action = AnalysisActionProvider()

    parameters = {
        "input": [str(graph1_path), str(graph2_path)],
    }

    status, metadata, objects = action.run(
        "merge_graphs", parameters, mode="run", logger=MockLogger()
    )

    assert status == "success"
    captured = capsys.readouterr()
    assert "Loaded" in captured.out
    assert "Merged 2 graphs into PDG" in captured.out


# Test merge_graphs wraps ValueError in ActionExecutionError.
def test_merge_graphs_value_error_exception(
    tmp_path: "pytest.TempPathFactory",
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test merge_graphs wraps ValueError in ActionExecutionError."""
    from causaliq_core.graph import DAG
    from causaliq_core.graph.io import graphml

    from causaliq_analysis.workflow_action import (
        ActionExecutionError,
        AnalysisActionProvider,
    )

    # Create valid GraphML file
    dag = DAG(["A", "B"], [("A", "->", "B")])
    graph_path = tmp_path / "graph.graphml"
    with open(graph_path, "w") as f:
        graphml.write(dag, f)

    action = AnalysisActionProvider()

    # Mock merge_graphs to raise ValueError
    def mock_merge_graphs(*args, **kwargs):
        raise ValueError("Invalid weights")

    monkeypatch.setattr(
        "causaliq_analysis.merge.merge_graphs",
        mock_merge_graphs,
    )

    parameters = {
        "input": [str(graph_path)],
    }

    with pytest.raises(ActionExecutionError, match="Graph merge failed"):
        action.run("merge_graphs", parameters, mode="run")


# Test merge_graphs wraps general exceptions in ActionExecutionError.
def test_merge_graphs_general_exception(
    tmp_path: "pytest.TempPathFactory",
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test merge_graphs wraps general exceptions in ActionExecutionError."""
    from causaliq_core.graph import DAG
    from causaliq_core.graph.io import graphml

    from causaliq_analysis.workflow_action import (
        ActionExecutionError,
        AnalysisActionProvider,
    )

    # Create valid GraphML file
    dag = DAG(["A", "B"], [("A", "->", "B")])
    graph_path = tmp_path / "graph.graphml"
    with open(graph_path, "w") as f:
        graphml.write(dag, f)

    action = AnalysisActionProvider()

    # Mock merge_graphs to raise RuntimeError
    def mock_merge_graphs(*args, **kwargs):
        raise RuntimeError("Unexpected error")

    monkeypatch.setattr(
        "causaliq_analysis.merge.merge_graphs",
        mock_merge_graphs,
    )

    parameters = {
        "input": [str(graph_path)],
    }

    with pytest.raises(ActionExecutionError, match="Graph merge failed"):
        action.run("merge_graphs", parameters, mode="run")


# Test merge_graphs action requires inputs.
def test_merge_graphs_missing_inputs() -> None:
    """Test merge_graphs action requires inputs or aggregate parameter."""
    from causaliq_core import ActionValidationError

    from causaliq_analysis.workflow_action import AnalysisActionProvider

    action = AnalysisActionProvider()

    with pytest.raises(
        ActionValidationError,
        match="requires either '_aggregation_entries'.*or 'input'",
    ):
        action.run("merge_graphs", {}, mode="run")


# Test merge_graphs dry-run mode.
def test_merge_graphs_dry_run() -> None:
    """Test merge_graphs action dry-run mode."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    action = AnalysisActionProvider()

    parameters = {
        "input": ["graph1.graphml", "graph2.graphml"],
    }

    status, metadata, objects = action.run(
        "merge_graphs", parameters, mode="dry-run"
    )

    assert status == "skipped"
    assert "Dry-run mode" in metadata["message"]
    assert metadata["num_inputs"] == 2
    assert objects == []


# Test merge_graphs with invalid input path raises error.
def test_merge_graphs_invalid_input_path() -> None:
    """Test merge_graphs action with invalid input path."""
    from causaliq_analysis.workflow_action import (
        ActionExecutionError,
        AnalysisActionProvider,
    )

    action = AnalysisActionProvider()

    parameters = {
        "input": ["nonexistent.graphml"],
    }

    with pytest.raises(ActionExecutionError, match="Failed to read"):
        action.run("merge_graphs", parameters, mode="run")


# Test merge_graphs accepts string input (normalised to list).
def test_merge_graphs_string_input_normalised() -> None:
    """Test merge_graphs action accepts string input and normalises to list."""
    from causaliq_analysis.workflow_action import (
        ActionExecutionError,
        AnalysisActionProvider,
    )

    action = AnalysisActionProvider()

    # String input should be normalised to list, then fail on missing file
    parameters = {
        "input": "nonexistent.graphml",  # String, not list
    }

    # Should get "Failed to read nonexistent.graphml" not character iteration
    with pytest.raises(ActionExecutionError, match="Failed to read"):
        action.run("merge_graphs", parameters, mode="run")


# Test merge_graphs action with real GraphML files.
def test_merge_graphs_functional(
    tmp_path: "pytest.TempPathFactory",
) -> None:
    """Test merge_graphs action with real GraphML files."""
    from io import StringIO

    from causaliq_core.graph import DAG
    from causaliq_core.graph.io import graphml

    from causaliq_analysis.workflow_action import AnalysisActionProvider

    # Create two DAGs and save as GraphML
    dag1 = DAG(["A", "B"], [("A", "->", "B")])
    dag2 = DAG(["A", "B"], [("B", "->", "A")])

    graph1_path = tmp_path / "graph1.graphml"
    graph2_path = tmp_path / "graph2.graphml"

    with open(graph1_path, "w") as f:
        graphml.write(dag1, f)
    with open(graph2_path, "w") as f:
        graphml.write(dag2, f)

    action = AnalysisActionProvider()

    parameters = {
        "input": [str(graph1_path), str(graph2_path)],
    }

    status, metadata, objects = action.run(
        "merge_graphs", parameters, mode="run"
    )

    assert status == "success"
    assert metadata["num_graphs"] == 2
    assert metadata["cpdag"] is False

    # Check PDG object returned
    assert len(objects) == 1
    assert objects[0]["type"] == "graphml"
    assert objects[0]["name"] == "merged_pdg"
    assert "<?xml" in objects[0]["content"]

    # Verify PDG can be parsed back
    pdg = graphml.read_pdg(StringIO(objects[0]["content"]))
    assert pdg.nodes == ["A", "B"]
    # 0.5 forward probability (from equal weighting of opposite edges)
    probs = pdg.get_probabilities("A", "B")
    assert probs.forward == pytest.approx(0.5)
    assert probs.backward == pytest.approx(0.5)


# Test merge_graphs with weights parameter.
def test_merge_graphs_with_weights(
    tmp_path: "pytest.TempPathFactory",
) -> None:
    """Test merge_graphs action with weights parameter."""
    from io import StringIO

    from causaliq_core.graph import DAG
    from causaliq_core.graph.io import graphml

    from causaliq_analysis.workflow_action import AnalysisActionProvider

    # Create two DAGs
    dag1 = DAG(["A", "B"], [("A", "->", "B")])
    dag2 = DAG(["A", "B"], [("B", "->", "A")])

    graph1_path = tmp_path / "graph1.graphml"
    graph2_path = tmp_path / "graph2.graphml"

    with open(graph1_path, "w") as f:
        graphml.write(dag1, f)
    with open(graph2_path, "w") as f:
        graphml.write(dag2, f)

    action = AnalysisActionProvider()

    parameters = {
        "input": [str(graph1_path), str(graph2_path)],
        "weights": [0.75, 0.25],
    }

    status, metadata, objects = action.run(
        "merge_graphs", parameters, mode="run"
    )

    assert status == "success"
    assert metadata["weights"] == [0.75, 0.25]

    # Verify weighted probabilities
    pdg = graphml.read_pdg(StringIO(objects[0]["content"]))
    probs = pdg.get_probabilities("A", "B")
    assert probs.forward == pytest.approx(0.75)
    assert probs.backward == pytest.approx(0.25)


# Test merge_graphs with cpdag parameter.
def test_merge_graphs_with_cpdag(
    tmp_path: "pytest.TempPathFactory",
) -> None:
    """Test merge_graphs action with cpdag conversion."""
    from io import StringIO

    from causaliq_core.graph import DAG
    from causaliq_core.graph.io import graphml

    from causaliq_analysis.workflow_action import AnalysisActionProvider

    # Create two DAGs - one with A->B, one with B->A
    # As CPDAGs they are the same (A-B undirected equivalence class)
    dag1 = DAG(["A", "B"], [("A", "->", "B")])
    dag2 = DAG(["A", "B"], [("B", "->", "A")])

    graph1_path = tmp_path / "graph1.graphml"
    graph2_path = tmp_path / "graph2.graphml"

    with open(graph1_path, "w") as f:
        graphml.write(dag1, f)
    with open(graph2_path, "w") as f:
        graphml.write(dag2, f)

    action = AnalysisActionProvider()

    parameters = {
        "input": [str(graph1_path), str(graph2_path)],
        "cpdag": True,
    }

    status, metadata, objects = action.run(
        "merge_graphs", parameters, mode="run"
    )

    assert status == "success"
    assert metadata["cpdag"] is True

    # Both DAGs convert to equivalent CPDAGs, so should get 1.0 undirected
    pdg = graphml.read_pdg(StringIO(objects[0]["content"]))
    probs = pdg.get_probabilities("A", "B")
    assert probs.undirected == pytest.approx(1.0)


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


# Test _compute_weights_from_metadata computes normalised weights.
def test_compute_weights_from_metadata() -> None:
    """Test metadata-driven weight computation and normalisation."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    action = AnalysisActionProvider()

    # Sample metadata for 3 graphs
    graph_metadata = [
        {"action": "generate_graph", "algorithm": "pc"},
        {"action": "migrate_trace", "algorithm": "pc"},
        {"action": "migrate_trace", "algorithm": "fci"},
    ]

    # Weight spec: generate_graph=1.0, migrate_trace=0.5; pc=1.0, fci=0.8
    weight_spec = {
        "action": {
            "generate_graph": 1.0,
            "migrate_trace": 0.5,
        },
        "algorithm": {
            "pc": 1.0,
            "fci": 0.8,
        },
    }

    weights = action._compute_weights_from_metadata(
        graph_metadata, weight_spec, None
    )

    # Raw weights: 1.0*1.0=1.0, 0.5*1.0=0.5, 0.5*0.8=0.4
    # Total: 1.9
    # Normalised: 1.0/1.9, 0.5/1.9, 0.4/1.9
    assert len(weights) == 3
    assert weights[0] == pytest.approx(1.0 / 1.9)
    assert weights[1] == pytest.approx(0.5 / 1.9)
    assert weights[2] == pytest.approx(0.4 / 1.9)
    assert sum(weights) == pytest.approx(1.0)


# Test metadata-driven weights requires aggregation mode.
def test_merge_graphs_metadata_weights_requires_aggregation(
    tmp_path: "pytest.TempPathFactory",
) -> None:
    """Test metadata-driven weights error without aggregation mode."""
    from causaliq_core.graph import DAG
    from causaliq_core.graph.io import graphml

    from causaliq_analysis.workflow_action import (
        ActionExecutionError,
        AnalysisActionProvider,
    )

    # Create a valid GraphML file
    dag = DAG(["A", "B"], [("A", "->", "B")])
    graph_path = tmp_path / "graph.graphml"
    with open(graph_path, "w") as f:
        graphml.write(dag, f)

    action = AnalysisActionProvider()

    # Provide dict weights without aggregation mode
    parameters = {
        "input": [str(graph_path)],
        "weights": {"action": {"generate_graph": 1.0}},
    }

    with pytest.raises(
        ActionExecutionError, match="Metadata-driven weights require"
    ):
        action.run("merge_graphs", parameters, mode="run")


# Test invalid weight specification raises error.
def test_merge_graphs_invalid_weight_spec() -> None:
    """Test invalid weight specification raises ActionExecutionError."""
    from causaliq_analysis.workflow_action import (
        ActionExecutionError,
        AnalysisActionProvider,
    )

    action = AnalysisActionProvider()

    # Invalid weight: negative value
    weight_spec = {"action": {"pc": -1.0}}

    with pytest.raises(ActionExecutionError, match="Invalid weight"):
        action._compute_weights_from_metadata(
            [{"action": "pc"}], weight_spec, None
        )


# Test merge_graphs includes provenance metadata in output.
def test_merge_graphs_provenance_metadata(
    tmp_path: "pytest.TempPathFactory",
) -> None:
    """Test merge_graphs includes action, timestamp, filter in metadata."""
    from datetime import datetime

    from causaliq_core.graph import DAG
    from causaliq_core.graph.io import graphml

    from causaliq_analysis.workflow_action import AnalysisActionProvider

    dag = DAG(["A", "B"], [("A", "->", "B")])
    graph_path = tmp_path / "graph.graphml"
    with open(graph_path, "w") as f:
        graphml.write(dag, f)

    action = AnalysisActionProvider()

    # Run without filter
    status, metadata, _ = action.run(
        "merge_graphs",
        {"input": [str(graph_path)]},
        mode="run",
    )

    assert status == "success"
    assert metadata["action"] == "merge_graphs"
    assert "timestamp" in metadata
    # Verify timestamp is valid ISO format
    datetime.fromisoformat(metadata["timestamp"])
    assert "filter" not in metadata


# Test merge_graphs includes filter in provenance when specified.
def test_merge_graphs_provenance_with_filter(
    tmp_path: "pytest.TempPathFactory",
) -> None:
    """Test merge_graphs includes filter in provenance metadata."""
    from causaliq_core.graph import DAG
    from causaliq_core.graph.io import graphml

    from causaliq_analysis.workflow_action import AnalysisActionProvider

    dag = DAG(["A", "B"], [("A", "->", "B")])
    graph_path = tmp_path / "graph.graphml"
    with open(graph_path, "w") as f:
        graphml.write(dag, f)

    action = AnalysisActionProvider()

    # Note: filter parameter is captured in metadata even if not evaluated
    # (evaluation happens in workflow engine before calling action)
    status, metadata, _ = action.run(
        "merge_graphs",
        {"input": [str(graph_path)], "filter": "algorithm == 'pc'"},
        mode="run",
    )

    assert status == "success"
    assert metadata["action"] == "merge_graphs"
    assert metadata["filter"] == "algorithm == 'pc'"


# --------------------------------------------------------------------------
# summarise action functional tests
# --------------------------------------------------------------------------


# Test summarise direct mode with real workflow cache.
def test_summarise_direct_mode_with_cache(
    tmp_path: "pytest.TempPathFactory",
) -> None:
    """Test summarise reads from real workflow cache in direct mode."""
    from causaliq_workflow.cache import CacheEntry, WorkflowCache

    from causaliq_analysis.workflow_action import AnalysisActionProvider

    # Create a workflow cache with entries
    cache_path = tmp_path / "results.db"
    with WorkflowCache(str(cache_path)) as cache:
        entry1 = CacheEntry(
            metadata={
                "causaliq-analysis": {"evaluate_graph": {"f1": 0.8, "shd": 2}}
            }
        )
        entry2 = CacheEntry(
            metadata={
                "causaliq-analysis": {"evaluate_graph": {"f1": 0.9, "shd": 1}}
            }
        )
        cache.put({"seed": 1}, entry1)
        cache.put({"seed": 2}, entry2)

    output_path = tmp_path / "summary.csv"

    action = AnalysisActionProvider()
    status, metadata, _ = action.run(
        "summarise",
        {
            "metric": ["f1.mean", "f1.count", "shd.mean"],
            "input": str(cache_path),  # Single string input
            "output": str(output_path),
        },
        mode="run",
    )

    assert status == "success"
    assert metadata["source_count"] == 2
    assert abs(metadata["f1.mean"] - 0.85) < 0.01
    assert metadata["f1.count"] == 2
    assert abs(metadata["shd.mean"] - 1.5) < 0.01
    assert output_path.exists()


# Test summarise direct mode with filter on cache.
def test_summarise_direct_mode_with_filter(
    tmp_path: "pytest.TempPathFactory",
) -> None:
    """Test summarise applies filter when reading cache."""
    from causaliq_workflow.cache import CacheEntry, WorkflowCache

    from causaliq_analysis.workflow_action import AnalysisActionProvider

    cache_path = tmp_path / "results.db"
    with WorkflowCache(str(cache_path)) as cache:
        entry1 = CacheEntry(
            metadata={
                "causaliq-analysis": {
                    "evaluate_graph": {"f1": 0.8, "status": "completed"}
                }
            }
        )
        entry2 = CacheEntry(
            metadata={
                "causaliq-analysis": {
                    "evaluate_graph": {"f1": 0.5, "status": "failed"}
                }
            }
        )
        entry3 = CacheEntry(
            metadata={
                "causaliq-analysis": {
                    "evaluate_graph": {"f1": 0.9, "status": "completed"}
                }
            }
        )
        cache.put({"seed": 1}, entry1)
        cache.put({"seed": 2}, entry2)
        cache.put({"seed": 3}, entry3)

    output_path = tmp_path / "summary.csv"

    action = AnalysisActionProvider()
    status, metadata, _ = action.run(
        "summarise",
        {
            "metric": ["f1.mean", "f1.count"],
            "input": [str(cache_path)],  # List input
            "output": str(output_path),
            "filter": "status == 'completed'",
        },
        mode="run",
    )

    assert status == "success"
    # Only 2 completed entries
    assert metadata["f1.count"] == 2
    assert abs(metadata["f1.mean"] - 0.85) < 0.01


# Test summarise direct mode filter exception skips entries.
def test_summarise_direct_mode_filter_exception(
    tmp_path: "pytest.TempPathFactory",
) -> None:
    """Test summarise skips entries when filter raises exception."""
    from causaliq_workflow.cache import CacheEntry, WorkflowCache

    from causaliq_analysis.workflow_action import AnalysisActionProvider

    cache_path = tmp_path / "results.db"
    with WorkflowCache(str(cache_path)) as cache:
        entry = CacheEntry(
            metadata={"causaliq-analysis": {"evaluate_graph": {"f1": 0.8}}}
        )
        cache.put({"seed": 1}, entry)

    output_path = tmp_path / "summary.csv"

    action = AnalysisActionProvider()
    status, metadata, _ = action.run(
        "summarise",
        {
            "metric": ["f1.count"],
            "input": str(cache_path),
            "output": str(output_path),
            "filter": "undefined_var > 5",  # Will cause exception
        },
        mode="run",
    )

    assert status == "success"
    # Entry skipped due to filter exception
    assert metadata["f1.count"] == 0


# Test summarise direct mode cache read error.
def test_summarise_direct_mode_cache_read_error(
    tmp_path: "pytest.TempPathFactory",
) -> None:
    """Test summarise raises error when cache file is corrupt."""
    from causaliq_analysis.workflow_action import (
        ActionExecutionError,
        AnalysisActionProvider,
    )

    # Create a corrupt db file
    cache_path = tmp_path / "corrupt.db"
    cache_path.write_text("not a valid sqlite database")

    action = AnalysisActionProvider()

    with pytest.raises(ActionExecutionError, match="Failed to read cache"):
        action.run(
            "summarise",
            {
                "metric": ["f1.mean"],
                "input": str(cache_path),
            },
            mode="run",
        )


# Test summarise direct mode logs progress.
def test_summarise_direct_mode_logs_progress(
    tmp_path: "pytest.TempPathFactory",
    capsys: "pytest.CaptureFixture[str]",
) -> None:
    """Test summarise logs progress when terminal logging enabled."""
    from unittest.mock import MagicMock

    from causaliq_workflow.cache import CacheEntry, WorkflowCache

    from causaliq_analysis.workflow_action import AnalysisActionProvider

    cache_path = tmp_path / "results.db"
    with WorkflowCache(str(cache_path)) as cache:
        entry = CacheEntry(
            metadata={"causaliq-analysis": {"evaluate_graph": {"f1": 0.8}}}
        )
        cache.put({"seed": 1}, entry)

    output_path = tmp_path / "summary.csv"

    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = True

    action = AnalysisActionProvider()
    action.run(
        "summarise",
        {
            "metric": ["f1.mean"],
            "input": str(cache_path),
            "output": str(output_path),
        },
        mode="run",
        logger=mock_logger,
    )

    captured = capsys.readouterr()
    assert "Processed:" in captured.out
    assert "Collected values from" in captured.out
    assert "Summary written to" in captured.out
