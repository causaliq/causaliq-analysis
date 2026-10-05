#   Test graph file reading helpers

import pytest

import tests.fixtures.example_dags as ex_dag
from causaliq_analysis.graph_io import (
    is_pdg_graphml,
    read_graph_or_pdg_file,
)


# Test is_pdg_graphml detects the PDG probability key
def test_is_pdg_graphml():
    assert is_pdg_graphml('<key id="p_forward" for="edge"/>') is True
    assert is_pdg_graphml("<graph id='G'></graph>") is False


# Test a PDG GraphML file is read as a PDG
def test_read_graph_or_pdg_file_pdg(tmp_path):
    from causaliq_core.graph import PDG, EdgeProbabilities
    from causaliq_core.graph.io import graphml

    pdg = PDG(
        ["A", "B"],
        {("A", "B"): EdgeProbabilities(forward=0.8, none=0.2)},
    )
    path = tmp_path / "graph.graphml"
    with open(path, "w") as f:
        graphml.write_pdg(pdg, f)

    result = read_graph_or_pdg_file(str(path))
    assert isinstance(result, PDG)
    assert result.get_probabilities("A", "B").forward == pytest.approx(0.8)


# Test a deterministic GraphML file is read as a graph
def test_read_graph_or_pdg_file_graph(tmp_path):
    from causaliq_core.graph.io import graphml

    path = tmp_path / "graph.graphml"
    with open(path, "w") as f:
        graphml.write(ex_dag.ab(), f)

    result = read_graph_or_pdg_file(str(path))
    assert result.nodes == ["A", "B"]
    assert len(result.edges) == 1


# Test an xdsl file is read via the Bayesian network reader
def test_read_graph_or_pdg_file_xdsl(monkeypatch):
    sentinel = object()
    monkeypatch.setattr(
        "causaliq_core.bn.io.read_bn",
        lambda path: type("BN", (), {"dag": sentinel})(),
    )
    assert read_graph_or_pdg_file("net.xdsl") is sentinel


# Test a missing graphml path falls back to the graph reader
def test_read_graph_or_pdg_file_missing_graphml(monkeypatch):
    sentinel = object()
    monkeypatch.setattr(
        "causaliq_core.graph.io.read_graph", lambda path: sentinel
    )
    assert read_graph_or_pdg_file("missing.graphml") is sentinel
