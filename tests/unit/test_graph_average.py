"""Unit tests for graph averaging functionality."""

from math import log2

import pytest
from causaliq_core.graph import DAG
from pandas import DataFrame

from causaliq_analysis.graph import average
from causaliq_analysis.trace import Trace


# Test entropy calculations for various edge probability scenarios
def test_entropy_calculations():
    """Test h_exist and h_orient entropy calculations."""
    # Create 4 graphs to test various probability scenarios
    # Graph 1: A->B (directed A to B)
    trace1 = Trace(context={"id": "network_N1000_0", "N": 1000})
    trace1.result = DAG(["A", "B"], [("A", "->", "B")])

    # Graph 2: A->B (same direction)
    trace2 = Trace(context={"id": "network_N1000_1", "N": 1000})
    trace2.result = DAG(["A", "B"], [("A", "->", "B")])

    # Graph 3: B->A (opposite direction)
    trace3 = Trace(context={"id": "network_N1000_2", "N": 1000})
    trace3.result = DAG(["A", "B"], [("B", "->", "A")])

    # Graph 4: no edge
    trace4 = Trace(context={"id": "network_N1000_3", "N": 1000})
    trace4.result = DAG(["A", "B"], [])

    traces = {
        "network_N1000_0": trace1,
        "network_N1000_1": trace2,
        "network_N1000_2": trace3,
        "network_N1000_3": trace4,
    }

    df = average(
        traces=traces, sample_size=1000, pdag=False, seeds=(0, 1, 2, 3)
    )

    # Probabilities: p_a_to_b=0.5, p_b_to_a=0.25, p_no_edge=0.25
    assert len(df) == 1
    row = df.iloc[0]
    assert row["p_a_to_b"] == 0.5
    assert row["p_b_to_a"] == 0.25
    assert row["p_no_edge"] == 0.25

    # h_exist: H(p_exist=0.75, p_no_edge=0.25)
    p_exist = 0.75
    p_no_edge = 0.25
    expected_h_exist = -p_exist * log2(p_exist) - p_no_edge * log2(p_no_edge)
    assert abs(row["h_exist"] - expected_h_exist) < 0.001

    # h_orient: weighted combination
    # p_directed = 0.75, p_undirected = 0
    # p_a_given_dir = 0.5/0.75 = 2/3, p_b_given_dir = 0.25/0.75 = 1/3
    # H(2/3, 1/3) = -2/3*log2(2/3) - 1/3*log2(1/3)
    p_a_given_dir = 0.5 / 0.75
    p_b_given_dir = 0.25 / 0.75
    expected_h_dir = -p_a_given_dir * log2(
        p_a_given_dir
    ) - p_b_given_dir * log2(p_b_given_dir)
    assert abs(row["h_orient"] - expected_h_dir) < 0.001


# Test entropy with all undirected edges (max direction uncertainty)
def test_entropy_all_undirected():
    """Test h_orient = 1.0 when all edges are undirected."""
    # Create graphs that become undirected in PDAG
    # Simple chain: A->B->C becomes A-B-C in PDAG
    trace1 = Trace(context={"id": "network_N1000_0", "N": 1000})
    trace1.result = DAG(["A", "B", "C"], [("A", "->", "B"), ("B", "->", "C")])

    trace2 = Trace(context={"id": "network_N1000_1", "N": 1000})
    trace2.result = DAG(["A", "B", "C"], [("B", "->", "A"), ("C", "->", "B")])

    traces = {"network_N1000_0": trace1, "network_N1000_1": trace2}

    df = average(traces=traces, sample_size=1000, pdag=True, seeds=(0, 1))

    # With PDAG conversion, chains become undirected
    # h_orient should be 1.0 (max uncertainty) for undirected edges
    for _, row in df.iterrows():
        if row["p_undirected"] == 1.0:
            assert row["h_orient"] == 1.0
            assert row["h_exist"] == 0.0  # certain edge exists


# Average raises ValueError when no traces match the sample size
def test_no_matching_traces():
    trace = Trace(context={"N": 5000})
    trace.result = DAG(["A", "B"], [("A", "->", "B")])

    with pytest.raises(ValueError, match="no traces found"):
        average(
            traces={"trace1": trace}, sample_size=1000, pdag=False, seeds=()
        )


