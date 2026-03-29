"""Unit tests for graph merging functionality."""

import pytest
from causaliq_core.graph import (
    DAG,
    PDAG,
    PDG,
    EdgeProbabilities,
    EdgeType,
)

from causaliq_analysis.merge import (
    _combine_noisy_or,
    merge_graphs,
)


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


# Test cpdag=True converts DAGs to CPDAGs before merging.
def test_cpdag_converts_dag_to_equivalence_class() -> None:
    # A -> B -> C is equivalent to A <- B <- C (same v-structures: none)
    # Their CPDAG is A - B - C (all undirected)
    dag1 = DAG(["A", "B", "C"], [("A", "->", "B"), ("B", "->", "C")])
    dag2 = DAG(["A", "B", "C"], [("C", "->", "B"), ("B", "->", "A")])

    # Without cpdag: distinct directions
    pdg_no_cpdag = merge_graphs([dag1, dag2], cpdag=False)
    probs_ab = pdg_no_cpdag.get_probabilities("A", "B")
    assert probs_ab.forward == 0.5
    assert probs_ab.backward == 0.5

    # With cpdag: both become A - B - C, so 100% undirected
    pdg_cpdag = merge_graphs([dag1, dag2], cpdag=True)
    probs_ab_cpdag = pdg_cpdag.get_probabilities("A", "B")
    assert probs_ab_cpdag.undirected == 1.0
    assert probs_ab_cpdag.forward == 0.0


# Test cpdag=True with v-structure preserves directed edges.
def test_cpdag_preserves_v_structure_directions() -> None:
    # A -> B <- C is a v-structure, CPDAG keeps A -> B <- C
    dag = DAG(["A", "B", "C"], [("A", "->", "B"), ("C", "->", "B")])

    pdg = merge_graphs([dag], cpdag=True)
    probs_ab = pdg.get_probabilities("A", "B")
    probs_cb = pdg.get_probabilities("C", "B")
    # Both edges should remain directed into B
    assert probs_ab.forward == 1.0
    assert probs_cb.forward == 1.0


# Test cpdag=False is the default behaviour.
def test_cpdag_default_false() -> None:
    dag = DAG(["A", "B"], [("A", "->", "B")])
    pdg = merge_graphs([dag])
    probs = pdg.get_probabilities("A", "B")
    # Default: DAG edge kept as directed
    assert probs.forward == 1.0
    assert probs.undirected == 0.0


# Test noisy-OR preserves edge from single source.
def test_noisy_or_preserves_single_source_edge() -> None:
    dag1 = DAG(["A", "B"], [("A", "->", "B")])
    dag2 = DAG(["A", "B"], [])
    pdg = merge_graphs([dag1, dag2], strategy="noisy_or")
    probs = pdg.get_probabilities("A", "B")
    # p_none = 0.0^1 * 1.0^1 = 0.0
    assert probs.none == 0.0
    assert probs.forward == 1.0
    assert probs.backward == 0.0


# Test noisy-OR existence with two partial PDG sources.
def test_noisy_or_existence_two_sources() -> None:
    pdg1 = PDG(
        ["A", "B"],
        {("A", "B"): EdgeProbabilities(forward=0.8, none=0.2)},
    )
    pdg2 = PDG(
        ["A", "B"],
        {("A", "B"): EdgeProbabilities(backward=0.6, none=0.4)},
    )
    result = merge_graphs([pdg1, pdg2], strategy="noisy_or")
    probs = result.get_probabilities("A", "B")
    # p_none = 0.2 * 0.4 = 0.08
    assert abs(probs.none - 0.08) < 1e-9
    assert abs(probs.p_exist - 0.92) < 1e-9
    # Source 1 has higher p_exist, so forward dominates
    assert probs.forward > probs.backward


# Test noisy-OR blends orientation proportionally.
def test_noisy_or_blends_orientation() -> None:
    pdg1 = PDG(
        ["A", "B"],
        {("A", "B"): EdgeProbabilities(forward=0.9, none=0.1)},
    )
    pdg2 = PDG(
        ["A", "B"],
        {("A", "B"): EdgeProbabilities(undirected=1.0, none=0.0)},
    )
    result = merge_graphs([pdg1, pdg2], strategy="noisy_or")
    probs = result.get_probabilities("A", "B")
    # p_none = 0.1 * 0.0 = 0.0
    assert probs.none == 0.0
    assert probs.forward > 0.4
    assert probs.undirected > 0.4
    assert probs.backward == 0.0


# Test noisy-OR with custom weights.
def test_noisy_or_with_weights() -> None:
    pdg1 = PDG(
        ["A", "B"],
        {("A", "B"): EdgeProbabilities(forward=0.8, none=0.2)},
    )
    pdg2 = PDG(["A", "B"], {})  # no edge
    result = merge_graphs(
        [pdg1, pdg2],
        weights=[0.7, 0.3],
        strategy="noisy_or",
    )
    probs = result.get_probabilities("A", "B")
    # alpha1=1.4, alpha2=0.6; p_none = 0.2^1.4 * 1.0
    expected_none = 0.2**1.4
    assert abs(probs.none - expected_none) < 1e-9
    assert probs.forward > probs.backward


