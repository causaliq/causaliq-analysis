# Unit tests for migrate module - pure logic without filesystem access.

from enum import Enum

import pytest
from causaliq_core.graph import DAG, PDAG

from causaliq_analysis.migrate import (
    _apply_name_corrections,
    _get_network_name,
    _json_serialise,
    filter_traces,
    trace_to_dag,
    trace_to_pdag,
)
from causaliq_analysis.trace import Trace


# Test _apply_name_corrections applies known corrections.
def test_apply_name_corrections_applies_correction() -> None:
    dag = DAG(["HTshotOnTarget", "B"], [("HTshotOnTarget", "->", "B")])

    result = _apply_name_corrections(dag)

    assert "HTshotsOnTarget" in result.nodes
    assert "HTshotOnTarget" not in result.nodes


# Test _apply_name_corrections returns unchanged if no corrections needed.
def test_apply_name_corrections_no_change() -> None:
    dag = DAG(["A", "B"], [("A", "->", "B")])

    result = _apply_name_corrections(dag)

    assert result.nodes == ["A", "B"]


# Test _json_serialise handles Enum types.
def test_json_serialise_enum() -> None:
    class TestEnum(Enum):
        VALUE_ONE = 1
        VALUE_TWO = 2

    result = _json_serialise(TestEnum.VALUE_ONE)
    assert result == "VALUE_ONE"


# Test _json_serialise handles objects with args tuple (Prefer-style).
def test_json_serialise_args_tuple() -> None:
    class PreferLike:
        def __init__(self, value: str) -> None:
            self.args = (value,)

    obj = PreferLike("none")
    result = _json_serialise(obj)
    assert result == "none"


# Test _json_serialise handles objects with name attribute.
def test_json_serialise_name_attribute() -> None:
    class NamedObject:
        def __init__(self, name: str) -> None:
            self.name = name

    obj = NamedObject("test_name")
    result = _json_serialise(obj)
    assert result == "test_name"


# Test _json_serialise handles objects with value attribute.
def test_json_serialise_value_attribute() -> None:
    class ValueObject:
        def __init__(self, value: int) -> None:
            self.value = value

    obj = ValueObject(42)
    result = _json_serialise(obj)
    assert result == 42


# Test _json_serialise falls back to str() representation.
def test_json_serialise_str_fallback() -> None:
    class NoSpecialAttrs:
        def __str__(self) -> str:
            return "custom_string"

    obj = NoSpecialAttrs()
    result = _json_serialise(obj)
    assert result == "custom_string"


# Test trace_to_dag raises TypeError when result is PDAG not DAG.
def test_trace_to_dag_pdag_result_raises_type_error() -> None:
    trace = Trace({"id": "TEST/test", "N": 100})
    # Create a PDAG (not a DAG) with an undirected edge
    pdag = PDAG(nodes=["A", "B"], edges=[("A", "-", "B")])
    trace.result = pdag

    with pytest.raises(TypeError, match="not a DAG"):
        trace_to_dag(trace)


# Test trace_to_pdag returns PDAG result as-is.
def test_trace_to_pdag_pdag_result_returns_unchanged() -> None:
    trace = Trace({"id": "TEST/test", "N": 100})
    # Create a PDAG (not a DAG) with undirected edge
    pdag = PDAG(
        nodes=["A", "B", "C"], edges=[("A", "-", "B"), ("B", "-", "C")]
    )
    trace.result = pdag

    result = trace_to_pdag(trace)

    assert result is pdag  # Same object returned
    assert isinstance(result, PDAG)
    assert not isinstance(result, DAG)


# Test trace_to_pdag raises TypeError for invalid result type.
def test_trace_to_pdag_invalid_result_type_raises_type_error() -> None:
    trace = Trace({"id": "TEST/test", "N": 100})
    trace.result = "not a graph"  # type: ignore

    with pytest.raises(TypeError, match="not a DAG or PDAG"):
        trace_to_pdag(trace)


# Test _get_network_name extracts name from id when 'in' not present.
def test_get_network_name_from_id() -> None:
    trace = Trace({"id": "ALGO/MODE/network/N1000", "N": 1000})
    # Create a result so trace_to_graphml can proceed
    dag = DAG(nodes=["A", "B"], edges=[("A", "->", "B")])
    trace.result = dag

    name = _get_network_name(trace)

    # parts[-2] is "network" (second-to-last part before N1000)
    assert name == "network"


# Test _get_network_name returns "G" when neither 'in' nor 'id' with parts.
def test_get_network_name_fallback_to_g() -> None:
    trace = Trace({"N": 100})
    # No 'in' and no 'id' in context

    name = _get_network_name(trace)

    assert name == "G"


# Test _get_network_name returns "G" when id has insufficient parts.
def test_get_network_name_short_id_fallback() -> None:
    trace = Trace({"id": "X/Y", "N": 100})
    # id has exactly 2 parts, len(parts) >= 2, so should return parts[-2]

    name = _get_network_name(trace)

    # With id "X/Y", parts = ["X", "Y"], parts[-2] = "X"
    assert name == "X"


# Test filter_traces with seed filters correctly.
def test_filter_traces_by_seed() -> None:
    # Create traces with seed-like IDs
    traces = {
        "N1000_0": Trace({"id": "TABU/STD/net/N1000_0", "N": 1000}),
        "N1000_1": Trace({"id": "TABU/STD/net/N1000_1", "N": 1000}),
        "N1000_2": Trace({"id": "TABU/STD/net/N1000_2", "N": 1000}),
        "N1000_5": Trace({"id": "TABU/STD/net/N1000_5", "N": 1000}),
    }

    filtered = filter_traces(traces, seed=(0, 2))

    assert len(filtered) == 2
    assert "N1000_0" in filtered
    assert "N1000_2" in filtered
    assert "N1000_1" not in filtered
    assert "N1000_5" not in filtered


# Test filter_traces seed with non-numeric parts skipped.
def test_filter_traces_seed_skips_non_numeric() -> None:
    # Create trace with ID that has non-numeric parts
    traces = {
        "abc_def_3": Trace({"id": "TABU/STD/net/abc_def_3", "N": 1000}),
    }

    filtered = filter_traces(traces, seed=(3,))

    # Should find seed 3 despite non-numeric parts
    assert len(filtered) == 1
    assert "abc_def_3" in filtered


# Test filter_traces seed excludes when no matching seed found.
def test_filter_traces_seed_excludes_no_match() -> None:
    traces = {
        "N1000_0": Trace({"id": "TABU/STD/net/N1000_0", "N": 1000}),
        "N1000_1": Trace({"id": "TABU/STD/net/N1000_1", "N": 1000}),
    }

    filtered = filter_traces(traces, seed=(5, 10))

    # No traces match seed 5 or 10
    assert len(filtered) == 0


# Test filter_traces combines sample_size and seed filters.
def test_filter_traces_combined_filters() -> None:
    traces = {
        "N500_0": Trace({"id": "TABU/STD/net/N500_0", "N": 500}),
        "N1000_0": Trace({"id": "TABU/STD/net/N1000_0", "N": 1000}),
        "N1000_5": Trace({"id": "TABU/STD/net/N1000_5", "N": 1000}),
    }

    filtered = filter_traces(traces, sample_size=1000, seed=(0,))

    assert len(filtered) == 1
    assert "N1000_0" in filtered
