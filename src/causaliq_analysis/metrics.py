#
#   Class for metrics and comparisons of values, distributions, graphs
#   and networks
#

from itertools import combinations
from typing import Any, Dict, List, Optional, Set, Tuple, Union

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


def _positive_edge_probs(
    graph: PDAG,
    nodes: List[str],
) -> Dict[Tuple[str, str], EdgeProbabilities]:
    """Return probabilities for node pairs that may have an edge.

    Args:
        graph: Deterministic graph to convert.
        nodes: Node names in canonical order.

    Returns:
        Mapping of node pairs to their non-zero edge probabilities.
    """
    probs_by_pair = {
        (node_a, node_b): source_probabilities(graph, node_a, node_b)
        for node_a, node_b in combinations(nodes, 2)
    }
    return {
        pair: probs
        for pair, probs in probs_by_pair.items()
        if probs.p_exist > 0.0
    }


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
    return PDG(nodes, _positive_edge_probs(graph, nodes))


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
    _validate_compare_args(reference, bayesys)
    graph_pdg, reference_pdg = _convert_pair(graph, reference)
    metrics = _new_metric_counters()
    metric_edges = _new_metric_edges(metrics, identify_edges)
    nodes = reference_pdg.nodes
    _accumulate_pair_metrics(
        reference_pdg, graph_pdg, nodes, metrics, metric_edges
    )
    result_metrics, max_edges = _summary_metrics(metrics, nodes)
    if bayesys is not None:
        _attach_bayesys(result_metrics, reference_pdg, max_edges)
    if identify_edges and metric_edges is not None:
        return _with_edges(result_metrics, metric_edges)
    return result_metrics


def _validate_compare_args(reference: Any, bayesys: Optional[str]) -> None:
    """Validate reference graph and Bayesys arguments for comparison.

    Args:
        reference: Reference graph supplied by the caller.
        bayesys: Requested Bayesys version, or None.

    Raises:
        TypeError: If reference or bayesys has an invalid type.
        ValueError: If the Bayesys version is unknown.
    """
    if not isinstance(reference, (PDAG, PDG)) or (
        not isinstance(bayesys, str) and bayesys is not None
    ):
        raise TypeError("bad arg type for compared_to")
    if bayesys is not None and bayesys not in BAYESYS_VERSIONS:
        raise ValueError("bad bayesys value for compared_to")


def _convert_pair(graph: Any, reference: Any) -> Tuple[PDG, PDG]:
    """Convert both graphs to PDGs and check they share a node set.

    Args:
        graph: Graph being compared.
        reference: Reference graph.

    Returns:
        Tuple of (graph PDG, reference PDG).

    Raises:
        ValueError: If the graphs have different node sets.
    """
    graph_pdg = _graph_to_pdg(graph)
    reference_pdg = _graph_to_pdg(reference)
    if graph_pdg.nodes != reference_pdg.nodes:
        raise ValueError("comparing two graphs with different nodes")
    return graph_pdg, reference_pdg


def _new_metric_counters() -> Dict[str, Union[int, float]]:
    """Return zeroed low-level edge metric counters.

    Returns:
        Dictionary mapping each low-level metric name to zero.
    """
    return {name: 0 for name in EDGE_METRICS if name != "missing_matched"}


def _new_metric_edges(
    metrics: Dict[str, Union[int, float]],
    identify_edges: bool,
) -> Optional[Dict[str, Set[Any]]]:
    """Return per-metric edge sets when edge identification is requested.

    Args:
        metrics: Low-level metric counters that define the metric names.
        identify_edges: Whether edges should be identified.

    Returns:
        Mapping of metric name to an empty set, or None.
    """
    if not identify_edges:
        return None
    return {name: set() for name in metrics}


