#   Test PDAG comparison metrics

import pytest

import tests.fixtures.example_dags as ex_dag
import tests.fixtures.example_pdags as ex_pdag
import tests.fixtures.example_sdgs as ex_sdg
from causaliq_analysis.metrics import pdag_compare


@pytest.fixture
def expected():
    return {
        "arc_matched": 0,
        "arc_reversed": 0,
        "edge_not_arc": 0,
        "arc_not_edge": 0,
        "edge_matched": 0,
        "arc_extra": 0,
        "edge_extra": 0,
        "arc_missing": 0,
        "edge_missing": 0,
        "missing_matched": 0,
        "shd": 0,
        "p": None,
        "r": None,
        "f1": 0.0,
    }


# Test TypeError for bad argument type for pdag parameter
def test_metrics_pdag_type_error1():
    with pytest.raises(TypeError):
        pdag_compare(ex_pdag.empty())
    with pytest.raises(TypeError):
        pdag_compare(ex_pdag.empty(), 37)
    with pytest.raises(TypeError):
        pdag_compare(ex_pdag.empty(), "bad arg type")
    with pytest.raises(TypeError):
        pdag_compare(ex_pdag.empty(), ex_sdg.ab())


# Test TypeError for bad argument type for bayesys parameter
def test_metrics_pdag_type_error2():
    with pytest.raises(TypeError):
        pdag_compare(ex_pdag.empty(), ex_pdag.empty(), False)
    with pytest.raises(TypeError):
        pdag_compare(ex_pdag.empty(), ex_pdag.empty(), False)
    with pytest.raises(TypeError):
        pdag_compare(ex_pdag.empty(), ex_pdag.empty(), ex_pdag.empty())


# Test ValueError for bad value for bayesys parameter
def test_metrics_pdag_value_error1():
    with pytest.raises(ValueError):
        pdag_compare(ex_pdag.empty(), ex_pdag.empty(), "unsupported")
    with pytest.raises(ValueError):
        pdag_compare(ex_pdag.empty(), ex_pdag.empty(), "unsupported")
    with pytest.raises(ValueError):
        pdag_compare(ex_pdag.empty(), ex_pdag.empty(), "bayesys1.5")


# Test ValueError for different node sets
def test_metrics_pdag_value_error2():
    with pytest.raises(ValueError):
        pdag_compare(ex_pdag.empty(), ex_pdag.a())
    with pytest.raises(ValueError):
        pdag_compare(ex_pdag.empty(), ex_dag.a())
    with pytest.raises(ValueError):
        pdag_compare(ex_pdag.asia(), ex_pdag.cancer1())


# Compare empty PDAG with empty PDAG
def test_metrics_pdag_empty_ok1(expected):
    metrics = pdag_compare(ex_pdag.empty(), ex_pdag.empty())
    print("\nempty PDAG compared to empty PDAG:\n{}".format(metrics))
    assert metrics == expected


# Compare empty PDAG with empty DAG
def test_metrics_pdag_empty_ok2(expected):
    metrics = pdag_compare(ex_pdag.empty(), ex_dag.empty())
    print("\nempty PDAG compared to empty DAG:\n{}".format(metrics))
    assert metrics == expected


# Compare empty DAG with empty PDAG
def test_metrics_pdag_empty_ok3(expected):
    metrics = pdag_compare(ex_dag.empty(), ex_pdag.empty())
    print("\nempty DAG compared to empty PDAG:\n{}".format(metrics))
    assert metrics == expected


# Compare empty DAG with empty DAG
def test_metrics_pdag_empty_ok4(expected):
    metrics = pdag_compare(ex_dag.empty(), ex_dag.empty())
    print("\nempty DAG compared to empty DAG:\n{}".format(metrics))
    assert metrics == expected


# single node comparisons


# Compare "A" PDAG with "A" PDAG
def test_metrics_pdag_a_ok1(expected):
    graph = ex_pdag.a()
    reference = ex_pdag.a()
    metrics = pdag_compare(graph, reference)
    print("\n{}\ncompared to\n{}\n{}\n".format(graph, reference, metrics))
    assert metrics == expected


# Compare "A" DAG with "A" PDAG
def test_metrics_pdag_a_ok2(expected):
    graph = ex_dag.a()
    reference = ex_pdag.a()
    metrics = pdag_compare(graph, reference)
    print("\n{}\ncompared to\n{}\n{}\n".format(graph, reference, metrics))
    assert metrics == expected


