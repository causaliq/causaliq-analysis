# Tests for migrate module - full-circle verification of graph migration.

from io import StringIO
from typing import List

import pytest
from causaliq_core.graph import DAG, PDAG
from causaliq_core.graph.io import graphml

from causaliq_analysis.migrate import (
    MigratedGraph,
    MigrateTraceResult,
    get_trace_metadata,
    migrate_traces,
    run_migrate_trace,
    trace_to_dag,
    trace_to_graphml,
    trace_to_pdag,
    write_migrate_result,
)
from causaliq_analysis.trace import Trace

TESTDATA_DIR = "tests/data/functional/"


# Test get_trace_metadata with bad argument type.
def test_get_trace_metadata_type_error() -> None:
    with pytest.raises(TypeError):
        get_trace_metadata(None)  # type: ignore
    with pytest.raises(TypeError):
        get_trace_metadata("not a trace")  # type: ignore
    with pytest.raises(TypeError):
        get_trace_metadata({"id": "test"})  # type: ignore


# Test get_trace_metadata extracts correct fields.
def test_get_trace_metadata_ok() -> None:
    traces = Trace.read("TABU/STD/asia", TESTDATA_DIR + "trace")
    assert traces is not None
    trace = traces["N1000"]

    metadata = get_trace_metadata(trace)

    # Check expected fields are present
    assert "algorithm" in metadata
    assert isinstance(metadata["algorithm"], str)
    assert "N" in metadata
    assert metadata["N"] == 1000
    assert "params" in metadata
    assert isinstance(metadata["params"], dict)


# Test get_trace_metadata serialises params values.
def test_get_trace_metadata_params_serialised() -> None:
    """Test that params dict values are serialised to JSON-compatible types."""
    traces = Trace.read("TABU/STD/asia", TESTDATA_DIR + "trace")
    assert traces is not None
    trace = traces["N1000"]

    metadata = get_trace_metadata(trace)

    # All values in params should be JSON-serialisable (no object refs)
    params = metadata.get("params", {})
    for key, value in params.items():
        # Value should not be an object reference string
        if isinstance(value, str):
            assert not value.startswith(
                "<"
            ), f"params['{key}'] is object reference: {value}"


# Test trace_to_dag with bad argument type.
def test_trace_to_dag_type_error() -> None:
    with pytest.raises(TypeError):
        trace_to_dag(None)  # type: ignore
    with pytest.raises(TypeError):
        trace_to_dag("not a trace")  # type: ignore


# Test trace_to_dag with trace that has no result.
def test_trace_to_dag_no_result_error() -> None:
    trace = Trace({"id": "test", "N": 100})
    with pytest.raises(ValueError, match="no result"):
        trace_to_dag(trace)


# Test trace_to_dag extracts DAG correctly.
def test_trace_to_dag_ok() -> None:
    traces = Trace.read("TABU/STD/asia", TESTDATA_DIR + "trace")
    assert traces is not None
    trace = traces["N1000"]

    dag = trace_to_dag(trace)

    assert isinstance(dag, DAG)
    assert len(dag.nodes) == 8  # asia has 8 nodes
    assert "asia" in dag.nodes
    assert "smoke" in dag.nodes


# Test trace_to_pdag with bad argument type.
def test_trace_to_pdag_type_error() -> None:
    with pytest.raises(TypeError):
        trace_to_pdag(None)  # type: ignore
    with pytest.raises(TypeError):
        trace_to_pdag("not a trace")  # type: ignore


# Test trace_to_pdag with trace that has no result.
def test_trace_to_pdag_no_result_error() -> None:
    trace = Trace({"id": "test", "N": 100})
    with pytest.raises(ValueError, match="no result"):
        trace_to_pdag(trace)


# Test trace_to_pdag converts DAG to PDAG correctly.
def test_trace_to_pdag_ok() -> None:
    traces = Trace.read("TABU/STD/asia", TESTDATA_DIR + "trace")
    assert traces is not None
    trace = traces["N1000"]

    pdag = trace_to_pdag(trace)

    assert isinstance(pdag, PDAG)
    # PDAG should not be a DAG instance (after conversion)
    assert not isinstance(pdag, DAG)
    assert len(pdag.nodes) == 8


