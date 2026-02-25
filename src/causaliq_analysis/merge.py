"""
Graph merging functionality for causaliq-analysis.

This module provides functions for merging multiple graphs (DAG, PDAG, PDG)
into a single PDG with weighted edge probabilities.
"""

from typing import Dict, List, Optional, Tuple, Union

from causaliq_core.graph import (
    DAG,
    PDAG,
    PDG,
    EdgeProbabilities,
    EdgeType,
)


def merge_graphs(
    graphs: List[Union[DAG, PDAG, PDG]],
    weights: Optional[List[float]] = None,
) -> PDG:
    """Merge multiple graphs into a single PDG with edge probabilities.

    Combines DAGs, PDAGs, and/or PDGs into a single probabilistic graph.
    DAG/PDAG edges are treated as having probability 1.0 for their edge
    type before averaging.

    Args:
        graphs: List of graphs to merge. Must all have identical node sets.
        weights: Optional weights for each graph. Must sum to 1.0 if
            provided. If None, uniform weights (1/n) are used.

    Returns:
        PDG with weighted average edge probabilities.

    Raises:
        TypeError: If graphs or weights have invalid types.
        ValueError: If graphs list is empty, nodes differ across graphs,
            weights don't match graph count, or weights don't sum to 1.0.

    Example:
        >>> from causaliq_core.graph import DAG, PDAG
        >>> dag1 = DAG(["A", "B"], [("A", "->", "B")])
        >>> dag2 = DAG(["A", "B"], [("B", "->", "A")])
        >>> pdg = merge_graphs([dag1, dag2])
        >>> probs = pdg.get_probabilities("A", "B")
        >>> probs.forward  # P(A -> B)
        0.5
    """
    # Validate graphs argument
    if not isinstance(graphs, list):
        raise TypeError("graphs must be a list")
    if len(graphs) == 0:
        raise ValueError("graphs list cannot be empty")

    valid_types = (DAG, PDAG, PDG)
    for i, graph in enumerate(graphs):
        if not isinstance(graph, valid_types):
            raise TypeError(
                f"graph at index {i} must be DAG, PDAG, or PDG, "
                f"got {type(graph).__name__}"
            )

    # Validate and normalise weights
    if weights is None:
        weights = [1.0 / len(graphs)] * len(graphs)
    else:
        if not isinstance(weights, list):
            raise TypeError("weights must be a list")
        if len(weights) != len(graphs):
            raise ValueError(
                f"weights length ({len(weights)}) must match "
                f"graphs length ({len(graphs)})"
            )
        for i, w in enumerate(weights):
            if not isinstance(w, (int, float)):
                raise TypeError(f"weight at index {i} must be numeric")
            if w < 0:
                raise ValueError(f"weight at index {i} must be non-negative")

        weight_sum = sum(weights)
        if abs(weight_sum - 1.0) > 1e-9:
            raise ValueError(f"weights must sum to 1.0, got {weight_sum:.10f}")

    # Get reference nodes from first graph
    reference_nodes = sorted(graphs[0].nodes)

    # Validate all graphs have identical nodes
    for i, graph in enumerate(graphs[1:], start=1):
        if sorted(graph.nodes) != reference_nodes:
            raise ValueError(
                f"graph at index {i} has different nodes: "
                f"{sorted(graph.nodes)} vs {reference_nodes}"
            )

    # Accumulate weighted probabilities for each node pair
    prob_accum: Dict[Tuple[str, str], Dict[str, float]] = {}

    for i, node_a in enumerate(reference_nodes):
        for node_b in reference_nodes[i + 1 :]:
            prob_accum[(node_a, node_b)] = {
                "forward": 0.0,
                "backward": 0.0,
                "undirected": 0.0,
                "none": 0.0,
            }

    # Process each graph
    for graph, weight in zip(graphs, weights):
        if isinstance(graph, PDG):
            _accumulate_pdg(graph, prob_accum, weight)
        else:
            _accumulate_sdg(graph, prob_accum, weight)

    # Build PDG from accumulated probabilities
    edges: Dict[Tuple[str, str], EdgeProbabilities] = {}
    for (node_a, node_b), probs in prob_accum.items():
        # Only include edges with non-zero existence probability
        if probs["none"] < 1.0 - 1e-9:
            edges[(node_a, node_b)] = EdgeProbabilities(
                forward=probs["forward"],
                backward=probs["backward"],
                undirected=probs["undirected"],
                none=probs["none"],
            )

    return PDG(reference_nodes, edges)


def _accumulate_pdg(
    pdg: PDG,
    accum: Dict[Tuple[str, str], Dict[str, float]],
    weight: float,
) -> None:
    """Accumulate weighted probabilities from a PDG.

    Args:
        pdg: Source PDG.
        accum: Accumulator dictionary to update.
        weight: Weight for this graph's contribution.
    """
    for (node_a, node_b), probs_dict in accum.items():
        edge_probs = pdg.get_probabilities(node_a, node_b)
        probs_dict["forward"] += weight * edge_probs.forward
        probs_dict["backward"] += weight * edge_probs.backward
        probs_dict["undirected"] += weight * edge_probs.undirected
        probs_dict["none"] += weight * edge_probs.none


def _accumulate_sdg(
    graph: Union[DAG, PDAG],
    accum: Dict[Tuple[str, str], Dict[str, float]],
    weight: float,
) -> None:
    """Accumulate weighted probabilities from a DAG or PDAG.

    DAG/PDAG edges are converted to probability 1.0 for their edge type.

    Args:
        graph: Source DAG or PDAG.
        accum: Accumulator dictionary to update.
        weight: Weight for this graph's contribution.
    """
    for (node_a, node_b), probs_dict in accum.items():
        # Check for directed edge A -> B (stored as (A, B): DIRECTED)
        edge_a_to_b = graph.edges.get((node_a, node_b))
        # Check for directed edge B -> A (stored as (B, A): DIRECTED)
        edge_b_to_a = graph.edges.get((node_b, node_a))

        if edge_a_to_b == EdgeType.DIRECTED:
            # A -> B (forward direction)
            probs_dict["forward"] += weight
        elif edge_b_to_a == EdgeType.DIRECTED:
            # B -> A (backward relative to canonical A, B)
            probs_dict["backward"] += weight
        elif edge_a_to_b == EdgeType.UNDIRECTED:
            # Undirected edges stored in canonical order (A < B)
            probs_dict["undirected"] += weight
        elif edge_b_to_a == EdgeType.UNDIRECTED:
            # Should not happen for canonical order, but handle it
            probs_dict["undirected"] += weight
        elif edge_a_to_b is not None or edge_b_to_a is not None:
            # Other edge types treated as undirected
            probs_dict["undirected"] += weight
        else:
            # No edge
            probs_dict["none"] += weight
