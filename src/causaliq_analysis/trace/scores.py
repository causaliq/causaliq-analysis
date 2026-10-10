"""Score recalculation for series of structure-learning traces.

These helpers implement ``Trace.update_scores``. They live at module level so
the method stays thin; the ``Trace`` class is passed in as ``trace_cls`` so
this module does not import it (keeping the package import graph acyclic).
"""

from typing import Any, Dict, List, Optional, Tuple

from causaliq_core.graph import DAG, extend_pdag
from causaliq_data import NumPy
from causaliq_data.score import dag_score

__all__ = ["update_scores"]


def update_scores(
    trace_cls: Any,
    series: str,
    networks: List[str],
    score: str,
    root_dir: str,
    save: bool = False,
    test: bool = False,
) -> Dict[Tuple[str, str], Tuple[Optional[float], float]]:
    """Update score in all traces of a series (see Trace.update_scores).

    Args:
        trace_cls: The ``Trace`` class used to read traces.
        series (str): Series to update traces for.
        networks (list): List of networks to update.
        score (str): Score to update e.g. 'bic', 'loglik'.
        root_dir (str): Root directory holding trace files.
        save (bool, optional): Whether to save updated scores in trace
            file. Defaults to False.
        test (bool, optional): Whether score should be evaluated on test
            data. Defaults to False.

    Returns:
        dict: {(network, id): (initial score, learnt score)}.

    Raises:
        ValueError: If bad arg values.
    """
    _validate_update_scores_args(series, networks, score, root_dir)
    params = {"base": "e", "unistate_ok": True}
    scores: Dict[Tuple[str, str], Tuple[Optional[float], float]] = {}
    for network in networks:
        _update_network_scores(
            trace_cls,
            series,
            network,
            score,
            root_dir,
            save,
            test,
            params,
            scores,
        )
    return scores


def _validate_update_scores_args(
    series: str, networks: List[str], score: str, root_dir: str
) -> None:
    """Validate the arguments of Trace.update_scores()."""
    if (
        not isinstance(series, str)
        or not isinstance(networks, list)
        or not isinstance(score, str)
        or not isinstance(root_dir, str)
    ):
        raise TypeError("Trace.ipdate_scores() bad arg types")


def _read_network_data(
    root_dir: str, network: str, test: bool
) -> Tuple[Any, str]:
    """Read the dataset for a network, returning it and the score suffix."""
    dstype = "continuous" if network.endswith("_c") else "categorical"
    gauss = "" if dstype == "categorical" else "-g"
    N_reqd = 1000000 if test is True else None
    data = NumPy.read(
        root_dir + "/datasets/" + network + ".data.gz",
        dstype=dstype,  # type: ignore[arg-type]
        N=N_reqd,
    )
    return data, gauss


def _initial_scores(
    data: Any,
    Ns: set,
    N_data: int,
    score: str,
    gauss: str,
    params: Dict[str, Any],
) -> Dict[int, float]:
    """Score the initial graph at each sample size."""
    initial = DAG(list(data.get_order()), [])
    initial_score: Dict[int, float] = {}
    for N in Ns:
        if N > N_data:
            continue
        data.set_N(N)
        initial_score[N] = (
            dag_score(initial, data, score + gauss, params)[score + gauss]
        ).sum()
    return initial_score


def _prepare_data(data: Any, N: int, test: bool, trace_id: str) -> None:
    """Select the trace sample (optionally a test subsample) in the data."""
    if test is True:
        seed = int(trace_id.split("_")[1]) if "_" in trace_id else 0
        print(f"Seed is {seed}")
        data.set_N(N, seed=seed, random_selection=True)
    if N != data.N:
        data.set_N(N)


def _learnt_score(
    trace: Any,
    data: Any,
    score: str,
    gauss: str,
    params: Dict[str, Any],
    trace_id: str,
) -> Any:
    """Score the learnt graph, returning NaN when the PDAG cannot extend."""
    try:
        learnt = extend_pdag(trace.result)
        return (
            dag_score(learnt, data, score + gauss, params)[score + gauss]
        ).sum()
    except ValueError:
        print("\n*** Cannot extend PDAG for {}\n".format(trace_id))
        return float("nan")


def _record_score(
    trace: Any,
    network: str,
    trace_id: str,
    score: str,
    gauss: str,
    learnt_score: float,
    initial_score: float,
    test: bool,
    scores: Dict[Tuple[str, str], Tuple[Optional[float], float]],
) -> None:
    """Record a traced score, printing the before/after value."""
    if score == "loglik":
        print(
            "{} {}: {}{} score --> {:.3e}".format(
                network,
                trace_id,
                ("test " if test is True else "train "),
                score,
                learnt_score,
            )
        )
        trace.context["lltest" if test is True else "loglik"] = learnt_score
        scores[(network, trace_id)] = (None, learnt_score)
        return
    print(
        "{} {}: {} score {:.3e} --> {:.3e}".format(
            network, trace_id, score, initial_score, learnt_score
        )
    )
    trace.trace["delta/score"][0] = initial_score
    trace.trace["delta/score"][-1] = learnt_score
    scores[(network, trace_id)] = (initial_score, learnt_score)


def _update_trace_score(
    trace: Any,
    network: str,
    trace_id: str,
    score: str,
    gauss: str,
    params: Dict[str, Any],
    initial_score: Dict[int, float],
    test: bool,
    save: bool,
    root_dir: str,
    data: Any,
    N_data: int,
    scores: Dict[Tuple[str, str], Tuple[Optional[float], float]],
) -> None:
    """Update and optionally save the score of a single trace."""
    if (
        score != "loglik"
        and "score" in trace.context["params"]
        and score + gauss != trace.context["params"]["score"]
    ):
        raise ValueError("update_trace_scores bad arg values")
    N = int(trace_id.split("_")[0][1:])
    if N > N_data:
        return
    _prepare_data(data, N, test, trace_id)
    learnt_score = _learnt_score(trace, data, score, gauss, params, trace_id)
    _record_score(
        trace,
        network,
        trace_id,
        score,
        gauss,
        learnt_score,
        initial_score.get(N, 0.0),
        test,
        scores,
    )
    if save is True:
        trace.save(root_dir)


def _update_network_scores(
    trace_cls: Any,
    series: str,
    network: str,
    score: str,
    root_dir: str,
    save: bool,
    test: bool,
    params: Dict[str, Any],
    scores: Dict[Tuple[str, str], Tuple[Optional[float], float]],
) -> None:
    """Update the scores of all traces for one network."""
    print("\nReading {} traces for {} ...".format(series, network))
    traces = trace_cls.read(series + "/" + network, root_dir)
    if traces is None:
        print(" ... no traces found for {}".format(network))
        return
    Ns = {int(id.split("_")[0][1:]) for id in traces}
    print(Ns)
    data, gauss = _read_network_data(root_dir, network, test)
    N_data = data.N
    initial_score: Dict[int, float] = {}
    if score != "loglik":
        initial_score = _initial_scores(data, Ns, N_data, score, gauss, params)
    for trace_id, trace in traces.items():
        _update_trace_score(
            trace,
            network,
            trace_id,
            score,
            gauss,
            params,
            initial_score,
            test,
            save,
            root_dir,
            data,
            N_data,
            scores,
        )
