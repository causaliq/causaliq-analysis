#
#   Class for metrics and comparisons of values, distributions, graphs
#   and networks
#

from typing import Any, Dict, Optional, Set, Tuple, Union

from causaliq_core.graph import (
    BAYESYS_VERSIONS,
    PDAG,
    PDG,
    EdgeProbabilities,
)
from causaliq_core.utils import ln
from pandas import Series

from causaliq_analysis.merge import source_probabilities

# Low-level edge comparison counts returned by pdag_compare and pdg_compare.
# The first nine are per-edge categories; missing_matched completes the
# 2x2 confusion matrix and is derived separately, so it is not part of
# the counter dictionary but is included here as a public metric name.
EDGE_METRICS: Tuple[str, ...] = (
    "arc_matched",
    "arc_reversed",
    "edge_not_arc",
    "arc_not_edge",
    "edge_matched",
    "arc_extra",
    "edge_extra",
    "arc_missing",
    "edge_missing",
    "missing_matched",
)

# Edge states whose probabilities are stored for each node pair by a PDG.
_EDGE_STATES: Tuple[str, ...] = (
    "forward",
    "backward",
    "undirected",
    "none",
)

# Map (reference state, graph state) to the low-level metric it feeds. For
# deterministic graphs (probabilities 0.0/1.0) this reproduces the integer
# counts obtained by comparing PDAGs directly.
_STATE_METRICS: Dict[Tuple[str, str], str] = {
    ("forward", "forward"): "arc_matched",
    ("forward", "backward"): "arc_reversed",
    ("forward", "undirected"): "edge_not_arc",
    ("forward", "none"): "arc_missing",
    ("backward", "forward"): "arc_reversed",
    ("backward", "backward"): "arc_matched",
    ("backward", "undirected"): "edge_not_arc",
    ("backward", "none"): "arc_missing",
    ("undirected", "forward"): "arc_not_edge",
    ("undirected", "backward"): "arc_not_edge",
    ("undirected", "undirected"): "edge_matched",
    ("undirected", "none"): "edge_missing",
    ("none", "forward"): "arc_extra",
    ("none", "backward"): "arc_extra",
    ("none", "undirected"): "edge_extra",
    ("none", "none"): "missing_matched",
}

# Metrics whose identified edge key is described by the graph's edge state.
# The remainder (arc_missing, edge_missing) use the reference edge state.
_GRAPH_KEYED_METRICS = frozenset(
    {
        "arc_matched",
        "arc_reversed",
        "edge_not_arc",
        "arc_not_edge",
        "edge_matched",
        "arc_extra",
        "edge_extra",
    }
)

# Relative tolerance used by the SHD sanity check for fractional counts.
_SHD_TOL = 1e-9


def _as_number(value: Union[int, float]) -> Union[int, float]:
    """Return an int for whole numbers, else the float unchanged.

    Deterministic comparisons (probabilities of 0.0/1.0) therefore keep
    returning integer counts, matching historical pdag_compare output,
    while probabilistic comparisons return fractional values.

    Args:
        value: Accumulated metric value.

    Returns:
        int(value) when value is a whole number, else value unchanged.
    """
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def _oriented_key(node_a: str, node_b: str, state: str) -> Tuple[str, str]:
    """Return the edge key implied by a canonical pair and edge state.

    Args:
        node_a: First node (alphabetically before node_b).
        node_b: Second node.
        state: One of forward, backward, undirected or none.

    Returns:
        (node_b, node_a) for a backward state, else (node_a, node_b).
    """
    return (node_b, node_a) if state == "backward" else (node_a, node_b)


def _graph_to_pdg(graph: Any) -> PDG:
    """Convert a deterministic graph or PDG to a PDG.

    Args:
        graph: A PDG (returned unchanged), or a deterministic DAG/PDAG
            whose edges become probability 1.0 for their edge state.

    Returns:
        The equivalent PDG.

    Raises:
        TypeError: if graph is neither a PDG nor a PDAG/DAG.
    """
    if isinstance(graph, PDG):
        return graph
    if not isinstance(graph, PDAG):
        raise TypeError("bad arg type for compared_to")

    nodes = list(graph.nodes)
    edges: Dict[Tuple[str, str], EdgeProbabilities] = {}
    for i, node_a in enumerate(nodes):
        for node_b in nodes[i + 1 :]:
            probs = source_probabilities(graph, node_a, node_b)
            if probs.p_exist > 0.0:
                edges[(node_a, node_b)] = probs
    return PDG(nodes, edges)