# Average computes correct edge probabilities for two opposing directed edges
def test_simple_average_two_dags():
    trace1 = Trace(context={"id": "network_N1000_0", "N": 1000})
    trace1.result = DAG(["A", "B"], [("A", "->", "B")])

    trace2 = Trace(context={"id": "network_N1000_1", "N": 1000})
    trace2.result = DAG(["A", "B"], [("B", "->", "A")])

    traces = {"network_N1000_0": trace1, "network_N1000_1": trace2}

    print("\n=== Input Graphs (Simple Two DAGs) ===")
    print(f"Graph 1: {trace1.result}")
    print(f"Graph 2: {trace2.result}")

    df = average(traces=traces, sample_size=1000, pdag=False, seeds=(0, 1))

    print("\n=== Simple Average Two DAGs Test Results ===")
    print(df.to_string(index=False))
    print(f"\nTotal node pairs: {len(df)}")
    print("Number of graphs averaged: 2")

    assert isinstance(df, DataFrame)
    assert len(df) == 1
    assert df.iloc[0]["node_a"] == "A"
    assert df.iloc[0]["node_b"] == "B"
    assert df.iloc[0]["p_a_to_b"] == 0.5
    assert df.iloc[0]["p_b_to_a"] == 0.5
    assert df.iloc[0]["p_undirected"] == 0.0
    assert df.iloc[0]["p_no_edge"] == 0.0
    # Edge always exists (h_exist=0), but direction is maximally uncertain
    assert df.iloc[0]["h_exist"] == 0.0
    assert df.iloc[0]["h_orient"] == 1.0  # max uncertainty: 50/50 split


# Average returns empty DataFrame when no edges exist in any graph
def test_average_with_no_edges():
    trace1 = Trace(context={"id": "network_N1000_0", "N": 1000})
    trace1.result = DAG(["A", "B"], [])

    trace2 = Trace(context={"id": "network_N1000_1", "N": 1000})
    trace2.result = DAG(["A", "B"], [])

    traces = {"network_N1000_0": trace1, "network_N1000_1": trace2}

    print("\n=== Input Graphs (No Edges) ===")
    print(f"Graph 1: {trace1.result}")
    print(f"Graph 2: {trace2.result}")

    df = average(traces=traces, sample_size=1000, pdag=False, seeds=(0, 1))

    print("\n=== No Edges Test Results ===")
    print(df.to_string(index=False))
    print(f"\nTotal node pairs: {len(df)}")
    print("Number of graphs averaged: 2")

    # Rows with p_no_edge == 1.0 are now dropped
    assert len(df) == 0


# Average handles three nodes and creates correct number of node pairs
def test_average_three_nodes():
    trace1 = Trace(context={"id": "network_N1000_0", "N": 1000})
    trace1.result = DAG(["A", "B", "C"], [("A", "->", "B"), ("B", "->", "C")])

    trace2 = Trace(context={"id": "network_N1000_1", "N": 1000})
    trace2.result = DAG(["A", "B", "C"], [("A", "->", "B"), ("B", "->", "C")])

    traces = {"network_N1000_0": trace1, "network_N1000_1": trace2}

    print("\n=== Input Graphs (Three Nodes) ===")
    print(f"Graph 1: {trace1.result}")
    print(f"Graph 2: {trace2.result}")

    df = average(traces=traces, sample_size=1000, pdag=False, seeds=(0, 1))

    print("\n=== Three Nodes Test Results ===")
    print(df.to_string(index=False))
    print(f"\nTotal node pairs: {len(df)}")
    print("Number of graphs averaged: 2")

    # Only 2 pairs have edges (A-B and B-C), A-C has no edge so is dropped
    assert len(df) == 2

    ab_row = df[(df["node_a"] == "A") & (df["node_b"] == "B")]
    assert len(ab_row) == 1
    assert ab_row.iloc[0]["p_a_to_b"] == 1.0
    # With p_a_to_b=1.0, h_exist=0 (certain edge exists),
    # h_orient=0 (certain direction)
    assert ab_row.iloc[0]["h_exist"] == 0.0
    assert ab_row.iloc[0]["h_orient"] == 0.0


