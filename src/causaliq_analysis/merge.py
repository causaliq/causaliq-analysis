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
    dag_to_pdag,
)

VALID_STRATEGIES = frozenset({"average", "noisy_or", "max"})


def merge_graphs(
    graphs: List[Union[DAG, PDAG, PDG]],
    weights: Optional[List[float]] = None,
    cpdag: bool = False,
    strategy: str = "average",
) -> PDG:
    """Merge multiple graphs into a single PDG with edge probabilities.

    Combines DAGs, PDAGs, and/or PDGs into a single probabilistic
    graph using the specified merge strategy.

    Args:
        graphs: List of graphs to merge. Must all have
            identical node sets.
        weights: Optional weights for each graph. Must sum to
            1.0 if provided. If None, uniform weights (1/n)
            are used.
        cpdag: If True, convert DAGs to their CPDAG
            (equivalence class) before merging.
        strategy: Merge strategy. 'average' for weighted
            average of probability vectors (default).
            'noisy_or' for noisy-OR existence with weighted
            orientation. 'max' to select the most confident
            source per edge.

    Returns:
        PDG with combined edge probabilities.

    Raises:
        TypeError: If graphs or weights have invalid types.
        ValueError: If graphs list is empty, nodes differ,
            weights don't match graph count, weights don't
            sum to 1.0, or strategy is invalid.

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

    # Convert DAGs to CPDAGs if requested
    if cpdag:
        graphs = [dag_to_pdag(g) if isinstance(g, DAG) else g for g in graphs]

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

    # Validate strategy
    if strategy not in VALID_STRATEGIES:
        raise ValueError(
            f"strategy must be one of "
            f"{sorted(VALID_STRATEGIES)}, "
            f"got '{strategy}'"
        )

    # Non-average strategies use per-source combination
    if strategy != "average":
        return _merge_per_source(graphs, weights, reference_nodes, strategy)

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


def _source_probs(
    graph: Union[DAG, PDAG, PDG],
    node_a: str,
    node_b: str,
) -> EdgeProbabilities:
    """Extract edge probabilities for a node pair.

    For DAG/PDAG, edges are converted to probability 1.0
    for their type. Absent edges become p_none=1.0.

    Args:
        graph: Source graph (DAG, PDAG, or PDG).
        node_a: First node (canonical order).
        node_b: Second node.

    Returns:
        Edge probabilities for the node pair.
    """
    if isinstance(graph, PDG):
        return graph.get_probabilities(node_a, node_b)

    edge_ab = graph.edges.get((node_a, node_b))
    edge_ba = graph.edges.get((node_b, node_a))

    if edge_ab == EdgeType.DIRECTED:
        return EdgeProbabilities(forward=1.0, none=0.0)
    if edge_ba == EdgeType.DIRECTED:
        return EdgeProbabilities(backward=1.0, none=0.0)
    if edge_ab == EdgeType.UNDIRECTED or edge_ba == EdgeType.UNDIRECTED:
        return EdgeProbabilities(undirected=1.0, none=0.0)
    if edge_ab is not None or edge_ba is not None:
        return EdgeProbabilities(undirected=1.0, none=0.0)
    return EdgeProbabilities()


def _combine_noisy_or(
    source_probs: List[EdgeProbabilities],
    weights: List[float],
) -> EdgeProbabilities:
    """Combine edge probabilities using noisy-OR.

    Existence follows noisy-OR: an edge exists if any
    source supports it. Orientation is a weighted average
    of conditional directional probabilities.

    With weights w_i (summing to 1.0) and n sources, the
    exponent for source i is alpha_i = w_i * n. This gives
    alpha=1.0 (standard noisy-OR) for uniform weights.

    Args:
        source_probs: Per-source edge probabilities.
        weights: Normalised weights for each source.

    Returns:
        Combined edge probabilities.
    """
    n = len(source_probs)

    # Noisy-OR: p_none = product(p_none_i ^ alpha_i)
    p_none = 1.0
    for i, probs in enumerate(source_probs):
        alpha = weights[i] * n
        if alpha > 0:
            p_none *= probs.none**alpha

    p_exist = 1.0 - p_none
    if p_exist < 1e-12:
        return EdgeProbabilities()

    # Weighted orientation from contributing sources
    total_w = 0.0
    fwd_sum = 0.0
    bwd_sum = 0.0
    und_sum = 0.0

    for i, probs in enumerate(source_probs):
        src_exist = probs.p_exist
        if src_exist < 1e-12:
            continue
        contrib = weights[i] * src_exist
        total_w += contrib
        fwd_sum += contrib * probs.forward / src_exist
        bwd_sum += contrib * probs.backward / src_exist
        und_sum += contrib * probs.undirected / src_exist

    if total_w < 1e-12:  # pragma: no cover
        third = p_exist / 3.0
        return EdgeProbabilities(
            forward=third,
            backward=third,
            undirected=third,
            none=p_none,
        )

    fwd = p_exist * fwd_sum / total_w
    bwd = p_exist * bwd_sum / total_w
    und = p_exist * und_sum / total_w

    return EdgeProbabilities(
        forward=fwd,
        backward=bwd,
        undirected=und,
        none=p_none,
    )


def _combine_max(
    source_probs: List[EdgeProbabilities],
    weights: List[float],
) -> EdgeProbabilities:
    """Combine by selecting the most confident source.

    For each edge pair, selects the source with the highest
    weighted existence probability and uses its complete
    probability vector.

    Args:
        source_probs: Per-source edge probabilities.
        weights: Normalised weights for each source.

    Returns:
        Edge probabilities from the most confident source.
    """
    n = len(source_probs)
    best_idx = 0
    best_score = -1.0

    for i, probs in enumerate(source_probs):
        score = probs.p_exist * weights[i] * n
        if score > best_score:
            best_score = score
            best_idx = i

    return source_probs[best_idx]


def _merge_per_source(
    graphs: List[Union[DAG, PDAG, PDG]],
    weights: List[float],
    nodes: List[str],
    strategy: str,
) -> PDG:
    """Merge graphs using per-source combination strategy.

    Collects per-source probabilities for each node pair,
    then applies the specified combination strategy.

    Args:
        graphs: Validated graphs with identical node sets.
        weights: Normalised weights for each graph.
        nodes: Sorted node names.
        strategy: 'noisy_or' or 'max'.

    Returns:
        Merged PDG.
    """
    combine = _combine_noisy_or if strategy == "noisy_or" else _combine_max

    edges: Dict[Tuple[str, str], EdgeProbabilities] = {}

    for i, node_a in enumerate(nodes):
        for node_b in nodes[i + 1 :]:
            src_probs = [_source_probs(g, node_a, node_b) for g in graphs]
            combined = combine(src_probs, weights)
            if combined.none < 1.0 - 1e-9:
                edges[(node_a, node_b)] = combined

    return PDG(nodes, edges)
