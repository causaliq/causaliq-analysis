"""Edge-level analysis of probabilistic DAGs (PDGs).

The helpers here operate on a PDG's per-node-pair edge probabilities. A
PDG can be reduced to deterministic edge states at a probability
threshold, and its within-ensemble agreement can be summarised for
description (no reference graph) workflows.
"""

from typing import Any

from causaliq_core.graph import PDG, EdgeProbabilities

from causaliq_analysis.metrics import graph_to_pdg

__all__ = ["pdg_edge_agreement", "threshold_graph"]


def threshold_graph(graph: Any, threshold: float) -> PDG:
    """Return a PDG whose edge states are thresholded deterministically.

    A node pair keeps its edge only when ``p_exist >= threshold``. The
    dominant direction is used when the forward and backward
    probabilities differ; an exact tie becomes undirected.

    Args:
        graph: PDG or deterministic graph to threshold.
        threshold: Minimum ``p_exist`` for an edge to be retained.

    Returns:
        PDG whose edges carry a single deterministic state.

    Raises:
        ValueError: If the threshold is not a probability.
    """
    _require_probability(threshold, "threshold")
    pdg = graph_to_pdg(graph)
    edges = {
        pair: _thresholded_edge(probs)
        for pair, probs in pdg.edges.items()
        if probs.p_exist >= threshold
    }
    return PDG(list(pdg.nodes), edges)


def _thresholded_edge(probs: EdgeProbabilities) -> EdgeProbabilities:
    """Return the deterministic edge state of a probability vector.

    Args:
        probs: Edge probabilities of one node pair.

    Returns:
        Forward, backward or undirected probability of 1.0.
    """
    if probs.forward > probs.backward:
        return EdgeProbabilities(forward=1.0, none=0.0)
    if probs.backward > probs.forward:
        return EdgeProbabilities(backward=1.0, none=0.0)
    return EdgeProbabilities(undirected=1.0, none=0.0)


def pdg_edge_agreement(
    graph: Any,
    present_threshold: float = 0.0,
    direction_threshold: float = 0.0,
) -> dict[str, list[float]]:
    """Return per-pair existence and direction agreement measures.

    Existence agreement of a node pair is ``max(p_exist, 1 - p_exist)``
    for pairs above the presence threshold. Direction agreement splits
    the undirected probability equally between the two orientations and
    reports the larger share for pairs above the direction threshold.

    Args:
        graph: PDG or deterministic graph to describe.
        present_threshold: Minimum ``p_exist`` for existence agreement.
        direction_threshold: Minimum ``p_exist`` for direction agreement.

    Returns:
        Mapping with the lists ``exist_agree`` and ``dir_agree``.

    Raises:
        ValueError: If a threshold is not a probability.
    """
    _require_probability(present_threshold, "present_threshold")
    _require_probability(direction_threshold, "direction_threshold")
    pdg = graph_to_pdg(graph)
    exist: list[float] = []
    direction: list[float] = []
    for node_a, node_b in pdg.node_pairs():
        probs = pdg.get_probabilities(node_a, node_b)
        p_exist = probs.p_exist
        if p_exist > present_threshold:
            exist.append(max(p_exist, 1.0 - p_exist))
        if p_exist > 0.0 and p_exist >= direction_threshold:
            direction.append(_direction_agreement(probs, p_exist))
    return {"exist_agree": exist, "dir_agree": direction}


def _direction_agreement(
    probs: EdgeProbabilities,
    p_exist: float,
) -> float:
    """Return the dominant direction share of an existing edge.

    Args:
        probs: Edge probabilities of one node pair.
        p_exist: Probability that the edge exists.

    Returns:
        Larger of the two orientation shares, with undirected
        probability split equally between them.
    """
    half_undirected = probs.undirected / 2.0
    forward = (probs.forward + half_undirected) / p_exist
    backward = (probs.backward + half_undirected) / p_exist
    return max(forward, backward)


def _require_probability(value: float, name: str) -> None:
    """Require a value to be a probability between 0.0 and 1.0.

    Args:
        value: Threshold value to validate.
        name: Parameter name used in the error message.

    Raises:
        ValueError: If the value is not a probability.
    """
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be between 0.0 and 1.0, got {value}")