def _accumulate_pair_metrics(
    reference_pdg: PDG,
    graph_pdg: PDG,
    nodes: List[str],
    metrics: Dict[str, Union[int, float]],
    metric_edges: Optional[Dict[str, Set[Any]]],
) -> None:
    """Accumulate fractional edge metrics over all node pairs.

    Args:
        reference_pdg: Reference graph.
        graph_pdg: Graph being compared.
        nodes: Graph node names.
        metrics: Accumulator updated in place.
        metric_edges: Optional per-metric edge sets updated in place.
    """
    for node_a, node_b in combinations(nodes, 2):
        ref_probs = reference_pdg.get_probabilities(node_a, node_b)
        graph_probs = graph_pdg.get_probabilities(node_a, node_b)
        _accumulate_pair_states(
            node_a, node_b, ref_probs, graph_probs, metrics, metric_edges
        )


def _accumulate_pair_states(
    node_a: str,
    node_b: str,
    ref_probs: EdgeProbabilities,
    graph_probs: EdgeProbabilities,
    metrics: Dict[str, Union[int, float]],
    metric_edges: Optional[Dict[str, Set[Any]]],
) -> None:
    """Accumulate the edge-state products for one node pair.

    Args:
        node_a: First node.
        node_b: Second node.
        ref_probs: Reference edge probabilities.
        graph_probs: Graph edge probabilities.
        metrics: Accumulator updated in place.
        metric_edges: Optional per-metric edge sets updated in place.
    """
    for ref_state in _EDGE_STATES:
        p_ref = getattr(ref_probs, ref_state)
        if p_ref == 0.0:
            continue
        _accumulate_graph_states(
            node_a,
            node_b,
            ref_state,
            p_ref,
            graph_probs,
            metrics,
            metric_edges,
        )


def _accumulate_graph_states(
    node_a: str,
    node_b: str,
    ref_state: str,
    p_ref: float,
    graph_probs: EdgeProbabilities,
    metrics: Dict[str, Union[int, float]],
    metric_edges: Optional[Dict[str, Set[Any]]],
) -> None:
    """Accumulate the graph edge states for one reference edge state.

    Args:
        node_a: First node.
        node_b: Second node.
        ref_state: Reference edge state.
        p_ref: Reference probability for the state.
        graph_probs: Graph edge probabilities.
        metrics: Accumulator updated in place.
        metric_edges: Optional per-metric edge sets updated in place.
    """
    for graph_state in _EDGE_STATES:
        p_graph = getattr(graph_probs, graph_state)
        if p_graph == 0.0:
            continue
        metric = _STATE_METRICS[(ref_state, graph_state)]
        if metric == "missing_matched":
            continue
        metrics[metric] += p_ref * p_graph
        _record_metric_edge(
            metric_edges, metric, node_a, node_b, graph_state, ref_state
        )


def _record_metric_edge(
    metric_edges: Optional[Dict[str, Set[Any]]],
    metric: str,
    node_a: str,
    node_b: str,
    graph_state: str,
    ref_state: str,
) -> None:
    """Record the identified edge for a metric, when requested.

    Args:
        metric_edges: Optional per-metric edge sets updated in place.
        metric: Low-level metric name.
        node_a: First node.
        node_b: Second node.
        graph_state: Graph edge state.
        ref_state: Reference edge state.
    """
    if metric_edges is None:
        return
    state = graph_state if metric in _GRAPH_KEYED_METRICS else ref_state
    metric_edges[metric].add(_oriented_key(node_a, node_b, state))


def _structural_hamming_distance(
    metrics: Dict[str, Union[int, float]],
) -> float:
    """Return the structural Hamming distance from edge metrics.

    Args:
        metrics: Accumulated low-level edge metrics.

    Returns:
        The structural Hamming distance.
    """
    shd_e = (
        metrics["arc_extra"]
        + metrics["edge_extra"]
        + metrics["arc_missing"]
        + metrics["edge_missing"]
    )
    return (
        shd_e
        + metrics["arc_reversed"]
        + metrics["arc_not_edge"]
        + metrics["edge_not_arc"]
    )