def pdg_compare(
    graph: Any,
    reference: Any,
    bayesys: Optional[str] = None,
    identify_edges: bool = False,
) -> Dict[str, Any]:
    """Compare a PDG with a reference PDG.

    Both arguments may be PDGs or deterministic graphs (DAG/PDAG/CPDAG),
    which are converted to PDGs first, each edge state then having
    probability 1.0. Every node pair contributes the sixteen products of
    the reference and graph edge-state probabilities, so the low-level
    edge metrics are fractional for probabilistic graphs and add up to
    1.0 for each node pair.

    Args:
        graph (PDG): graph which is to be compared
        reference (PDG): reference graph for comparison
        bayesys (str, optional): version of Bayesys metrics to return, or
                                 None if not required
        identify_edges (bool): whether edges in each low level category
                              (e.g. arc_missing) are to be included in
                              metrics returned.

    Raises:
        TypeError: if bad argument types
        ValueError: if bad bayesys value or the graphs have different nodes

    Returns:
        dict: structural comparison metrics
    """
    # Validation logic from compared_to method
    if not isinstance(reference, (PDAG, PDG)) or (
        not isinstance(bayesys, str) and bayesys is not None
    ):
        raise TypeError("bad arg type for compared_to")

    if bayesys is not None and bayesys not in BAYESYS_VERSIONS:
        raise ValueError("bad bayesys value for compared_to")

    graph_pdg = _graph_to_pdg(graph)
    reference_pdg = _graph_to_pdg(reference)

    if graph_pdg.nodes != reference_pdg.nodes:
        raise ValueError("comparing two graphs with different nodes")

    metrics: Dict[str, Union[int, float]] = {
        name: 0 for name in EDGE_METRICS if name != "missing_matched"
    }
    metric_edges: Optional[Dict[str, Set[Any]]] = (
        {m: set() for m in metrics} if identify_edges else None
    )

    # Combine the four edge-state probabilities of each node pair in the
    # reference and graph, accumulating the sixteen fractional products.

    nodes = reference_pdg.nodes
    for i, node_a in enumerate(nodes):
        for node_b in nodes[i + 1 :]:
            ref_probs = reference_pdg.get_probabilities(node_a, node_b)
            graph_probs = graph_pdg.get_probabilities(node_a, node_b)
            for ref_state in _EDGE_STATES:
                p_ref = getattr(ref_probs, ref_state)
                if p_ref == 0.0:
                    continue
                for graph_state in _EDGE_STATES:
                    p_graph = getattr(graph_probs, graph_state)
                    if p_graph == 0.0:
                        continue
                    metric = _STATE_METRICS[(ref_state, graph_state)]
                    if metric == "missing_matched":
                        continue
                    metrics[metric] += p_ref * p_graph
                    if metric_edges is not None:
                        state = (
                            graph_state
                            if metric in _GRAPH_KEYED_METRICS
                            else ref_state
                        )
                        key = _oriented_key(node_a, node_b, state)
                        metric_edges[metric].add(key)

    # Deterministic comparisons keep integer counts for compatibility.
    metrics = {name: _as_number(value) for name, value in metrics.items()}

    max_edges = int(0.5 * len(nodes) * (len(nodes) - 1))
    missing = max_edges - sum(metrics.values())
    metrics["missing_matched"] = _as_number(missing)

    # compute standard and edge SHD metrics and perform sanity check

    shd_e = (
        metrics["arc_extra"]
        + metrics["edge_extra"]
        + metrics["arc_missing"]
        + metrics["edge_missing"]
    )
    shd = (
        shd_e
        + metrics["arc_reversed"]
        + metrics["arc_not_edge"]
        + metrics["edge_not_arc"]
    )
    tp = metrics["arc_matched"] + metrics["edge_matched"]

    # Alternative computation allowing weighting of reversed and edge/arc
    # to be varied more easily.

    mis = (
        1.0 * (metrics["arc_not_edge"] + metrics["edge_not_arc"])
        + 1.0 * metrics["arc_reversed"]
    )
    fp = metrics["arc_extra"] + metrics["edge_extra"] + mis
    fn = metrics["arc_missing"] + metrics["edge_missing"] + mis
    p = tp / (tp + fp) if tp + fp > 0 else None
    r = tp / (tp + fn) if tp + fn > 0 else None
    f1 = (
        0.0
        if p is None or r is None or (p == 0 and r == 0)
        else 2 * p * r / (p + r)
    )
    total = tp + metrics["missing_matched"] + shd
    if abs(total - max_edges) > _SHD_TOL * max(1, max_edges):
        raise RuntimeError("SHD sanity check: {}".format(metrics))

    # Create base metrics dict with correct types
    result_metrics: Dict[str, Union[int, float, None]] = dict(metrics)
    result_metrics.update({"shd": shd, "p": p, "r": r, "f1": f1})

    # add in Bayesys metrics and edge details if required

    if bayesys is not None:
        num_ref_edges = sum(
            probs.p_exist for probs in reference_pdg.edges.values()
        )
        result_metrics.update(
            bayesys_metrics(result_metrics, max_edges, num_ref_edges)
        )
    if identify_edges and metric_edges is not None:
        # Add edges separately to avoid type conflicts
        final_result: Dict[str, Any] = dict(result_metrics)
        final_result["edges"] = metric_edges
        return final_result

    return result_metrics