# two node comparisons


# Compare A -> B PDAG with A -> B PDAG
def test_metrics_pdag_ab_ok1(expected):
    graph = ex_pdag.ab()
    reference = ex_pdag.ab()
    metrics = pdag_compare(graph, reference)
    print("\n{}\ncompared to\n{}\n{}\n".format(graph, reference, metrics))
    expected.update({"arc_matched": 1, "p": 1.0, "r": 1.0, "f1": 1.0})
    assert metrics == expected


# Compare A -> B PDAG with A <- B PDAG
def test_metrics_pdag_ab_ok2(expected):
    graph = ex_pdag.ab()
    reference = ex_pdag.ba()
    metrics = pdag_compare(graph, reference)
    print("\n{}\ncompared to\n{}\n{}\n".format(graph, reference, metrics))
    expected.update({"arc_reversed": 1, "shd": 1, "p": 0.0, "r": 0.0})
    assert metrics == expected


# Compare A <- B PDAG with A -> B DAG
def test_metrics_pdag_ab_ok3(expected):
    graph = ex_pdag.ba()
    reference = ex_dag.ab()
    metrics = pdag_compare(graph, reference)
    print("\n{}\ncompared to\n{}\n{}\n".format(graph, reference, metrics))
    expected.update({"arc_reversed": 1, "shd": 1, "p": 0.0, "r": 0.0})
    assert metrics == expected


# Compare A  B PDAG with A -> B PDAG
def test_metrics_pdag_ab_ok4(expected):
    graph = ex_pdag.a_b()
    reference = ex_pdag.ab()
    metrics = pdag_compare(graph, reference)
    print("\n{}\ncompared to\n{}\n{}\n".format(graph, reference, metrics))
    expected.update({"arc_missing": 1, "shd": 1, "r": 0.0})
    assert metrics == expected


# Compare A <- B DAG with A  B PDAG
def test_metrics_pdag_ab_ok5(expected):
    graph = ex_dag.ba()
    reference = ex_pdag.a_b()
    metrics = pdag_compare(graph, reference)
    print("\n{}\ncompared to\n{}\n{}\n".format(graph, reference, metrics))
    expected.update({"arc_extra": 1, "shd": 1, "p": 0.0})
    assert metrics == expected


# Compare A  B PDAG with A  B PDAG
def test_metrics_pdag_ab_ok6(expected):
    graph = ex_pdag.a_b()
    reference = ex_pdag.a_b()
    metrics = pdag_compare(graph, reference)
    print("\n{}\ncompared to\n{}\n{}\n".format(graph, reference, metrics))
    expected.update({"missing_matched": 1})
    assert metrics == expected


# Compare A - B PDAG with A - B PDAG
def test_metrics_pdag_ab_ok7(expected):
    graph = ex_pdag.ab3()
    reference = ex_pdag.ab3()
    metrics = pdag_compare(graph, reference)
    print("\n{}\ncompared to\n{}\n{}\n".format(graph, reference, metrics))
    expected.update({"edge_matched": 1, "p": 1.0, "r": 1.0, "f1": 1.0})
    assert metrics == expected


# Compare A -> B PDAG with A - B PDAG
def test_metrics_pdag_ab_ok8(expected):
    graph = ex_pdag.ab()
    reference = ex_pdag.ab3()
    metrics = pdag_compare(graph, reference)
    print("\n{}\ncompared to\n{}\n{}\n".format(graph, reference, metrics))
    expected.update({"arc_not_edge": 1, "shd": 1, "p": 0.0, "r": 0.0})
    assert metrics == expected


# Compare A - B PDAG with A -> B DAG
def test_metrics_pdag_ab_ok9(expected):
    graph = ex_pdag.ab3()
    reference = ex_dag.ab()
    metrics = pdag_compare(graph, reference)
    print("\n{}\ncompared to\n{}\n{}\n".format(graph, reference, metrics))
    expected.update({"edge_not_arc": 1, "shd": 1, "p": 0.0, "r": 0.0})
    assert metrics == expected


# Compare A  B DAG with A - B PDAG
def test_metrics_pdag_ab_ok10(expected):
    graph = ex_dag.a_b()
    reference = ex_pdag.ab3()
    metrics = pdag_compare(graph, reference)
    print("\n{}\ncompared to\n{}\n{}\n".format(graph, reference, metrics))
    expected.update({"edge_missing": 1, "shd": 1, "r": 0.0})
    assert metrics == expected