# Test noisy-OR with all sources having no edge.
def test_noisy_or_all_none() -> None:
    dag1 = DAG(["A", "B"], [])
    dag2 = DAG(["A", "B"], [])
    result = merge_graphs([dag1, dag2], strategy="noisy_or")
    probs = result.get_probabilities("A", "B")
    assert probs.none == 1.0


# Test noisy-OR single graph is identity.
def test_noisy_or_single_graph_identity() -> None:
    dag = DAG(["A", "B"], [("A", "->", "B")])
    result = merge_graphs([dag], strategy="noisy_or")
    probs = result.get_probabilities("A", "B")
    assert probs.forward == 1.0
    assert probs.none == 0.0


# Test max strategy picks source with highest existence.
def test_max_picks_highest_existence() -> None:
    pdg1 = PDG(
        ["A", "B"],
        {("A", "B"): EdgeProbabilities(forward=0.6, none=0.4)},
    )
    pdg2 = PDG(
        ["A", "B"],
        {("A", "B"): EdgeProbabilities(backward=0.9, none=0.1)},
    )
    result = merge_graphs([pdg1, pdg2], strategy="max")
    probs = result.get_probabilities("A", "B")
    assert probs.backward == 0.9
    assert probs.none == 0.1


# Test max picks DAG edge over empty graph.
def test_max_picks_dag_over_empty() -> None:
    dag1 = DAG(["A", "B"], [("A", "->", "B")])
    dag2 = DAG(["A", "B"], [])
    result = merge_graphs([dag1, dag2], strategy="max")
    probs = result.get_probabilities("A", "B")
    assert probs.forward == 1.0
    assert probs.none == 0.0


# Test max with weights changes the winner.
def test_max_with_weights_changes_winner() -> None:
    pdg1 = PDG(
        ["A", "B"],
        {("A", "B"): EdgeProbabilities(forward=0.6, none=0.4)},
    )
    pdg2 = PDG(
        ["A", "B"],
        {("A", "B"): EdgeProbabilities(backward=0.7, none=0.3)},
    )
    # Without weights, source 2 wins (0.7 > 0.6)
    result1 = merge_graphs([pdg1, pdg2], strategy="max")
    p1 = result1.get_probabilities("A", "B")
    assert p1.backward == 0.7
    # Heavy weight on source 1 flips winner
    result2 = merge_graphs(
        [pdg1, pdg2],
        weights=[0.8, 0.2],
        strategy="max",
    )
    p2 = result2.get_probabilities("A", "B")
    assert p2.forward == 0.6


# Test invalid strategy raises ValueError.
def test_invalid_strategy_raises_valueerror() -> None:
    dag = DAG(["A", "B"], [("A", "->", "B")])
    with pytest.raises(ValueError, match="strategy must be one of"):
        merge_graphs([dag], strategy="invalid")


# Test default strategy is average (backward compatible).
def test_default_strategy_is_average() -> None:
    dag1 = DAG(["A", "B"], [("A", "->", "B")])
    dag2 = DAG(["A", "B"], [])
    pdg_default = merge_graphs([dag1, dag2])
    pdg_average = merge_graphs([dag1, dag2], strategy="average")
    pd = pdg_default.get_probabilities("A", "B")
    pa = pdg_average.get_probabilities("A", "B")
    assert pd.forward == pa.forward == 0.5
    assert pd.none == pa.none == 0.5


# Test noisy-OR with backward DAG edge.
def test_noisy_or_backward_dag_edge() -> None:
    dag1 = DAG(["A", "B"], [("B", "->", "A")])
    dag2 = DAG(["A", "B"], [])
    result = merge_graphs([dag1, dag2], strategy="noisy_or")
    probs = result.get_probabilities("A", "B")
    assert probs.backward == 1.0
    assert probs.none == 0.0


# Test noisy-OR with undirected PDAG edge.
def test_noisy_or_undirected_pdag() -> None:
    pdag1 = PDAG(["A", "B"], [("A", "-", "B")])
    pdag2 = PDAG(["A", "B"], [])
    result = merge_graphs([pdag1, pdag2], strategy="noisy_or")
    probs = result.get_probabilities("A", "B")
    assert probs.undirected == 1.0
    assert probs.none == 0.0


# Test noisy-OR with bidirected edge as undirected.
def test_noisy_or_bidirected_as_undirected() -> None:
    pdag = PDAG(["A", "B"], [])
    pdag.edges[("A", "B")] = EdgeType.BIDIRECTED
    result = merge_graphs([pdag], strategy="noisy_or")
    probs = result.get_probabilities("A", "B")
    assert probs.undirected == 1.0


# Test _combine_noisy_or with zero-weight source.
def test_combine_noisy_or_zero_weight_source() -> None:
    # Source 1 has edge (weight=0), source 2 has no edge (weight=1)
    # Alpha for source 1 is 0 => skipped in noisy-OR
    # Alpha for source 2 is 2 => p_none = 1.0^2 = 1.0
    # Result: no edge detected (defensive fallback unreachable)
    probs1 = EdgeProbabilities(forward=0.8, none=0.2)
    probs2 = EdgeProbabilities()
    result = _combine_noisy_or([probs1, probs2], [0.0, 1.0])
    assert result.none == 1.0