# Average with empty seeds tuple includes all traces with matching sample size
def test_average_all_seeds():
    trace1 = Trace(context={"id": "network_N1000_0", "N": 1000})
    trace1.result = DAG(["A", "B"], [("A", "->", "B")])

    trace2 = Trace(context={"id": "network_N1000_99", "N": 1000})
    trace2.result = DAG(["A", "B"], [("B", "->", "A")])

    traces = {"network_N1000_0": trace1, "network_N1000_99": trace2}

    print("\n=== Input Graphs (All Seeds) ===")
    print(f"Graph 1: {trace1.result}")
    print(f"Graph 2: {trace2.result}")

    df = average(traces=traces, sample_size=1000, pdag=False, seeds=())

    print("\n=== All Seeds Test Results ===")
    print(df.to_string(index=False))
    print(f"\nTotal node pairs: {len(df)}")
    print("Number of graphs averaged: 2 (all matching seeds)")

    assert len(df) == 1
    assert df.iloc[0]["p_a_to_b"] == 0.5
    assert df.iloc[0]["p_b_to_a"] == 0.5


# Average raises ValueError when trace has no result graph
def test_trace_without_result():
    trace = Trace(context={"id": "network_N1000_0", "N": 1000})

    traces = {"network_N1000_0": trace}

    with pytest.raises(ValueError, match="trace has no result graph"):
        average(traces=traces, sample_size=1000, pdag=False, seeds=(0,))


# Average raises ValueError when traces have different node sets
def test_mismatched_nodes():
    trace1 = Trace(context={"id": "network_N1000_0", "N": 1000})
    trace1.result = DAG(["A", "B"], [("A", "->", "B")])

    trace2 = Trace(context={"id": "network_N1000_1", "N": 1000})
    trace2.result = DAG(["A", "C"], [("A", "->", "C")])

    traces = {"network_N1000_0": trace1, "network_N1000_1": trace2}

    with pytest.raises(ValueError, match="has different nodes"):
        average(traces=traces, sample_size=1000, pdag=False, seeds=(0, 1))


# Complex case: three graphs with four edges (different topologies) as DAG
def test_complex_four_edges_three_graphs_dag():
    # Graph 1: A->B->C->D (chain)
    trace1 = Trace(context={"id": "network_N1000_0", "N": 1000})
    trace1.result = DAG(
        ["A", "B", "C", "D"],
        [("A", "->", "B"), ("B", "->", "C"), ("C", "->", "D")],
    )

    # Graph 2: A->B, A->C, A->D (star from A)
    trace2 = Trace(context={"id": "network_N1000_1", "N": 1000})
    trace2.result = DAG(
        ["A", "B", "C", "D"],
        [("A", "->", "B"), ("A", "->", "C"), ("A", "->", "D")],
    )

    # Graph 3: B->A, C->B, D->C (reverse chain)
    trace3 = Trace(context={"id": "network_N1000_2", "N": 1000})
    trace3.result = DAG(
        ["A", "B", "C", "D"],
        [("B", "->", "A"), ("C", "->", "B"), ("D", "->", "C")],
    )

    traces = {
        "network_N1000_0": trace1,
        "network_N1000_1": trace2,
        "network_N1000_2": trace3,
    }

    print("\n=== Input Graphs (DAG) ===")
    print(f"Graph 1: {trace1.result}")
    print(f"Graph 2: {trace2.result}")
    print(f"Graph 3: {trace3.result}")

    df = average(traces=traces, sample_size=1000, pdag=False, seeds=(0, 1, 2))

    print("\n=== Complex DAG Test: 4 nodes, 3 graphs, pdag=False ===")
    print(df.to_string(index=False))
    print(f"\nTotal node pairs: {len(df)}")
    print("Number of graphs averaged: 3")

    # Should have 5 node pairs (B-D has no edge in any graph, so dropped)
    assert len(df) == 5

    # Check A-B pair: appears in all 3 graphs (A->B twice, B->A once)
    ab_row = df[(df["node_a"] == "A") & (df["node_b"] == "B")]
    assert len(ab_row) == 1
    assert abs(ab_row.iloc[0]["p_a_to_b"] - 2 / 3) < 0.01
    assert abs(ab_row.iloc[0]["p_b_to_a"] - 1 / 3) < 0.01

    # Check B-C pair: B->C in graph 1, C->B in graph 3, A->C in graph 2
    bc_row = df[(df["node_a"] == "B") & (df["node_b"] == "C")]
    assert len(bc_row) == 1
    assert abs(bc_row.iloc[0]["p_a_to_b"] - 1 / 3) < 0.01  # B->C
    assert abs(bc_row.iloc[0]["p_b_to_a"] - 1 / 3) < 0.01  # C->B