def pdag_compare(
    graph: Any,
    reference: Any,
    bayesys: Optional[str] = None,
    identify_edges: bool = False,
) -> Dict[str, Any]:
    """Compare a pdag with a reference pdag.

    Retained for compatibility; delegates to :func:`pdg_compare`, which
    converts both graphs to PDGs before comparing them. For deterministic
    graphs the low-level metrics are integers, matching historical output.

    Args:
        graph (PDAG): graph which is to be compared
        reference (PDAG): reference graph for comparison
        bayesys (str, optional): version of Bayesys metrics to return, or
                                 None if not required
        identify_edges (bool): whether edges in each low level category
                              (e.g. arc_missing) are to be included in
                              metrics returned.

    Raises:
        TypeError: if bad argument types

    Returns:
        dict: structural comparison metrics
    """
    if not isinstance(reference, PDAG) or (
        not isinstance(bayesys, str) and bayesys is not None
    ):
        raise TypeError("bad arg type for compared_to")

    return pdg_compare(
        graph, reference, bayesys=bayesys, identify_edges=identify_edges
    )


def kl(dist: Series, ref_dist: Series) -> float:
    """Returns the Kullback-Liebler Divergence of dist from ref_dist.

    Args:
        dist (Series): distribution to compute KL from ...
        ref_dist (Series): ... the reference/theoretical distribution

    Raises:
        TypeError: if both arguments not Panda Series
        ValueError: if dists have different indices or bad values

    Returns:
        float: divergence value
    """
    if not isinstance(dist, Series) or not isinstance(ref_dist, Series):
        raise TypeError("kl() called with bad argument types")

    if set(dist.index) != set(ref_dist.index):
        raise ValueError("kl: dist and ref_dist indices different")
    if dist.hasnans or ref_dist.hasnans:
        raise ValueError("kl: distributions contain NaNs")
    if (
        dist.max() > 1.000001
        or dist.min() < -0.000001
        or ref_dist.max() > 1.000001
        or ref_dist.min() <= -0.000001
    ):
        raise ValueError("kl: distributions with bad values")

    result = 0.0
    for key, prob in dist.items():
        prob = prob if prob > 0 else 1e-16
        ref_val = ref_dist[key]  # type: ignore[call-overload,unused-ignore]  # noqa: E501
        ref_prob = ref_val if ref_val > 0 else 1e-16
        result += prob * ln(prob / ref_prob)

    return result


def bayesys_metrics(
    metrics: Dict[str, Union[int, float, None]],
    max_edges: int,
    num_ref_edges: float,
) -> Dict[str, float]:

    # Compute true/false postive/negatives
    # If reference has an edge but graph has arc this is considered a match
    # Bayesys comparison introduces concept of a "half-match" when graph has
    # an edge, or an oppositely orientated arc compared to reference.
    # Note edge_matched is not counted as TP giving incorrectly high shd-b for
    # CPDAG comparisons
    # This implementation has extra protection against divide by zero errors

    # Ensure we get numeric values from metrics (they should all be int/float)
    arc_matched = float(metrics["arc_matched"] or 0)
    arc_not_edge = float(metrics["arc_not_edge"] or 0)
    edge_matched = float(metrics["edge_matched"] or 0)
    arc_reversed = float(metrics["arc_reversed"] or 0)
    edge_not_arc = float(metrics["edge_not_arc"] or 0)
    arc_extra = float(metrics["arc_extra"] or 0)
    edge_extra = float(metrics["edge_extra"] or 0)

    TP = float(arc_matched + arc_not_edge + edge_matched)
    TP2 = float(arc_reversed + edge_not_arc)
    FP = float(arc_extra + edge_extra)
    TN = max_edges - num_ref_edges - FP
    FN = num_ref_edges - TP - 0.5 * TP2

    # Precision, recall and F1 but allowing for half-matches.

    precision = (
        1.0 if TP + TP2 + FP == 0 else (TP + 0.5 * TP2) / (TP + TP2 + FP)
    )
    recall = (
        1.0 if TP + TP2 + FN == 0 else (TP + 0.5 * TP2) / (TP + 0.5 * TP2 + FN)
    )
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall > 0
        else 0.0
    )  # Bayesys code sets this to 1.0!

    # SHD computed as usual but now includes half-matches
    # BSF and DDM as defined by Constantinou

    SHD = FP + FN

    # DDM and positive_worth divide by the number of reference edges, which
    # is zero when the reference graph has no edges; guard that degenerate
    # case against a divide by zero error.
    DDM = (
        (TP + 0.5 * TP2 - FN - FP) / num_ref_edges
        if num_ref_edges != 0
        else 0.0
    )
    positive_worth = 1.0 / num_ref_edges if num_ref_edges != 0 else 0.0
    negative_worth = (
        1.0 / (max_edges - num_ref_edges)
        if max_edges != num_ref_edges
        else 1.0
    )
    BSF = 0.5 * (
        (TP + 0.5 * TP2) * positive_worth
        + TN * negative_worth
        - FP * negative_worth
        - FN * positive_worth
    )

    return {
        "tp-b": TP,
        "tp2-b": TP2,
        "fp-b": FP,
        "tn-b": TN,
        "fn-b": FN,
        "p-b": precision,
        "r-b": recall,
        "f1-b": f1,
        "shd-b": SHD,
        "ddm": DDM,
        "bsf": BSF,
    }
