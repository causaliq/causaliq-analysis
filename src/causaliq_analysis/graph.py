# Enumerations describing changes made to a graph
# Will be migrated to causaliq_core.graph

from enum import Enum
from typing import TYPE_CHECKING, Dict, Tuple

from causaliq_core.graph import dag_to_pdag
from causaliq_core.utils import EnumWithAttrs
from pandas import DataFrame

if TYPE_CHECKING:
    from causaliq_analysis.trace import Trace  # pragma: no cover


class GraphActionDetail(Enum):  # details that can be provided on a Trace entry
    ARC = ("arc", tuple)  # Arc that was changed
    DELTA = ("delta/score", float)  # Delta as result of arc changed
    ACTIVITY_2 = ("activity_2", str)  # Arc change with second highest delta
    ARC_2 = ("arc_2", tuple)  # Arc changed in second highest delta
    DELTA_2 = ("delta_2", float)  # second highest delta
    MIN_N = ("min_N", float)  # minimum count in contingency tables' cells
    MEAN_N = ("mean_N", float)  # mean count in contingency tables' cells
    MAX_N = ("max_N", float)  # max count in contingency tables' cells
    LT5 = ("lt5", float)  # number of cells with count <5 in contingency tables
    FPA = ("free_params", float)  # number of free params in contingency tables
    KNOWLEDGE = ("knowledge", tuple)  # Knowledge used in iteration
    BLOCKED = ("blocked", list)  # list of blocked changes


# for PC delete in p-value or use score? some of MIN_N to FPA still relevant?
# need new field for conditioning set
# could arc and arc2 to defined v-structure


class GraphAction(EnumWithAttrs):
    """
    Defines set of Activities than can recorded in trace

    :ivar str value: short string code for activity
    :ivar str label: human-readable label for activity
    :ivar set mandatory: mandatory items for activity
    :ivar int priority: priority order for this activity
    """

    INIT = "init", "initialise", {GraphActionDetail.DELTA}, 0
    ADD = "add", "add arc", {GraphActionDetail.ARC, GraphActionDetail.DELTA}, 3
    DEL = (
        "delete",
        "delete arc",
        {GraphActionDetail.ARC, GraphActionDetail.DELTA},
        2,
    )
    REV = (
        "reverse",
        "reverse arc",
        {GraphActionDetail.ARC, GraphActionDetail.DELTA},
        1,
    )
    STOP = "stop", "stop search", {GraphActionDetail.DELTA}, 4
    PAUSE = "pause", "pause search", {GraphActionDetail.DELTA}, 6
    NONE = (
        "none",
        "no change",
        {GraphActionDetail.ARC, GraphActionDetail.DELTA},
        5,
    )

    # ignore the first param since it's already set by __new__
    def __init__(self, _: str, label: str, mandatory: set, priority: int):
        self._label_ = label
        self._mandatory_ = mandatory
        self._priority_ = priority

    # this makes sure that mandatory is read-only
    @property
    def mandatory(self) -> set:
        return self._mandatory_.copy()

    # this makes sure that priority is read-only
    @property
    def priority(self) -> int:
        return self._priority_


# for PC delete used for removing arc, v-struct needed for v-struct,
# and orientate for arc orientation


def _validate_average_params(
    sample_size: int,
    pdag: bool,
    seeds: Tuple[int, ...],
) -> None:
    """
    Common validation logic for graph averaging parameters.

    Args:
        sample_size (int): Sample size to filter traces
        pdag (bool): Whether to convert to PDAGs
        seeds (Tuple[int, ...]): Seeds to filter by

    Raises:
        TypeError: If arguments have invalid types.
        ValueError: If arguments have invalid values.
    """
    if not isinstance(sample_size, int):
        raise TypeError("sample_size must be an integer")
    if sample_size <= 0:
        raise ValueError("sample_size must be positive")
    if not isinstance(pdag, bool):
        raise TypeError("pdag must be a boolean")
    if not isinstance(seeds, tuple):
        raise TypeError("seeds must be a tuple")
    if not all(isinstance(s, int) for s in seeds):
        raise TypeError("all seeds must be integers")
    if any(s < 0 for s in seeds):
        raise ValueError("all seeds must be non-negative")