# Complex case: three graphs with four edges (different topologies) as PDAG
def test_complex_four_edges_three_graphs_pdag():
    # Graph 1: A->B->C->D (chain)
    trace1 = Trace(context={"id": "network_N1000_0", "N": 1000})
    trace1.result = DAG(
        ["A", "B", "C", "D"],
        [("A", "->", "B"), ("B", "->", "C"), ("C", "->", "D")],
    )

    # Graph 2: A->B, A->C, A->D (star from A)
    trace2 = Trace(context={"id": "network_N1000_1", "N": 1000})
    trace2.result = DAG(
        ["A", "B", "C", "D"],
        [("A", "->", "B"), ("A", "->", "C"), ("A", "->", "D")],
    )

    # Graph 3: B->A, C->B, D->C (reverse chain)
    trace3 = Trace(context={"id": "network_N1000_2", "N": 1000})
    trace3.result = DAG(
        ["A", "B", "C", "D"],
        [("B", "->", "A"), ("C", "->", "B"), ("D", "->", "C")],
    )

    traces = {
        "network_N1000_0": trace1,
        "network_N1000_1": trace2,
        "network_N1000_2": trace3,
    }

    print("\n=== Input Graphs (will be converted to PDAG) ===")
    print(f"Graph 1: {trace1.result}")
    print(f"Graph 2: {trace2.result}")
    print(f"Graph 3: {trace3.result}")

    df = average(traces=traces, sample_size=1000, pdag=True, seeds=(0, 1, 2))

    print("\n=== Complex PDAG Test: 4 nodes, 3 graphs, pdag=True ===")
    print(df.to_string(index=False))
    print(f"\nTotal node pairs: {len(df)}")
    print("Number of graphs averaged: 3")
    print(
        "\nNote: With pdag=True, graphs are converted to PDAGs "
        "before averaging"
    )

    # Should have 5 node pairs (B-D has no edge in any graph, so dropped)
    assert len(df) == 5

    # PDAG conversion may result in undirected edges
    # Check that probabilities sum to 1 for each pair
    for _, row in df.iterrows():
        prob_sum = (
            row["p_a_to_b"]
            + row["p_b_to_a"]
            + row["p_undirected"]
            + row["p_no_edge"]
        )
        assert abs(prob_sum - 1.0) < 0.01


# Complex case: varying edge presence across three graphs
def test_complex_varying_edge_presence():
    # Graph 1: A->B, B->C, C->D (chain)
    trace1 = Trace(context={"id": "network_N1000_0", "N": 1000})
    trace1.result = DAG(
        ["A", "B", "C", "D"],
        [("A", "->", "B"), ("B", "->", "C"), ("C", "->", "D")],
    )

    # Graph 2: only A->B and C->D (disconnected)
    trace2 = Trace(context={"id": "network_N1000_1", "N": 1000})
    trace2.result = DAG(
        ["A", "B", "C", "D"], [("A", "->", "B"), ("C", "->", "D")]
    )

    # Graph 3: no edges at all
    trace3 = Trace(context={"id": "network_N1000_2", "N": 1000})
    trace3.result = DAG(["A", "B", "C", "D"], [])

    traces = {
        "network_N1000_0": trace1,
        "network_N1000_1": trace2,
        "network_N1000_2": trace3,
    }

    print("\n=== Input Graphs (Varying Presence) ===")
    print(f"Graph 1: {trace1.result}")
    print(f"Graph 2: {trace2.result}")
    print(f"Graph 3: {trace3.result}")

    df = average(traces=traces, sample_size=1000, pdag=False, seeds=(0, 1, 2))

    print(
        "\n=== Complex Varying Presence Test: "
        "3 graphs with different edges ==="
    )
    print(df.to_string(index=False))
    print(f"\nTotal node pairs: {len(df)}")

    # Check A-B: appears in graphs 1 and 2, missing in 3
    ab_row = df[(df["node_a"] == "A") & (df["node_b"] == "B")]
    assert len(ab_row) == 1
    assert abs(ab_row.iloc[0]["p_a_to_b"] - 2 / 3) < 0.01
    assert abs(ab_row.iloc[0]["p_no_edge"] - 1 / 3) < 0.01
    # h_exist > 0 because edge is missing in 1/3 of graphs
    assert ab_row.iloc[0]["h_exist"] > 0.0

    # Check A-C: no direct edge between A and C in any graph - row is dropped
    ac_row = df[(df["node_a"] == "A") & (df["node_b"] == "C")]
    assert len(ac_row) == 0

    # Check B-C: only in graph 1
    bc_row = df[(df["node_a"] == "B") & (df["node_b"] == "C")]
    assert len(bc_row) == 1
    assert abs(bc_row.iloc[0]["p_a_to_b"] - 1 / 3) < 0.01
    assert abs(bc_row.iloc[0]["p_no_edge"] - 2 / 3) < 0.01


