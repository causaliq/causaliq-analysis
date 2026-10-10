#   Test PDG comparison metrics

import pytest
from causaliq_core.graph import PDG, EdgeProbabilities

import tests.fixtures.example_dags as ex_dag
import tests.fixtures.example_pdags as ex_pdag
import tests.fixtures.example_pdgs as ex_pdg
import tests.fixtures.example_sdgs as ex_sdg
from causaliq_analysis.metrics import (
    EDGE_METRICS,
    pdag_compare,
    pdg_compare,
)

DERIVED = {"shd", "p", "r", "f1"}


# Test TypeError for bad argument type for pdg parameters
def test_metrics_pdg_type_error1():
    with pytest.raises(TypeError):
        pdg_compare(ex_pdg.empty())
    with pytest.raises(TypeError):
        pdg_compare(ex_pdg.empty(), 37)
    with pytest.raises(TypeError):
        pdg_compare(ex_pdg.empty(), "bad arg type")
    with pytest.raises(TypeError):
        pdg_compare(ex_pdg.empty(), ex_sdg.ab())
    # Invalid graph argument (reference is valid) is also rejected
    with pytest.raises(TypeError):
        pdg_compare(ex_sdg.ab(), ex_pdg.empty())
    with pytest.raises(TypeError):
        pdg_compare(37, ex_pdg.empty())


# Test TypeError for bad argument type for bayesys parameter
def test_metrics_pdg_type_error2():
    with pytest.raises(TypeError):
        pdg_compare(ex_pdg.empty(), ex_pdg.empty(), False)
    with pytest.raises(TypeError):
        pdg_compare(ex_pdg.empty(), ex_pdg.empty(), ex_pdg.empty())


# Test ValueError for bad value for bayesys parameter
def test_metrics_pdg_value_error1():
    with pytest.raises(ValueError):
        pdg_compare(ex_pdg.empty(), ex_pdg.empty(), "unsupported")
    with pytest.raises(ValueError):
        pdg_compare(ex_pdg.empty(), ex_pdg.empty(), "bayesys1.5")
    with pytest.raises(ValueError):
        pdg_compare(ex_pdg.empty(), ex_pdg.empty(), "v1.3")


# Test ValueError for different node sets
def test_metrics_pdg_value_error2():
    with pytest.raises(ValueError):
        pdg_compare(ex_pdg.empty(), ex_pdg.a())
    with pytest.raises(ValueError):
        pdg_compare(ex_pdg.a(), ex_pdg.empty())
    with pytest.raises(ValueError):
        pdg_compare(ex_pdg.ab(), ex_pdg.a())


# Test the sixteen fractional products from the task specification
def test_metrics_pdg_fractional_counts():
    graph = ex_pdg.ab_fractional2()
    reference = ex_pdg.ab_fractional()
    metrics = pdg_compare(graph, reference)

    assert metrics["arc_matched"] == pytest.approx(0.27)
    assert metrics["arc_reversed"] == pytest.approx(0.22)
    assert metrics["edge_not_arc"] == pytest.approx(0.07)
    assert metrics["arc_not_edge"] == pytest.approx(0.0)
    assert metrics["edge_matched"] == pytest.approx(0.0)
    assert metrics["arc_extra"] == pytest.approx(0.21)
    assert metrics["edge_extra"] == pytest.approx(0.03)
    assert metrics["arc_missing"] == pytest.approx(0.14)
    assert metrics["edge_missing"] == pytest.approx(0.0)
    assert metrics["missing_matched"] == pytest.approx(0.06)


# Test the derived metrics from the fractional counts
def test_metrics_pdg_fractional_derived():
    graph = ex_pdg.ab_fractional2()
    reference = ex_pdg.ab_fractional()
    metrics = pdg_compare(graph, reference)

    assert metrics["shd"] == pytest.approx(0.67)
    assert metrics["p"] == pytest.approx(0.3375)
    assert metrics["r"] == pytest.approx(0.27 / 0.70)
    assert metrics["f1"] == pytest.approx(0.36)