def average(
    traces: Dict[str, "Trace"],
    sample_size: int,
    pdag: bool = False,
    seeds: Tuple[int, ...] = (),
) -> DataFrame:
    """
    Produce table of edge probabilities by averaging multiple graphs.

    Args:
        traces (Dict[str, Trace]): Dictionary of traces with keys containing
                                   sample size and seed information
        sample_size (int): average graphs learnt from this sample size
        pdag (bool): whether learned graphs are converted to PDAGs
        seeds (Tuple[int, ...]): use experiments with this range of seeds.
                                 Empty tuple means use all seeds.

    Returns:
        DataFrame: of node pairs and respective probabilities for each
                   directed edges, undirected edge, and no edge

    Raises:
        TypeError: If arguments have invalid types.
        ValueError: If no matching traces found or graphs have different nodes.
    """
    from causaliq_analysis.trace import Trace

    # Validate input types
    if not isinstance(traces, dict):
        raise TypeError("traces must be a dictionary")
    if not all(isinstance(t, Trace) for t in traces.values()):
        raise TypeError("all values in traces must be Trace objects")

    # Use common validation
    _validate_average_params(sample_size, pdag, seeds)

    # Filter traces based on sample_size and seeds
    matching_traces = {}
    for trace_id, trace in traces.items():
        # Check if trace has the right sample size
        if "N" not in trace.context or trace.context["N"] != sample_size:
            continue

        # Extract seed from trace ID (assuming format like "network_N1000_42")
        # If seeds tuple is empty, include all traces with matching sample size
        if len(seeds) == 0:
            matching_traces[trace_id] = trace
        else:
            # Try to extract seed from trace_id
            parts = trace_id.split("_")
            for part in parts:
                try:
                    seed = int(part)
                    if seed in seeds:
                        matching_traces[trace_id] = trace
                        break
                except ValueError:
                    continue

    if not matching_traces:
        raise ValueError(
            f"no traces found for sample_size={sample_size} "
            f"and seeds={seeds}"
        )

    # Get all nodes from the first graph
    first_trace = next(iter(matching_traces.values()))
    if first_trace.result is None:
        raise ValueError("trace has no result graph")

    # Convert to PDAG if requested
    if pdag:
        # Convert DAG to PDAG (may introduce undirected edges)
        reference_graph = dag_to_pdag(first_trace.result)  # type: ignore
    else:
        reference_graph = first_trace.result  # type: ignore[assignment]

    nodes = sorted(reference_graph.nodes)
    n_graphs = len(matching_traces)

    # Validate all graphs have the same nodes
    for trace_id, trace in matching_traces.items():
        if trace.result is None:
            raise ValueError(f"trace {trace_id} has no result graph")
        if pdag:
            # Convert DAG to PDAG (may introduce undirected edges)
            graph = dag_to_pdag(trace.result)  # type: ignore[arg-type]
        else:
            graph = trace.result  # type: ignore[assignment]
        if sorted(graph.nodes) != nodes:
            raise ValueError(
                f"trace {trace_id} has different nodes: "
                f"{sorted(graph.nodes)} vs {nodes}"
            )

    # Build edge probability table
    # For each pair of nodes, count the different edge types
    edge_counts: Dict[Tuple[str, str], Dict[str, int]] = {}

    for i, node_a in enumerate(nodes):
        for j, node_b in enumerate(nodes):
            if i >= j:  # Skip diagonal and lower triangle
                continue

            pair = (node_a, node_b)
            edge_counts[pair] = {
                "A->B": 0,  # directed A to B
                "B->A": 0,  # directed B to A
                "A-B": 0,  # undirected
                "none": 0,  # no edge
            }

    # Count edges across all matching traces
    for trace in matching_traces.values():
        if pdag:
            # Convert DAG to PDAG (may introduce undirected edges)
            graph = dag_to_pdag(trace.result)  # type: ignore[arg-type]
        else:
            graph = trace.result  # type: ignore[assignment]

        for i, node_a in enumerate(nodes):
            for j, node_b in enumerate(nodes):
                if i >= j:
                    continue

                pair = (node_a, node_b)

                # Check what edge exists between these nodes
                # For undirected edges, they are canonicalized with
                # alphabetically first node first
                canonical_pair = (min(node_a, node_b), max(node_a, node_b))

                # Check edge types
                edge_b_to_a = graph.edges.get((node_b, node_a))
                canonical_edge = graph.edges.get(canonical_pair)

                if canonical_edge is not None:
                    # Check if it's an undirected edge
                    from causaliq_core.graph import EdgeType

                    if canonical_edge == EdgeType.UNDIRECTED:
                        edge_counts[pair]["A-B"] += 1
                    elif canonical_pair == (node_a, node_b):
                        # Directed A to B (canonical form matches our pair)
                        edge_counts[pair]["A->B"] += 1

                elif edge_b_to_a is not None:
                    # Direct edge from B to A
                    edge_counts[pair]["B->A"] += 1
                else:
                    # No edge
                    edge_counts[pair]["none"] += 1

    # Convert counts to probabilities and create DataFrame
    rows = []
    for (node_a, node_b), counts in edge_counts.items():
        row = {
            "node_a": node_a,
            "node_b": node_b,
            "p_a_to_b": counts["A->B"] / n_graphs,
            "p_b_to_a": counts["B->A"] / n_graphs,
            "p_undirected": counts["A-B"] / n_graphs,
            "p_no_edge": counts["none"] / n_graphs,
        }
        rows.append(row)

    df = DataFrame(rows)
    return df