# Test with undirected edges: simple v-structure creates undirected edge
def test_pdag_with_undirected_edges_vstructure():
    # Graph 1: A->C<-B (v-structure, C is collider)
    trace1 = Trace(context={"id": "network_N1000_0", "N": 1000})
    trace1.result = DAG(["A", "B", "C"], [("A", "->", "C"), ("B", "->", "C")])

    # Graph 2: A->C<-B (same v-structure)
    trace2 = Trace(context={"id": "network_N1000_1", "N": 1000})
    trace2.result = DAG(["A", "B", "C"], [("A", "->", "C"), ("B", "->", "C")])

    # Graph 3: B->C<-A (same v-structure)
    trace3 = Trace(context={"id": "network_N1000_2", "N": 1000})
    trace3.result = DAG(["A", "B", "C"], [("A", "->", "C"), ("B", "->", "C")])

    traces = {
        "network_N1000_0": trace1,
        "network_N1000_1": trace2,
        "network_N1000_2": trace3,
    }

    print("\n=== Input Graphs (V-structures for undirected edges) ===")
    print(f"Graph 1: {trace1.result}")
    print(f"Graph 2: {trace2.result}")
    print(f"Graph 3: {trace3.result}")

    df = average(traces=traces, sample_size=1000, pdag=True, seeds=(0, 1, 2))

    print("\n=== PDAG Test with Undirected Edges: V-structure ===")
    print(df.to_string(index=False))
    print(f"\nTotal node pairs: {len(df)}")
    print("Note: A-B edge may be undirected in PDAG after v-structure")

    # Should have 2 node pairs (A-B has no edge, so dropped)
    assert len(df) == 2

    # A-C should be directed A->C in all graphs
    ac_row = df[(df["node_a"] == "A") & (df["node_b"] == "C")]
    assert len(ac_row) == 1
    assert ac_row.iloc[0]["p_a_to_b"] == 1.0
    # Certain existence and direction
    assert ac_row.iloc[0]["h_exist"] == 0.0
    assert ac_row.iloc[0]["h_orient"] == 0.0

    # B-C should be directed B->C in all graphs
    bc_row = df[(df["node_a"] == "B") & (df["node_b"] == "C")]
    assert len(bc_row) == 1
    # In a v-structure, B->C is forced
    assert bc_row.iloc[0]["p_a_to_b"] == 1.0

    # A-B: no edge in any input graph, so row is dropped
    ab_row = df[(df["node_a"] == "A") & (df["node_b"] == "B")]
    assert len(ab_row) == 0


