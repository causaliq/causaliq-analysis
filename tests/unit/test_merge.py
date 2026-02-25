"""Unit tests for graph merging functionality."""

import pytest
from causaliq_core.graph import (
    DAG,
    PDAG,
    PDG,
    EdgeProbabilities,
    EdgeType,
)

from causaliq_analysis.merge import merge_graphs


# Test merge_graphs returns a PDG instance.
def test_merge_graphs_returns_pdg() -> None:
    dag1 = DAG(["A", "B"], [("A", "->", "B")])
    dag2 = DAG(["A", "B"], [("A", "->", "B")])
    result = merge_graphs([dag1, dag2])
    assert isinstance(result, PDG)


# Test merging two identical DAGs produces probability 1.0.
def test_merge_identical_dags_produces_certainty() -> None:
    dag1 = DAG(["A", "B"], [("A", "->", "B")])
    dag2 = DAG(["A", "B"], [("A", "->", "B")])
    pdg = merge_graphs([dag1, dag2])
    probs = pdg.get_probabilities("A", "B")
    assert probs.forward == 1.0
    assert probs.backward == 0.0
    assert probs.undirected == 0.0
    assert probs.none == 0.0


# Test merging DAGs with opposite directions splits probability.
def test_merge_opposite_directions_splits_probability() -> None:
    dag1 = DAG(["A", "B"], [("A", "->", "B")])
    dag2 = DAG(["A", "B"], [("B", "->", "A")])
    pdg = merge_graphs([dag1, dag2])
    probs = pdg.get_probabilities("A", "B")
    assert probs.forward == 0.5
    assert probs.backward == 0.5
    assert probs.undirected == 0.0
    assert probs.none == 0.0


# Test merging DAG with no edge graphs.
def test_merge_with_no_edge_graphs() -> None:
    dag1 = DAG(["A", "B"], [("A", "->", "B")])
    dag2 = DAG(["A", "B"], [])  # No edge
    pdg = merge_graphs([dag1, dag2])
    probs = pdg.get_probabilities("A", "B")
    assert probs.forward == 0.5
    assert probs.backward == 0.0
    assert probs.undirected == 0.0
    assert probs.none == 0.5


# Test merging PDAGs with undirected edges.
def test_merge_pdag_undirected_edges() -> None:
    pdag1 = PDAG(["A", "B"], [("A", "-", "B")])
    pdag2 = PDAG(["A", "B"], [("A", "-", "B")])
    pdg = merge_graphs([pdag1, pdag2])
    probs = pdg.get_probabilities("A", "B")
    assert probs.forward == 0.0
    assert probs.backward == 0.0
    assert probs.undirected == 1.0
    assert probs.none == 0.0


# Test merging mixed directed and undirected edges.
def test_merge_mixed_directed_undirected() -> None:
    dag = DAG(["A", "B"], [("A", "->", "B")])
    pdag = PDAG(["A", "B"], [("A", "-", "B")])
    pdg = merge_graphs([dag, pdag])
    probs = pdg.get_probabilities("A", "B")
    assert probs.forward == 0.5
    assert probs.backward == 0.0
    assert probs.undirected == 0.5
    assert probs.none == 0.0


# Test merging with custom weights.
def test_merge_with_custom_weights() -> None:
    dag1 = DAG(["A", "B"], [("A", "->", "B")])
    dag2 = DAG(["A", "B"], [("B", "->", "A")])
    pdg = merge_graphs([dag1, dag2], weights=[0.75, 0.25])
    probs = pdg.get_probabilities("A", "B")
    assert probs.forward == 0.75
    assert probs.backward == 0.25
    assert probs.undirected == 0.0
    assert probs.none == 0.0