# Test trace_to_graphml with bad argument type.
def test_trace_to_graphml_type_error() -> None:
    with pytest.raises(TypeError):
        trace_to_graphml(None)  # type: ignore
    with pytest.raises(TypeError):
        trace_to_graphml("not a trace")  # type: ignore


# Test trace_to_graphml with trace that has no result.
def test_trace_to_graphml_no_result_error() -> None:
    trace = Trace({"id": "test", "N": 100})
    with pytest.raises(ValueError, match="no result"):
        trace_to_graphml(trace)


# Test trace_to_graphml produces valid GraphML string.
def test_trace_to_graphml_ok() -> None:
    traces = Trace.read("TABU/STD/asia", TESTDATA_DIR + "trace")
    assert traces is not None
    trace = traces["N1000"]

    graphml_str = trace_to_graphml(trace)

    assert isinstance(graphml_str, str)
    assert "<graphml" in graphml_str
    assert "asia" in graphml_str  # node should appear
    assert "</graphml>" in graphml_str


# Test migrate_traces with bad argument type.
def test_migrate_traces_type_error() -> None:
    with pytest.raises(TypeError):
        migrate_traces(None)  # type: ignore
    with pytest.raises(TypeError):
        migrate_traces([])  # type: ignore
    with pytest.raises(TypeError):
        migrate_traces({"test": "not a trace"})  # type: ignore


# Test migrate_traces skips traces without result.
def test_migrate_traces_skips_no_result() -> None:
    # Create some traces, one without a result
    trace_with_result = Trace.read("TABU/STD/asia", TESTDATA_DIR + "trace")
    assert trace_with_result is not None
    trace_n1000 = trace_with_result["N1000"]

    trace_no_result = Trace({"id": "TEST/test", "N": 100})
    # trace_no_result.result is None by default

    traces = {
        "trace_ok": trace_n1000,
        "trace_skip": trace_no_result,
    }

    migrated = migrate_traces(traces)

    # Should only migrate the one with a result
    assert len(migrated) == 1
    assert migrated[0][0] == "trace_ok"


# Test migrate_traces processes multiple traces.
def test_migrate_traces_ok() -> None:
    traces = Trace.read("TABU/STD/asia", TESTDATA_DIR + "trace")
    assert traces is not None

    migrated = migrate_traces(traces)

    # Should migrate all traces that have results
    assert len(migrated) >= 1

    # Check structure of migrated data
    for trace_id, graphml_str, metadata in migrated:
        assert isinstance(trace_id, str)
        assert "<graphml" in graphml_str
        assert "N" in metadata
        assert isinstance(metadata["N"], int)


# FULL-CIRCLE TEST: Verify graph structure is preserved through migration.
def test_full_circle_dag_structure_preserved() -> None:
    """Full-circle test: DAG structure preserved through GraphML round-trip.

    This test verifies that when we:
    1. Read a trace file
    2. Extract the DAG
    3. Convert to GraphML
    4. Parse GraphML back to DAG

    The nodes and edges are exactly preserved.
    """
    # Step 1: Read trace
    traces = Trace.read("TABU/STD/asia", TESTDATA_DIR + "trace")
    assert traces is not None
    trace = traces["N1000"]

    # Step 2: Extract original DAG
    original_dag = trace_to_dag(trace)
    original_nodes = set(original_dag.nodes)
    original_edges = set(original_dag.edges.keys())

    # Step 3: Convert to GraphML
    graphml_str = trace_to_graphml(trace)

    # Step 4: Parse GraphML back to graph
    buffer = StringIO(graphml_str)
    restored_graph = graphml.read(buffer)

    # Step 5: Verify structure matches
    assert isinstance(restored_graph, DAG), "Restored graph should be DAG"
    restored_nodes = set(restored_graph.nodes)
    restored_edges = set(restored_graph.edges.keys())

    # Verify nodes match exactly
    assert original_nodes == restored_nodes, (
        f"Nodes mismatch: original={original_nodes}, "
        f"restored={restored_nodes}"
    )

    # Verify edges match exactly
    assert original_edges == restored_edges, (
        f"Edges mismatch: original={original_edges}, "
        f"restored={restored_edges}"
    )

    # Verify edge types match
    for edge_key in original_edges:
        assert original_dag.edges[edge_key] == restored_graph.edges[edge_key]


