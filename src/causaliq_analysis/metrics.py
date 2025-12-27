#
#   Class for metrics and comparisons of values, distributions, graphs
#   and networks
#

from typing import Any, Dict, Optional, Set, Union

from causaliq_core.graph import BAYESYS_VERSIONS, EdgeType
from causaliq_core.utils import ln
from pandas import Series  # type: ignore


def pdag_compare(
    graph: Any,
    reference: Any,
    bayesys: Optional[str] = None,
    identify_edges: bool = False,
) -> Dict[str, Any]:
    """Compare a pdag with a reference pdag.

    Args:
        graph (PDAG): graph which is to be compared
        reference (PDAG): reference graph for comparison
        bayesys (str, optional): version of Bayesys metrics to return, or None
                                 if not required
        identify_edges (bool): whether edges in each low level category
                              (e.g. arc_missing) are to be included in
                              metrics returned.

    Raises:
        TypeError: if bad argument types

    Returns:
        dict: structural comparison metrics
    """
    # Import PDAG here to avoid circular imports
    from causaliq_core.graph import PDAG

    # Validation logic from compared_to method
    if not isinstance(reference, PDAG) or (
        not isinstance(bayesys, str) and bayesys is not None
    ):
        raise TypeError("bad arg type for compared_to")

    if bayesys is not None and bayesys not in BAYESYS_VERSIONS:
        raise ValueError("bad bayesys value for compared_to")

    if graph.nodes != reference.nodes and bayesys != "v1.3":
        raise ValueError("comparing two graphs with different nodes")

    def _metric(
        ref_type: Any, type: Any, reversed: bool = False
    ) -> str:  # identify count metric name
        if ref_type == EdgeType.DIRECTED and type == EdgeType.DIRECTED:
            return "arc_matched" if not reversed else "arc_reversed"
        elif ref_type == EdgeType.DIRECTED and type == EdgeType.UNDIRECTED:
            return "edge_not_arc"
        elif ref_type == EdgeType.UNDIRECTED and type == EdgeType.DIRECTED:
            return "arc_not_edge"
        elif ref_type == EdgeType.DIRECTED and type is None:
            return "arc_missing"
        elif ref_type == EdgeType.UNDIRECTED and type is None:
            return "edge_missing"
        else:
            return "edge_matched"

    edges = graph.edges
    ref_edges = reference.edges

    metrics = {
        "arc_matched": 0,
        "arc_reversed": 0,
        "edge_not_arc": 0,
        "arc_not_edge": 0,
        "edge_matched": 0,
        "arc_extra": 0,
        "edge_extra": 0,
        "arc_missing": 0,
        "edge_missing": 0,
    }
    metric_edges: Optional[Dict[str, Set[Any]]] = (
        {m: set() for m in metrics} if identify_edges else None
    )

    # Loop over all edges in tested graph looking for match in reference graph
    # Include case of arcs that have same type but are oppositely orientated
    # Count edges/arcs in graph not in reference graph too

    for e, t in edges.items():
        if e in ref_edges:
            metric = _metric(ref_edges[e], t)
        elif (e[1], e[0]) in ref_edges:
            metric = _metric(ref_edges[(e[1], e[0])], t, reversed=True)
        else:
            metric = "arc_extra" if t == EdgeType.DIRECTED else "edge_extra"
        metrics[metric] += 1
        if identify_edges is True and metric_edges is not None:
            metric_edges[metric].add(e)

    # loop over edges in reference not in graph

    for e, t in ref_edges.items():
        if e not in edges and (e[1], e[0]) not in edges:
            metric = _metric(t, None)
            metrics[metric] += 1
            if identify_edges is True and metric_edges is not None:
                metric_edges[metric].add(e)

    max_edges = int(0.5 * len(reference.nodes) * (len(reference.nodes) - 1))
    metrics.update({"missing_matched": max_edges - sum(metrics.values())})

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
    if tp + metrics["missing_matched"] + shd != max_edges:
        raise RuntimeError("SHD sanity check: {}".format(metrics))

    # Create base metrics dict with correct types
    result_metrics: Dict[str, Union[int, float, None]] = dict(metrics)
    result_metrics.update({"shd": shd, "p": p, "r": r, "f1": f1})

    # add in Bayesys metrics and edge details if required

    if bayesys is not None:
        result_metrics.update(
            bayesys_metrics(
                result_metrics, max_edges, len(reference.edges), bayesys
            )
        )
    if identify_edges and metric_edges is not None:
        # Add edges separately to avoid type conflicts
        final_result: Dict[str, Any] = dict(result_metrics)
        final_result["edges"] = metric_edges
        return final_result

    return result_metrics


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
        ref_prob = ref_dist[key] if ref_dist[key] > 0 else 1e-16
        result += prob * ln(prob / ref_prob)

    return result


def bayesys_metrics(
    metrics: Dict[str, Union[int, float, None]],
    max_edges: int,
    num_ref_edges: int,
    version: str,
) -> Dict[str, float]:

    # Compute true/false postive/negatives
    # If reference has an edge but graph has arc this is considered a match
    # Bayesys comparison introduces concept of a "half-match" when graph has
    # an edge, or an oppositely orientated arc compared to reference.
    # Note edge_matched is not counted as TP giving incorrectly high shd-b for
    # CPDAG comparisons
    # This implementation has extra protection against divide by zero errors

    # Ensure we get numeric values from metrics (they should all be int/float)
    arc_matched = int(metrics["arc_matched"] or 0)
    arc_not_edge = int(metrics["arc_not_edge"] or 0)
    edge_matched = int(metrics["edge_matched"] or 0)
    arc_reversed = int(metrics["arc_reversed"] or 0)
    edge_not_arc = int(metrics["edge_not_arc"] or 0)
    arc_extra = int(metrics["arc_extra"] or 0)
    edge_extra = int(metrics["edge_extra"] or 0)

    TP = float(arc_matched + arc_not_edge + edge_matched)
    TP2 = float(arc_reversed + edge_not_arc)
    FP = float(arc_extra + edge_extra)
    TN = max_edges - num_ref_edges - FP
    FN = num_ref_edges - TP - 0.5 * TP2

    # Precision, recall and F1 but allowing for half-matches.

    precision = (
        1.0
        if TP + TP2 + FP == 0
        else (
            (TP + 0.5 * TP2) / (TP + TP2 + FP)
            if version != "v1.3"
            else (TP + 0.5 * TP2) / (TP + 0.5 * TP2 + FP)
        )
    )  # bug pre Bayesys v1.5
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
    DDM = (TP + 0.5 * TP2 - FN - FP) / num_ref_edges
    positive_worth = 1.0 / num_ref_edges
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