# Test merging three graphs with uniform weights.
def test_merge_three_graphs_uniform() -> None:
    dag1 = DAG(["A", "B"], [("A", "->", "B")])
    dag2 = DAG(["A", "B"], [("B", "->", "A")])
    dag3 = DAG(["A", "B"], [])
    pdg = merge_graphs([dag1, dag2, dag3])
    probs = pdg.get_probabilities("A", "B")
    assert abs(probs.forward - 1 / 3) < 1e-9
    assert abs(probs.backward - 1 / 3) < 1e-9
    assert probs.undirected == 0.0
    assert abs(probs.none - 1 / 3) < 1e-9


# Test merging PDG inputs.
def test_merge_pdg_inputs() -> None:
    pdg1 = PDG(
        ["A", "B"],
        {("A", "B"): EdgeProbabilities(forward=0.8, none=0.2)},
    )
    pdg2 = PDG(
        ["A", "B"],
        {("A", "B"): EdgeProbabilities(forward=0.4, backward=0.4, none=0.2)},
    )
    result = merge_graphs([pdg1, pdg2])
    probs = result.get_probabilities("A", "B")
    assert abs(probs.forward - 0.6) < 1e-9  # (0.8 + 0.4) / 2
    assert abs(probs.backward - 0.2) < 1e-9  # (0.0 + 0.4) / 2
    assert probs.undirected == 0.0
    assert abs(probs.none - 0.2) < 1e-9


# Test merging DAG with PDG.
def test_merge_dag_with_pdg() -> None:
    dag = DAG(["A", "B"], [("A", "->", "B")])
    pdg = PDG(
        ["A", "B"],
        {("A", "B"): EdgeProbabilities(backward=1.0, none=0.0)},
    )
    result = merge_graphs([dag, pdg])
    probs = result.get_probabilities("A", "B")
    assert probs.forward == 0.5
    assert probs.backward == 0.5


# Test result preserves node set.
def test_merge_preserves_nodes() -> None:
    dag1 = DAG(["A", "B", "C"], [("A", "->", "B")])
    dag2 = DAG(["A", "B", "C"], [("B", "->", "C")])
    pdg = merge_graphs([dag1, dag2])
    assert pdg.nodes == ["A", "B", "C"]


# Test edges with no occurrence are not included.
def test_no_edge_pairs_excluded() -> None:
    dag1 = DAG(["A", "B", "C"], [("A", "->", "B")])
    dag2 = DAG(["A", "B", "C"], [("A", "->", "B")])
    pdg = merge_graphs([dag1, dag2])
    # A-C pair has no edges in any graph, should have p_none=1.0
    probs = pdg.get_probabilities("A", "C")
    assert probs.none == 1.0
    # But should return default EdgeProbabilities, not stored explicitly
    assert ("A", "C") not in pdg.edges


# Test single graph returns equivalent PDG.
def test_single_graph_merge() -> None:
    dag = DAG(["A", "B"], [("A", "->", "B")])
    pdg = merge_graphs([dag])
    probs = pdg.get_probabilities("A", "B")
    assert probs.forward == 1.0
    assert probs.none == 0.0


# Test TypeError for non-list graphs argument.
def test_graphs_not_list_raises_typeerror() -> None:
    dag = DAG(["A", "B"], [("A", "->", "B")])
    with pytest.raises(TypeError, match="graphs must be a list"):
        merge_graphs(dag)  # type: ignore[arg-type]


# Test ValueError for empty graphs list.
def test_empty_graphs_raises_valueerror() -> None:
    with pytest.raises(ValueError, match="graphs list cannot be empty"):
        merge_graphs([])


# Test TypeError for invalid graph type in list.
def test_invalid_graph_type_raises_typeerror() -> None:
    with pytest.raises(TypeError, match="must be DAG, PDAG, or PDG"):
        merge_graphs(["not a graph"])  # type: ignore[list-item]


# Test TypeError for non-list weights.
def test_weights_not_list_raises_typeerror() -> None:
    dag1 = DAG(["A", "B"], [("A", "->", "B")])
    dag2 = DAG(["A", "B"], [("A", "->", "B")])
    with pytest.raises(TypeError, match="weights must be a list"):
        merge_graphs([dag1, dag2], weights=0.5)  # type: ignore[arg-type]