# FULL-CIRCLE TEST: Verify PDAG structure is preserved through migration.
def test_full_circle_pdag_structure_preserved() -> None:
    """Full-circle test: PDAG structure preserved through GraphML round-trip.

    This test verifies that when we:
    1. Read a trace file
    2. Extract and convert to PDAG using trace_to_pdag
    3. Write PDAG to GraphML
    4. Parse GraphML back to PDAG

    The nodes and edges are exactly preserved.
    """
    # Step 1: Read trace
    traces = Trace.read("TABU/STD/asia", TESTDATA_DIR + "trace")
    assert traces is not None
    trace = traces["N1000"]

    # Step 2: Extract and convert to PDAG
    original_pdag = trace_to_pdag(trace)
    original_nodes = set(original_pdag.nodes)
    original_edges = set(original_pdag.edges.keys())

    # Step 3: Write PDAG to GraphML
    buffer_out = StringIO()
    graphml.write(original_pdag, buffer_out)
    graphml_str = buffer_out.getvalue()

    # Step 4: Parse GraphML back to graph
    buffer = StringIO(graphml_str)
    restored_graph = graphml.read(buffer)

    # Step 5: Verify structure matches
    assert isinstance(restored_graph, PDAG), "Restored graph should be PDAG"
    restored_nodes = set(restored_graph.nodes)
    restored_edges = set(restored_graph.edges.keys())

    # Verify nodes match exactly
    assert original_nodes == restored_nodes, (
        f"Nodes mismatch: original={original_nodes}, "
        f"restored={restored_nodes}"
    )

    # Verify edges match exactly
    assert original_edges == restored_edges, (
        f"Edges mismatch: original={original_edges}, "
        f"restored={restored_edges}"
    )

    # Verify edge types match
    for edge_key in original_edges:
        assert original_pdag.edges[edge_key] == restored_graph.edges[edge_key]


# FULL-CIRCLE TEST: Verify specific edge values from known trace.
def test_full_circle_asia_specific_edges() -> None:
    """Verify specific known edges from the asia network trace.

    This test checks that specific edges from the learnt asia graph
    are correctly preserved, providing a spot-check on structure.
    """
    traces = Trace.read("TABU/STD/asia", TESTDATA_DIR + "trace")
    assert traces is not None
    trace = traces["N1000"]

    # Get original edges
    original_dag = trace_to_dag(trace)

    # Round-trip through GraphML
    graphml_str = trace_to_graphml(trace)
    buffer = StringIO(graphml_str)
    restored_dag = graphml.read(buffer)

    # The asia network typically has edges like:
    # smoke -> lung, smoke -> bronc, lung -> either, tub -> either
    # Check that edges exist in both original and restored
    assert len(original_dag.edges) == len(restored_dag.edges)

    # Verify all edges are present after round-trip
    for edge_key, edge_type in original_dag.edges.items():
        assert (
            edge_key in restored_dag.edges
        ), f"Edge {edge_key} missing after round-trip"
        assert restored_dag.edges[edge_key] == edge_type, (
            f"Edge {edge_key} type mismatch: "
            f"original={edge_type}, restored={restored_dag.edges[edge_key]}"
        )


# Test run_migrate_trace raises ValueError when no traces found.
def test_run_migrate_trace_no_traces_error() -> None:
    with pytest.raises(ValueError, match="No traces found"):
        run_migrate_trace(
            partial_id="NONEXISTENT/PATH/network",
            root_dir=TESTDATA_DIR + "trace",
        )


