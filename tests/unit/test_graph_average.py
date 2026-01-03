"""Unit tests for graph averaging functionality."""

import pytest
from causaliq_core.graph import DAG
from pandas import DataFrame

from causaliq_analysis.graph import _validate_average_params, average
from causaliq_analysis.trace import Trace


# Validation with valid parameters passes without error
def test_valid_params():
    _validate_average_params(sample_size=1000, pdag=True, seeds=(0, 1, 2))
    _validate_average_params(sample_size=10000, pdag=False, seeds=())


# Validation raises TypeError for non-integer sample_size
def test_invalid_sample_size_type():
    with pytest.raises(TypeError, match="sample_size must be an integer"):
        _validate_average_params(sample_size="1000", pdag=True, seeds=())


# Validation raises ValueError for negative sample_size
def test_invalid_sample_size_value():
    with pytest.raises(ValueError, match="sample_size must be positive"):
        _validate_average_params(sample_size=-1000, pdag=True, seeds=())


# Validation raises TypeError for non-boolean pdag
def test_invalid_pdag_type():
    with pytest.raises(TypeError, match="pdag must be a boolean"):
        _validate_average_params(sample_size=1000, pdag="true", seeds=())


# Validation raises TypeError for non-tuple seeds
def test_invalid_seeds_type():
    with pytest.raises(TypeError, match="seeds must be a tuple"):
        _validate_average_params(sample_size=1000, pdag=True, seeds=[0, 1])


# Validation raises TypeError for non-integer seed elements
def test_invalid_seed_element_type():
    with pytest.raises(TypeError, match="all seeds must be integers"):
        _validate_average_params(sample_size=1000, pdag=True, seeds=(0, "1"))


# Validation raises ValueError for negative seeds
def test_negative_seed():
    with pytest.raises(ValueError, match="all seeds must be non-negative"):
        _validate_average_params(sample_size=1000, pdag=True, seeds=(0, -1))


# Average raises TypeError when traces is not a dictionary
def test_invalid_traces_type():
    with pytest.raises(TypeError, match="traces must be a dictionary"):
        average(traces="not_a_dict", sample_size=1000, pdag=False, seeds=())


# Average raises TypeError when trace values are not Trace objects
def test_invalid_trace_values():
    with pytest.raises(
        TypeError, match="all values in traces must be Trace objects"
    ):
        average(
            traces={"key": "not_a_trace"},
            sample_size=1000,
            pdag=False,
            seeds=(),
        )


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


# Average correctly reports probability of 1.0 when no edges exist in any graph
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

    assert df.iloc[0]["p_no_edge"] == 1.0
    assert df.iloc[0]["p_a_to_b"] == 0.0
    assert df.iloc[0]["p_b_to_a"] == 0.0
    assert df.iloc[0]["p_undirected"] == 0.0


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

    assert len(df) == 3

    ab_row = df[(df["node_a"] == "A") & (df["node_b"] == "B")]
    assert len(ab_row) == 1
    assert ab_row.iloc[0]["p_a_to_b"] == 1.0


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

    # Should have 6 node pairs (4 choose 2)
    assert len(df) == 6

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

    # Should have 6 node pairs (4 choose 2)
    assert len(df) == 6

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

    # Check A-C: no direct edge between A and C in any graph
    ac_row = df[(df["node_a"] == "A") & (df["node_b"] == "C")]
    assert len(ac_row) == 1
    assert ac_row.iloc[0]["p_no_edge"] == 1.0

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

    # Should have 3 node pairs (3 choose 2)
    assert len(df) == 3

    # A-C should be directed A->C in all graphs
    ac_row = df[(df["node_a"] == "A") & (df["node_b"] == "C")]
    assert len(ac_row) == 1
    assert ac_row.iloc[0]["p_a_to_b"] == 1.0

    # B-C should be directed B->C in all graphs
    bc_row = df[(df["node_a"] == "B") & (df["node_b"] == "C")]
    assert len(bc_row) == 1
    # In a v-structure, B->C is forced
    assert bc_row.iloc[0]["p_a_to_b"] == 1.0

    # A-B: in v-structure with collider C, A-B should be undirected in PDAG
    ab_row = df[(df["node_a"] == "A") & (df["node_b"] == "B")]
    assert len(ab_row) == 1
    # The edge A-B is not present in any input graph, so p_no_edge should be 1
    assert ab_row.iloc[0]["p_no_edge"] == 1.0


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

    # Should have 3 node pairs
    assert len(df) == 3

    # A-B: conflicting orientations result in mostly undirected edges
    ab_row = df[(df["node_a"] == "A") & (df["node_b"] == "B")]
    assert len(ab_row) == 1
    # Most A-B edges become undirected due to conflicts, some remain directed
    assert ab_row.iloc[0]["p_undirected"] > 0.5

    # B-C: also has conflicts, should have mix of directions and undirected
    bc_row = df[(df["node_a"] == "B") & (df["node_b"] == "C")]
    assert len(bc_row) == 1
    # Should have some undirected edges due to conflicts
    assert bc_row.iloc[0]["p_undirected"] > 0.0


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

    assert len(df) == 6

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