def _error_terms(
    metrics: Dict[str, Union[int, float]],
) -> Tuple[float, float]:
    """Return the false positive and false negative counts.

    Reversed arcs and edge/arc mismatches are weighted equally in both
    terms so the weighting can be varied in one place.

    Args:
        metrics: Accumulated low-level edge metrics.

    Returns:
        Tuple of (false positives, false negatives).
    """
    mis = (
        1.0 * (metrics["arc_not_edge"] + metrics["edge_not_arc"])
        + 1.0 * metrics["arc_reversed"]
    )
    fp = metrics["arc_extra"] + metrics["edge_extra"] + mis
    fn = metrics["arc_missing"] + metrics["edge_missing"] + mis
    return fp, fn


def _precision_recall_f1(
    tp: float,
    fp: float,
    fn: float,
) -> Tuple[Optional[float], Optional[float], float]:
    """Return precision, recall and F1 from confusion counts.

    Args:
        tp: True positives (half-matches counted once).
        fp: False positives.
        fn: False negatives.

    Returns:
        Tuple of (precision, recall, f1). Precision and recall are None
        when there are no positive predictions or references.
    """
    p = tp / (tp + fp) if tp + fp > 0 else None
    r = tp / (tp + fn) if tp + fn > 0 else None
    if p is None or r is None or (p == 0 and r == 0):
        return p, r, 0.0
    return p, r, 2 * p * r / (p + r)


def _summary_metrics(
    metrics: Dict[str, Union[int, float]],
    nodes: List[str],
) -> Tuple[Dict[str, Union[int, float, None]], int]:
    """Finalise edge metrics and derive SHD, precision, recall and F1.

    Args:
        metrics: Accumulated low-level edge metrics.
        nodes: Graph node names.

    Returns:
        Tuple of (result metrics, number of possible node pairs).

    Raises:
        RuntimeError: If the SHD sanity check fails.
    """
    max_edges = int(0.5 * len(nodes) * (len(nodes) - 1))
    metrics = {name: _as_number(value) for name, value in metrics.items()}
    missing = max_edges - sum(metrics.values())
    metrics["missing_matched"] = _as_number(missing)
    shd = _structural_hamming_distance(metrics)
    tp = metrics["arc_matched"] + metrics["edge_matched"]
    fp, fn = _error_terms(metrics)
    p, r, f1 = _precision_recall_f1(tp, fp, fn)
    total = tp + metrics["missing_matched"] + shd
    if abs(total - max_edges) > _SHD_TOL * max(1, max_edges):
        raise RuntimeError("SHD sanity check: {}".format(metrics))
    result: Dict[str, Union[int, float, None]] = dict(metrics)
    result.update({"shd": shd, "p": p, "r": r, "f1": f1})
    return result, max_edges


def _attach_bayesys(
    result_metrics: Dict[str, Union[int, float, None]],
    reference_pdg: PDG,
    max_edges: int,
) -> None:
    """Add Bayesys metrics to a result dictionary in place.

    Args:
        result_metrics: Metrics dictionary updated in place.
        reference_pdg: Reference graph.
        max_edges: Number of possible node pairs.
    """
    num_ref_edges = sum(
        probs.p_exist for probs in reference_pdg.edges.values()
    )
    result_metrics.update(
        bayesys_metrics(result_metrics, max_edges, num_ref_edges)
    )


def _with_edges(
    result_metrics: Dict[str, Union[int, float, None]],
    metric_edges: Dict[str, Set[Any]],
) -> Dict[str, Any]:
    """Return the result metrics with the identified edges attached.

    Args:
        result_metrics: Derived metrics dictionary.
        metric_edges: Per-metric identified edge sets.

    Returns:
        The metrics dictionary with an added "edges" entry.
    """
    final_result: Dict[str, Any] = dict(result_metrics)
    final_result["edges"] = metric_edges
    return final_result


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
    """Compute Bayesys-compatible metrics from structural metrics.

    If the reference has an edge but the graph has an arc this is counted
    as a match, and a "half-match" is recorded when the graph has an edge,
    or an oppositely oriented arc, compared to the reference. Note that
    edge_matched is not counted as a true positive, which would otherwise
    give an incorrectly high shd-b for CPDAG comparisons.

    Args:
        metrics: Low-level edge metrics from a PDG comparison.
        max_edges: Number of possible node pairs.
        num_ref_edges: Number of edges in the reference graph.

    Returns:
        Dictionary of Bayesys-compatible metrics.
    """
    tp, tp2, fp, tn, fn = _bayesys_confusion(metrics, max_edges, num_ref_edges)
    return _bayesys_scores(tp, tp2, fp, tn, fn, max_edges, num_ref_edges)