# Test that fractional counts for a pair sum to max_edges
def test_metrics_pdg_counts_sum_to_max_edges():
    graph = ex_pdg.ab_fractional2()
    reference = ex_pdg.ab_fractional()
    metrics = pdg_compare(graph, reference)

    total = sum(metrics[name] for name in EDGE_METRICS)
    assert total == pytest.approx(1.0)


# Test self comparison of an uncertain PDG matches the specification
def test_metrics_pdg_self_comparison():
    pdg = ex_pdg.ab_fractional()
    metrics = pdg_compare(pdg, pdg)

    # Both orientations are possible so reversed mass remains
    assert metrics["arc_matched"] == pytest.approx(0.37)
    assert metrics["arc_reversed"] == pytest.approx(0.12)
    assert metrics["arc_extra"] == pytest.approx(0.21)
    assert metrics["arc_missing"] == pytest.approx(0.21)
    assert metrics["missing_matched"] == pytest.approx(0.09)
    assert metrics["shd"] == pytest.approx(0.54)
    assert metrics["f1"] == pytest.approx(0.37 / 0.70)


# Test identical deterministic PDGs give a perfect score
def test_metrics_pdg_deterministic_perfect():
    metrics = pdg_compare(ex_pdg.ab(), ex_pdg.ab())

    assert metrics["arc_matched"] == 1
    assert metrics["shd"] == pytest.approx(0.0)
    assert metrics["p"] == pytest.approx(1.0)
    assert metrics["r"] == pytest.approx(1.0)
    assert metrics["f1"] == pytest.approx(1.0)


# Test deterministic PDG counts remain integers
def test_metrics_pdg_deterministic_integers():
    metrics = pdg_compare(ex_pdg.ab(), ex_pdg.ab())

    assert isinstance(metrics["arc_matched"], int)
    assert isinstance(metrics["missing_matched"], int)
    assert metrics["missing_matched"] == 0


# Test deterministic PDG comparison matches the PDAG comparison
def test_metrics_pdg_matches_pdag_compare():
    dag1 = ex_dag.ab()
    dag2 = ex_dag.ba()
    pdg_metrics = pdg_compare(ex_pdg.from_pdag(dag1), ex_pdg.from_pdag(dag2))
    pdag_metrics = pdag_compare(dag1, dag2)

    assert pdg_metrics == pdag_metrics


# Test the pdag_compare wrapper delegates to pdg_compare
def test_metrics_pdg_wrapper_delegates():
    dag1 = ex_pdag.abc_acyclic()
    dag2 = ex_pdag.abc4()

    assert pdag_compare(dag1, dag2) == pdg_compare(dag1, dag2)


# Test identified edges for a deterministic arc_reversed comparison
def test_metrics_pdg_identify_edges_deterministic():
    metrics = pdg_compare(ex_pdg.ab(), ex_pdg.ba(), identify_edges=True)

    assert metrics["edges"]["arc_reversed"] == {("A", "B")}
    assert metrics["edges"]["arc_matched"] == set()


# Test identified edges for a fractional comparison
def test_metrics_pdg_identify_edges_fractional():
    metrics = pdg_compare(
        ex_pdg.ab_forward_undirected(),
        ex_pdg.ab(),
        identify_edges=True,
    )

    assert metrics["edges"]["arc_matched"] == {("A", "B")}
    assert metrics["edges"]["edge_not_arc"] == {("A", "B")}


# Test Bayesys comparison rejects mismatched node sets (v1.3 removed)
def test_metrics_pdg_bayesys_mismatched_nodes_rejected():
    graph = ex_pdg.from_pdag(ex_dag.ab())
    reference = PDG(
        ["A", "B", "C"],
        {("A", "B"): EdgeProbabilities(forward=1.0, none=0.0)},
    )

    with pytest.raises(ValueError):
        pdg_compare(graph, reference, bayesys="v1.5+")


# Test EDGE_METRICS lists exactly the counts pdg_compare returns
def test_metrics_pdg_edge_metrics_constant_matches_output():
    metrics = pdg_compare(ex_pdg.ab(), ex_pdg.ab())

    assert set(metrics) - DERIVED == set(EDGE_METRICS)
    assert len(EDGE_METRICS) == len(set(EDGE_METRICS))