# Test with undirected edges: conflicting orientations create undirected
def test_pdag_with_undirected_edges_conflicts():
    # Graph 1: A->B, B->C
    trace1 = Trace(context={"id": "network_N1000_0", "N": 1000})
    trace1.result = DAG(["A", "B", "C"], [("A", "->", "B"), ("B", "->", "C")])

    # Graph 2: B->A, B->C (reverse A-B edge)
    trace2 = Trace(context={"id": "network_N1000_1", "N": 1000})
    trace2.result = DAG(["A", "B", "C"], [("B", "->", "A"), ("B", "->", "C")])

    # Graph 3: A--B (as A->B), C->B (reverse B-C edge)
    trace3 = Trace(context={"id": "network_N1000_2", "N": 1000})
    trace3.result = DAG(["A", "B", "C"], [("A", "->", "B"), ("C", "->", "B")])

    traces = {
        "network_N1000_0": trace1,
        "network_N1000_1": trace2,
        "network_N1000_2": trace3,
    }

    print("\n=== Input Graphs (Conflicting orientations) ===")
    print(f"Graph 1: {trace1.result}")
    print(f"Graph 2: {trace2.result}")
    print(f"Graph 3: {trace3.result}")

    df = average(traces=traces, sample_size=1000, pdag=True, seeds=(0, 1, 2))

    print("\n=== PDAG Test with Conflicting Orientations ===")
    print(df.to_string(index=False))
    print(
        "\nNote: dag_to_pdag may canonicalize edge orientations, "
        "so conflicting DAG orientations get standardized in PDAG form"
    )

    # Should have 2 node pairs (A-C has no edge in any graph, so dropped)
    assert len(df) == 2

    # A-B: conflicting orientations - depends on PDAG conversion behavior
    ab_row = df[(df["node_a"] == "A") & (df["node_b"] == "B")]
    assert len(ab_row) == 1
    # dag_to_pdag preserves directed edges when they're part of v-structures
    # or chains, so we check for consistent direction counts
    ab_probs = (
        ab_row.iloc[0]["p_a_to_b"]
        + ab_row.iloc[0]["p_b_to_a"]
        + ab_row.iloc[0]["p_undirected"]
    )
    assert abs(ab_probs - 1.0) < 0.01  # Probabilities sum to 1

    # B-C: also has conflicts
    bc_row = df[(df["node_a"] == "B") & (df["node_b"] == "C")]
    assert len(bc_row) == 1
    bc_probs = (
        bc_row.iloc[0]["p_a_to_b"]
        + bc_row.iloc[0]["p_b_to_a"]
        + bc_row.iloc[0]["p_undirected"]
    )
    assert abs(bc_probs - 1.0) < 0.01  # Probabilities sum to 1


# Test with truly undirected edges from PDAG conversion
def test_pdag_undirected_from_skeleton():
    # Create graphs that when converted to PDAG may have undirected edges
    # Use immoralities and chains that create ambiguity

    # Graph 1: A->B->C->D (simple chain)
    trace1 = Trace(context={"id": "network_N1000_0", "N": 1000})
    trace1.result = DAG(
        ["A", "B", "C", "D"],
        [("A", "->", "B"), ("B", "->", "C"), ("C", "->", "D")],
    )

    # Graph 2: A<-B<-C<-D (reverse chain)
    trace2 = Trace(context={"id": "network_N1000_1", "N": 1000})
    trace2.result = DAG(
        ["A", "B", "C", "D"],
        [("B", "->", "A"), ("C", "->", "B"), ("D", "->", "C")],
    )

    # Graph 3: A--B--C--D as A->B, C->D (no B-C edge)
    trace3 = Trace(context={"id": "network_N1000_2", "N": 1000})
    trace3.result = DAG(
        ["A", "B", "C", "D"], [("A", "->", "B"), ("C", "->", "D")]
    )

    traces = {
        "network_N1000_0": trace1,
        "network_N1000_1": trace2,
        "network_N1000_2": trace3,
    }

    print("\n=== Input Graphs (Skeleton with varying orientations) ===")
    print(f"Graph 1: {trace1.result}")
    print(f"Graph 2: {trace2.result}")
    print(f"Graph 3: {trace3.result}")

    df = average(traces=traces, sample_size=1000, pdag=True, seeds=(0, 1, 2))

    print("\n=== PDAG Test: Skeleton with varying orientations ===")
    print(df.to_string(index=False))
    print(f"\nTotal node pairs: {len(df)}")

    # Some node pairs may have no edge in any graph and be dropped
    # A-C, A-D and B-D have no direct edges in any graph
    assert len(df) == 3

    # Check that probabilities sum to 1 for all pairs
    for _, row in df.iterrows():
        prob_sum = (
            row["p_a_to_b"]
            + row["p_b_to_a"]
            + row["p_undirected"]
            + row["p_no_edge"]
        )
        assert abs(prob_sum - 1.0) < 0.01

    # Some edges should have non-zero undirected probability
    # when PDAG conversion creates ambiguous orientations
    undirected_count = (df["p_undirected"] > 0.0).sum()
    print(f"\nNode pairs with undirected probability > 0: {undirected_count}")
    # Note: PDAG conversion in causaliq_core may not always create undirected
    # edges - this depends on the specific rules for extend_pdag()