# Test ValueError for weights length mismatch.
def test_weights_length_mismatch_raises_valueerror() -> None:
    dag1 = DAG(["A", "B"], [("A", "->", "B")])
    dag2 = DAG(["A", "B"], [("A", "->", "B")])
    with pytest.raises(ValueError, match="weights length"):
        merge_graphs([dag1, dag2], weights=[0.5])


# Test TypeError for non-numeric weight.
def test_non_numeric_weight_raises_typeerror() -> None:
    dag1 = DAG(["A", "B"], [("A", "->", "B")])
    dag2 = DAG(["A", "B"], [("A", "->", "B")])
    with pytest.raises(TypeError, match="weight at index 1 must be numeric"):
        merge_graphs([dag1, dag2], weights=[0.5, "invalid"])  # type: ignore


# Test ValueError for negative weight.
def test_negative_weight_raises_valueerror() -> None:
    dag1 = DAG(["A", "B"], [("A", "->", "B")])
    dag2 = DAG(["A", "B"], [("A", "->", "B")])
    with pytest.raises(ValueError, match="must be non-negative"):
        merge_graphs([dag1, dag2], weights=[1.5, -0.5])


# Test ValueError for weights not summing to 1.0.
def test_weights_sum_not_one_raises_valueerror() -> None:
    dag1 = DAG(["A", "B"], [("A", "->", "B")])
    dag2 = DAG(["A", "B"], [("A", "->", "B")])
    with pytest.raises(ValueError, match="weights must sum to 1.0"):
        merge_graphs([dag1, dag2], weights=[0.3, 0.3])


# Test ValueError for graphs with different nodes.
def test_different_nodes_raises_valueerror() -> None:
    dag1 = DAG(["A", "B"], [("A", "->", "B")])
    dag2 = DAG(["A", "C"], [("A", "->", "C")])
    with pytest.raises(ValueError, match="different nodes"):
        merge_graphs([dag1, dag2])


# Test weights that sum to 1.0 within tolerance.
def test_weights_sum_tolerance() -> None:
    dag1 = DAG(["A", "B"], [("A", "->", "B")])
    dag2 = DAG(["A", "B"], [("B", "->", "A")])
    dag3 = DAG(["A", "B"], [])
    # These weights sum to 1.0 - 1e-10, within tolerance
    weights = [1 / 3, 1 / 3, 1 / 3]
    pdg = merge_graphs([dag1, dag2, dag3], weights=weights)
    assert isinstance(pdg, PDG)


# Test zero weight effectively excludes graph.
def test_zero_weight_excludes_graph() -> None:
    dag1 = DAG(["A", "B"], [("A", "->", "B")])
    dag2 = DAG(["A", "B"], [("B", "->", "A")])
    pdg = merge_graphs([dag1, dag2], weights=[1.0, 0.0])
    probs = pdg.get_probabilities("A", "B")
    assert probs.forward == 1.0
    assert probs.backward == 0.0


# Test undirected edge stored in reverse order (non-canonical).
def test_undirected_edge_reverse_order() -> None:
    # Create PDAG and manually set edge in reverse order (B, A) not (A, B)
    pdag = PDAG(["A", "B"], [])
    pdag.edges[("B", "A")] = EdgeType.UNDIRECTED

    pdg = merge_graphs([pdag])
    probs = pdg.get_probabilities("A", "B")
    assert probs.undirected == 1.0
    assert probs.forward == 0.0


# Test bidirected edge type treated as undirected.
def test_bidirected_edge_treated_as_undirected() -> None:
    # Create PDAG with bidirected edge to test other type handling.
    pdag = PDAG(["A", "B"], [])
    pdag.edges[("A", "B")] = EdgeType.BIDIRECTED

    pdg = merge_graphs([pdag])
    probs = pdg.get_probabilities("A", "B")
    assert probs.undirected == 1.0
    assert probs.forward == 0.0
    assert probs.backward == 0.0