def _bayesys_confusion(
    metrics: Dict[str, Union[int, float, None]],
    max_edges: int,
    num_ref_edges: float,
) -> Tuple[float, float, float, float, float]:
    """Return Bayesys true/false positive/negative counts.

    Args:
        metrics: Low-level edge metrics from a PDG comparison.
        max_edges: Number of possible node pairs.
        num_ref_edges: Number of edges in the reference graph.

    Returns:
        Tuple of (tp, tp2, fp, tn, fn), where tp2 counts half-matches.
    """
    arc_matched = float(metrics["arc_matched"] or 0)
    arc_not_edge = float(metrics["arc_not_edge"] or 0)
    edge_matched = float(metrics["edge_matched"] or 0)
    arc_reversed = float(metrics["arc_reversed"] or 0)
    edge_not_arc = float(metrics["edge_not_arc"] or 0)
    arc_extra = float(metrics["arc_extra"] or 0)
    edge_extra = float(metrics["edge_extra"] or 0)
    tp = float(arc_matched + arc_not_edge + edge_matched)
    tp2 = float(arc_reversed + edge_not_arc)
    fp = float(arc_extra + edge_extra)
    tn = max_edges - num_ref_edges - fp
    fn = num_ref_edges - tp - 0.5 * tp2
    return tp, tp2, fp, tn, fn


def _bayesys_scores(
    tp: float,
    tp2: float,
    fp: float,
    tn: float,
    fn: float,
    max_edges: int,
    num_ref_edges: float,
) -> Dict[str, float]:
    """Compute Bayesys precision, recall, F1, SHD, DDM and BSF.

    DDM and positive_worth divide by the number of reference edges, which
    is zero when the reference graph has no edges; the degenerate case is
    guarded against a divide by zero error.

    Args:
        tp: True positives (half-matches counted once).
        tp2: Half-match count (reversed or edge/arc mismatches).
        fp: False positives.
        tn: True negatives.
        fn: False negatives.
        max_edges: Number of possible node pairs.
        num_ref_edges: Number of edges in the reference graph.

    Returns:
        Dictionary of Bayesys-compatible metrics.
    """
    precision = (
        1.0 if tp + tp2 + fp == 0 else (tp + 0.5 * tp2) / (tp + tp2 + fp)
    )
    recall = (
        1.0 if tp + tp2 + fn == 0 else (tp + 0.5 * tp2) / (tp + 0.5 * tp2 + fn)
    )
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall > 0
        else 0.0
    )
    shd = fp + fn
    ddm = (
        (tp + 0.5 * tp2 - fn - fp) / num_ref_edges
        if num_ref_edges != 0
        else 0.0
    )
    positive_worth = 1.0 / num_ref_edges if num_ref_edges != 0 else 0.0
    negative_worth = (
        1.0 / (max_edges - num_ref_edges)
        if max_edges != num_ref_edges
        else 1.0
    )
    bsf = 0.5 * (
        (tp + 0.5 * tp2) * positive_worth
        + tn * negative_worth
        - fp * negative_worth
        - fn * positive_worth
    )
    return {
        "tp-b": tp,
        "tp2-b": tp2,
        "fp-b": fp,
        "tn-b": tn,
        "fn-b": fn,
        "p-b": precision,
        "r-b": recall,
        "f1-b": f1,
        "shd-b": shd,
        "ddm": ddm,
        "bsf": bsf,
    }