# Compare A - B PDAG with A  B PDAG
def test_metrics_pdag_ab_ok11(expected):
    graph = ex_pdag.ab3()
    reference = ex_pdag.a_b()
    metrics = pdag_compare(graph, reference)
    print("\n{}\ncompared to\n{}\n{}\n".format(graph, reference, metrics))
    expected.update({"edge_extra": 1, "shd": 1, "p": 0.0})
    assert metrics == expected


#   three node comparisons


# Compare A B C PDAG with A B C PDAG
def test_metrics_pdag_abc_ok1(expected):
    graph = ex_pdag.a_b_c()
    reference = ex_pdag.a_b_c()
    metrics = pdag_compare(graph, reference)
    print("\n{}\ncompared to\n{}\n{}\n".format(graph, reference, metrics))
    expected.update({"missing_matched": 3})
    assert metrics == expected


# Compare A->C B PDAG with A B C PDAG
def test_metrics_pdag_abc_ok2(expected):
    graph = ex_pdag.ac_b()
    reference = ex_pdag.a_b_c()
    metrics = pdag_compare(graph, reference)
    print("\n{}\ncompared to\n{}\n{}\n".format(graph, reference, metrics))
    expected.update({"missing_matched": 2, "arc_extra": 1, "shd": 1, "p": 0.0})
    assert metrics == expected


# Compare A B C PDAG with C->A B PDAG
def test_metrics_pdag_abc_ok3(expected):
    graph = ex_pdag.a_b_c()
    reference = ex_pdag.ac_b()
    metrics = pdag_compare(graph, reference)
    print("\n{}\ncompared to\n{}\n{}\n".format(graph, reference, metrics))
    expected.update(
        {"missing_matched": 2, "arc_missing": 1, "shd": 1, "r": 0.0}
    )
    assert metrics == expected


# Compare C->A B PDAG with C->A B PDAG
def test_metrics_pdag_abc_ok4(expected):
    graph = ex_pdag.ac_b()
    reference = ex_pdag.ac_b()
    metrics = pdag_compare(graph, reference)
    print("\n{}\ncompared to\n{}\n{}\n".format(graph, reference, metrics))
    expected.update(
        {"missing_matched": 2, "arc_matched": 1, "p": 1.0, "r": 1.0, "f1": 1.0}
    )
    assert metrics == expected


# Compare A->B->C PDAG with A->B->C PDAG
def test_metrics_pdag_abc_ok5(expected):
    graph = ex_pdag.abc()
    reference = ex_pdag.abc()
    metrics = pdag_compare(graph, reference)
    print("\n{}\ncompared to\n{}\n{}\n".format(graph, reference, metrics))
    expected.update(
        {"missing_matched": 1, "arc_matched": 2, "p": 1.0, "r": 1.0, "f1": 1.0}
    )
    assert metrics == expected


# Compare A->B->C PDAG with A B C PDAG
def test_metrics_pdag_abc_ok6(expected):
    graph = ex_pdag.abc()
    reference = ex_pdag.a_b_c()
    metrics = pdag_compare(graph, reference)
    print("\n{}\ncompared to\n{}\n{}\n".format(graph, reference, metrics))
    expected.update({"missing_matched": 1, "arc_extra": 2, "shd": 2, "p": 0.0})
    assert metrics == expected


# Compare A B C PDAG with A->B->C PDAG
def test_metrics_pdag_abc_ok7(expected):
    graph = ex_pdag.a_b_c()
    reference = ex_pdag.abc()
    metrics = pdag_compare(graph, reference)
    print("\n{}\ncompared to\n{}\n{}\n".format(graph, reference, metrics))
    expected.update(
        {"missing_matched": 1, "arc_missing": 2, "shd": 2, "r": 0.0}
    )
    assert metrics == expected


# Compare A->B->C PDAG with A-B-C PDAG
def test_metrics_pdag_abc_ok8(expected):
    graph = ex_pdag.abc()
    reference = ex_pdag.abc4()
    metrics = pdag_compare(graph, reference)
    print("\n{}\ncompared to\n{}\n{}\n".format(graph, reference, metrics))
    expected.update(
        {"missing_matched": 1, "arc_not_edge": 2, "shd": 2, "p": 0.0, "r": 0.0}
    )
    assert metrics == expected


