"""Unit tests for edge-level PDG analysis."""

import pytest
from causaliq_core.graph import PDG, EdgeProbabilities


def _pdg() -> PDG:
    """Return a three-node PDG with probabilistic and absent edges."""
    return PDG(
        ["A", "B", "C"],
        {
            ("A", "B"): EdgeProbabilities(
                forward=0.6, backward=0.1, undirected=0.0, none=0.3
            ),
            ("A", "C"): EdgeProbabilities(
                forward=0.1, backward=0.1, undirected=0.08, none=0.72
            ),
            ("B", "C"): EdgeProbabilities(none=1.0),
        },
    )


def test_threshold_graph_keeps_dominant_states() -> None:
    """A thresholded graph holds one deterministic state per edge."""
    from causaliq_analysis.edge_analysis import threshold_graph

    result = threshold_graph(_pdg(), 0.2)

    assert result.get_probabilities("A", "B").forward == 1.0
    assert result.get_probabilities("A", "C").undirected == 1.0
    assert result.get_probabilities("B", "C").p_exist == 0.0


def test_threshold_graph_keeps_backward_state() -> None:
    """A backward-dominant pair becomes a deterministic backward edge."""
    from causaliq_analysis.edge_analysis import threshold_graph

    pdg = PDG(
        ["A", "B"],
        {
            ("A", "B"): EdgeProbabilities(
                forward=0.1, backward=0.8, undirected=0.0, none=0.1
            )
        },
    )

    result = threshold_graph(pdg, 0.3)

    assert result.get_probabilities("A", "B").backward == 1.0


def test_threshold_graph_drops_edges_below_threshold() -> None:
    """Edges below the threshold become absent."""
    from causaliq_analysis.edge_analysis import threshold_graph

    result = threshold_graph(_pdg(), 0.5)

    assert result.get_probabilities("A", "B").p_exist == 1.0
    assert result.get_probabilities("A", "C").p_exist == 0.0


@pytest.mark.parametrize("threshold", [-0.1, 1.1])
def test_threshold_graph_rejects_invalid_threshold(
    threshold: float,
) -> None:
    """A threshold outside [0, 1] is rejected."""
    from causaliq_analysis.edge_analysis import threshold_graph

    with pytest.raises(ValueError, match="between 0.0 and 1.0"):
        threshold_graph(_pdg(), threshold)


def test_pdg_edge_agreement_lists() -> None:
    """Existence and direction agreement use the documented definitions."""
    from causaliq_analysis.edge_analysis import pdg_edge_agreement

    values = pdg_edge_agreement(
        _pdg(), present_threshold=0.0, direction_threshold=0.5
    )

    assert values["exist_agree"] == pytest.approx([0.7, 0.72])
    assert values["dir_agree"] == pytest.approx([0.6 / 0.7])


def test_pdg_edge_agreement_splits_undirected_mass() -> None:
    """Undirected probability is split equally between the orientations."""
    from causaliq_analysis.edge_analysis import pdg_edge_agreement

    values = pdg_edge_agreement(_pdg(), direction_threshold=0.0)

    assert values["dir_agree"] == pytest.approx([0.6 / 0.7, 0.5])


def test_pdg_edge_agreement_present_threshold() -> None:
    """Pairs at or below the presence threshold contribute no value."""
    from causaliq_analysis.edge_analysis import pdg_edge_agreement

    values = pdg_edge_agreement(_pdg(), present_threshold=0.5)

    assert values["exist_agree"] == pytest.approx([0.7])