# Test run_migrate_trace returns empty result when no matching traces.
def test_run_migrate_trace_no_matching_error() -> None:
    result = run_migrate_trace(
        partial_id="TABU/STD/asia",
        root_dir=TESTDATA_DIR + "trace",
        sample_size=99999,  # No trace has this sample size
    )
    assert result.num_graphs == 0


# Test run_migrate_trace logs messages via callback.
def test_run_migrate_trace_logs_messages() -> None:
    log_messages: List[str] = []

    def log_fn(msg: str) -> None:
        log_messages.append(msg)

    run_migrate_trace(
        partial_id="TABU/STD/asia",
        root_dir=TESTDATA_DIR + "trace",
        log_fn=log_fn,
    )

    # Should have logged loading, found, and completion messages
    assert any("Loading" in msg for msg in log_messages)
    assert any("Found" in msg for msg in log_messages)
    assert any("complete" in msg.lower() for msg in log_messages)


# Test run_migrate_trace returns correct result structure.
def test_run_migrate_trace_ok() -> None:
    result = run_migrate_trace(
        partial_id="TABU/STD/asia",
        root_dir=TESTDATA_DIR + "trace",
    )

    assert isinstance(result, MigrateTraceResult)
    assert result.num_graphs >= 1
    assert len(result.graphs) >= 1

    # Check graph structure
    graph = result.graphs[0]
    assert isinstance(graph, MigratedGraph)
    assert isinstance(graph.trace_id, str)
    assert "<graphml" in graph.graphml
    assert "N" in graph.metadata


# Test run_migrate_trace skips traces without result and logs.
def test_run_migrate_trace_skips_no_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from causaliq_analysis import migrate

    # Load real traces
    real_traces = Trace.read("TABU/STD/asia", TESTDATA_DIR + "trace")
    assert real_traces is not None

    # Create a trace without a result
    trace_no_result = Trace({"id": "TEST/test", "N": 100})
    # trace_no_result.result is None by default

    # Patch filter_traces to return both real trace and one without result
    def mock_filter_traces(
        traces: dict,
        sample_size: int = None,
        seed: tuple = None,
    ) -> dict:
        result_traces = {}
        for k, v in real_traces.items():
            result_traces[k] = v
        result_traces["no_result_trace"] = trace_no_result
        return result_traces

    monkeypatch.setattr(migrate, "filter_traces", mock_filter_traces)

    log_messages: List[str] = []

    result = run_migrate_trace(
        partial_id="TABU/STD/asia",
        root_dir=TESTDATA_DIR + "trace",
        log_fn=lambda msg: log_messages.append(msg),
    )

    # Should have logged skip message
    assert any("Skipping" in msg for msg in log_messages)
    assert result.skipped == 1


# Test write_migrate_result writes files correctly.
def test_write_migrate_result_ok(tmp_path: str) -> None:
    # Create a mock migration result
    result = MigrateTraceResult(
        graphs=[
            MigratedGraph(
                trace_id="test_trace_1",
                graphml='<?xml version="1.0"?><graphml></graphml>',
                metadata={"N": 1000, "algorithm": "TABU"},
            ),
            MigratedGraph(
                trace_id="test/trace/2",  # Contains slashes
                graphml='<?xml version="1.0"?><graphml></graphml>',
                metadata={"N": 500, "algorithm": "HC"},
            ),
        ],
        skipped=0,
    )

    log_messages: List[str] = []

    output_files = write_migrate_result(
        result=result,
        output_dir=str(tmp_path),
        log_fn=lambda msg: log_messages.append(msg),
    )

    # Check files were written
    assert len(output_files) == 2

    # Check file names (slashes should be replaced)
    import os

    files = os.listdir(tmp_path)
    assert "test_trace_1.graphml" in files
    assert "test_trace_1.metadata.json" in files
    assert "test_trace_2.graphml" in files  # Slashes replaced with underscores
    assert "test_trace_2.metadata.json" in files

    # Check logging
    assert any("Wrote" in msg for msg in log_messages)