# Compare A-B-C PDAG with A->B->C PDAG
def test_metrics_pdag_abc_ok9(expected):
    graph = ex_pdag.abc4()
    reference = ex_pdag.abc()
    metrics = pdag_compare(graph, reference)
    print("\n{}\ncompared to\n{}\n{}\n".format(graph, reference, metrics))
    expected.update(
        {"missing_matched": 1, "edge_not_arc": 2, "shd": 2, "p": 0.0, "r": 0.0}
    )
    assert metrics == expected


# Compare A->B->C<-A PDAG with A->B->C<-A PDAG
def test_metrics_pdag_abc_ok10(expected):
    graph = ex_pdag.abc_acyclic()
    reference = ex_pdag.abc_acyclic()
    metrics = pdag_compare(graph, reference)
    print("\n{}\ncompared to\n{}\n{}\n".format(graph, reference, metrics))
    expected.update({"arc_matched": 3, "p": 1.0, "r": 1.0, "f1": 1.0})
    assert metrics == expected


# Compare A B C PDAG with A->B->C<-A PDAG
def test_metrics_pdag_abc_ok11(expected):
    graph = ex_pdag.a_b_c()
    reference = ex_pdag.abc_acyclic()
    metrics = pdag_compare(graph, reference)
    print("\n{}\ncompared to\n{}\n{}\n".format(graph, reference, metrics))
    expected.update({"arc_missing": 3, "shd": 3, "r": 0.0})
    assert metrics == expected


# Compare A->B->C<-A PDAG with A B C PDAG
def test_metrics_pdag_abc_ok12(expected):
    graph = ex_pdag.abc_acyclic()
    reference = ex_pdag.a_b_c()
    metrics = pdag_compare(graph, reference)
    print("\n{}\ncompared to\n{}\n{}\n".format(graph, reference, metrics))
    expected.update({"arc_extra": 3, "shd": 3, "p": 0.0})
    assert metrics == expected


# Compare A->B->C<-A PDAG with A-B-C PDAG
def test_metrics_pdag_abc_ok13(expected):
    graph = ex_pdag.abc_acyclic()
    reference = ex_pdag.abc4()
    metrics = pdag_compare(graph, reference)
    print("\n{}\ncompared to\n{}\n{}\n".format(graph, reference, metrics))
    expected.update(
        {"arc_not_edge": 2, "arc_extra": 1, "shd": 3, "p": 0.0, "r": 0.0}
    )
    assert metrics == expected


# Compare A-B-C PDAG with A->B->C<-A PDAG
def test_metrics_pdag_abc_ok14(expected):
    graph = ex_pdag.abc4()
    reference = ex_pdag.abc_acyclic()
    metrics = pdag_compare(graph, reference)
    print("\n{}\ncompared to\n{}\n{}\n".format(graph, reference, metrics))
    expected.update(
        {"edge_not_arc": 2, "arc_missing": 1, "shd": 3, "p": 0.0, "r": 0.0}
    )
    assert metrics == expected


# Test SHD sanity check RuntimeError on line 145 in metrics.py
def test_metrics_pdag_shd_sanity_check_error(monkeypatch):
    """Test that covers line 145 by triggering the sanity check condition"""

    # The most direct approach: patch the sum builtin function
    # to corrupt the missing_matched calculation
    original_sum = sum

    def corrupted_sum(iterable):
        """Sum that corrupts specific calculations to break sanity check"""
        result = original_sum(iterable)

        # If we're summing metrics values and get 1 (for ab vs ab case),
        # return 0 to make missing_matched = max_edges - 0 = 1 instead of 0
        # This will break the sanity check:
        # tp(1) + missing_matched(1) + shd(0) = 2 != max_edges(1)
        try:
            # Check if this looks like a metrics values sum
            items = (
                list(iterable) if hasattr(iterable, "__iter__") else [iterable]
            )
            if len(items) > 5 and all(isinstance(x, int) for x in items):
                # This is likely the metrics.values() sum
                if result == 1:  # This would be the ab vs ab case
                    return 0  # Corrupt it to break the sanity check
        except (TypeError, ValueError):
            pass

        return result

    # Apply the patch using monkeypatch context manager
    with monkeypatch.context() as m:
        m.setattr("builtins.sum", corrupted_sum)

        # This should trigger the sanity check failure on line 145
        with pytest.raises(RuntimeError, match="SHD sanity check"):
            pdag_compare(ex_pdag.ab(), ex_pdag.ab())
