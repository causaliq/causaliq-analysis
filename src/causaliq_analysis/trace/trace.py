#   Implements code for detailed tracing of structure learning

import pickle
from gzip import BadGzipFile
from os import makedirs
from re import compile
from time import asctime, localtime, time
from typing import Any, Dict, List, Optional, Tuple, Union, cast

from causaliq_core import SOFTWARE_VERSION
from causaliq_core.graph import DAG, SDG
from causaliq_core.utils import environment, is_valid_path
from causaliq_core.utils.random import Randomise
from compress_pickle import dump  # type: ignore[import-untyped]
from pandas import DataFrame

from causaliq_analysis.graph import GraphAction, GraphActionDetail
from causaliq_analysis.trace.compatibility import load_with_compatibility
from causaliq_analysis.trace.diffs import (
    DiffType,
    blocked_same,
    build_diffs,
    compare_entry,
    diffs_summary,
    merge_opposites,
    nums_diff,
    update_diffs,
)
from causaliq_analysis.trace.scores import update_scores as _update_scores

__all__ = ["CONTEXT_FIELDS", "Trace"]


CONTEXT_FIELDS = {
    "id": str,
    "algorithm": str,
    "params": dict,
    "in": str,
    "N": int,
    "dataset": bool,
    "external": str,
    "knowledge": str,
    "score": float,
    "randomise": (Randomise, list),
    "var_order": list,
    "initial": DAG,
    "pretime": float,
}

ID_PATTERN = compile(r"^[A-Za-z0-9\/\ \_\.\-]+$")
ID_ANTIPATTERN1 = compile(r".*[\/|\ |\_|\.|\-][\/|\ |\_|\.|\-].*")
ID_ANTIPATTERN2 = compile(r"^[\/|\ |\_|\.|\-].*")
ID_ANTIPATTERN3 = compile(r".*[\/|\ |\_|\.|\-]$")


# for PC delete used for removing arc, v-struct needed for v-struct,
# and orientate for arc orientation


class Trace:
    """Class encapsulating detailed structure learning trace.

    Args:
        context (dict, optional): Description of learning context.

    Attributes:
        context (dict): Learning context.
        trace (list): Iteration by iteration structure learning trace.
        start (float): Time at which tracing started.
        result (SDG): Learnt graph.
        treestats (TreeStats): Statistics from a tree search.

    Raises:
        TypeError: If arguments have invalid types.
        ValueError: If invalid context fields provided.
    """

    def __init__(self, context: Optional[Dict[str, Any]] = None) -> None:

        if context is not None and not isinstance(context, dict):
            raise TypeError("Trace() bad arg type")

        if context is None:
            context = {}

        _validate_context(context)

        context.update(environment())
        context.update({"software_version": SOFTWARE_VERSION})

        self.context = context
        self.trace: Dict[str, List[Any]] = {"time": [], "activity": []}
        self.trace.update({d.value[0]: [] for d in GraphActionDetail})
        self.start = time()
        self.result: Optional[SDG] = None
        self.treestats = None

    def rename(self, name_map: Dict[str, str]) -> None:
        """Rename nodes in trace in place according to name map.

        Args:
            name_map (dict): Name mapping {name: new name}.

        Raises:
            TypeError: If bad arg type.
        """
        if not isinstance(name_map, dict) or not all(
            [
                isinstance(k, str) and isinstance(v, str)
                for k, v in name_map.items()
            ]
        ):
            raise TypeError("Trace.rename() bad arg types")

        # Rename nodes in the result graph if present

        if self.result is not None:
            self.result.rename(name_map)

        # modify node names for those trace elements which contain arcs

        self.trace["arc"] = [_map_arc(a, name_map) for a in self.trace["arc"]]
        self.trace["arc_2"] = [
            _map_arc(a, name_map) for a in self.trace["arc_2"]
        ]
        self.trace["knowledge"] = [
            (
                (k[0], k[1], k[2], _map_arc(k[3], name_map))
                if k is not None
                else k
            )
            for k in self.trace["knowledge"]
        ]
        self.trace["blocked"] = [
            (
                [(e[0], _map_arc(e[1], name_map), e[2], e[3]) for e in b]
                if b is not None
                else b
            )
            for b in self.trace["blocked"]
        ]

    @classmethod
    def read(
        self, partial_id: str, root_dir: str
    ) -> Optional[Dict[str, "Trace"]]:
        """Read set of Traces matching partial_id from serialised file.

        Args:
            partial_id (str): Partial_id of Trace.
            root_dir (str): Root directory holding trace files.

        Returns:
            dict or None: {key: Trace} of traces matching partial id.

        Raises:
            TypeError: If arguments are not strings.
            FileNotFoundError: If root_dir doesn't exist.
            ValueError: If partial_id is entry or serialised file is
                not a dictionary of traces.
        """
        if not len(partial_id):
            raise ValueError("Trace.read() empty partial id")

        _, _, _, traces = Trace._read_file(partial_id + "/*", root_dir)

        traces = {id: t._upgrade() for id, t in traces.items()}

        return traces if traces != {} else None

    def add(
        self, activity: GraphAction, details: Dict[GraphActionDetail, Any]
    ) -> "Trace":
        """Add an entry to the structure learning trace.

        Args:
            activity (GraphAction): Action e.g. initialisation, add arc.
            details (dict): Supplementary details relevant to activity.

        Returns:
            Trace: Returns trace after entry added.

        Raises:
            TypeError: If arguments have invalid types.
        """
        if (
            not isinstance(activity, GraphAction)
            or not isinstance(details, dict)
            or not len(details)
            or not all(
                isinstance(k, GraphActionDetail) for k in details.keys()
            )
            or not all(
                [
                    isinstance(v, k.value[1]) or v is None
                    for k, v in details.items()
                ]
            )
        ):

            raise TypeError("Trace.add() bad arg type")

        if not (activity.mandatory).issubset(set(details.keys())):
            raise ValueError("Trace.add() mandatory details not provided")

        self.trace["activity"].append(activity.value)
        self.trace["time"].append(time() - self.start)
        for d in GraphActionDetail:
            self.trace[d.value[0]].append(details[d] if d in details else None)
        return self

    @classmethod
    def update_scores(
        self,
        series: str,
        networks: List[str],
        score: str,
        root_dir: str,
        save: bool = False,
        test: bool = False,
    ) -> Dict[Tuple[str, str], Tuple[Optional[float], float]]:
        """Update score in all traces of a series.

        Args:
            series (str): Series to update traces for.
            networks (list): List of networks to update.
            score (str): Score to update e.g. 'bic', 'loglik'.
            root_dir (str): Root directory holding trace files.
            save (bool, optional): Whether to save updated scores in trace
                file. Defaults to False.
            test (bool, optional): Whether score should be evaluated on test
                data. Defaults to False.

        Raises:
            ValueError: If bad arg values.
        """
        return _update_scores(
            Trace, series, networks, score, root_dir, save, test
        )

    def _upgrade(self) -> "Trace":
        """Upgrade earlier versions of Trace to latest version.

        This method:
         - Makes sure knowledge properties are included
         - Makes sure blocked properties are included
         - Ensures randomise in context returned as a list
        """
        if "knowledge" not in self.trace:
            self.trace.update({"knowledge": [None] * len(self.trace["time"])})
        if "blocked" not in self.trace:
            self.trace.update({"blocked": [None] * len(self.trace["time"])})
        if "randomise" in self.context and isinstance(
            self.context["randomise"], Randomise
        ):
            self.context["randomise"] = [self.context["randomise"]]
        return self

    def get(self) -> DataFrame:
        """Return the trace information.

        Returns:
            DataFrame: Trace as Pandas data frame.
        """
        return DataFrame(self.trace)

    def set_result(self, result: SDG) -> "Trace":
        """Set the result of the learning GraphAction.

        Args:
            result (SDG): Graph result from learning activity.

        Returns:
            Trace: Current Trace to support chaining.

        Raises:
            TypeError: If result argument is not a SDG.
        """
        if not isinstance(result, SDG):
            raise TypeError("Trace.set_result() bad arg type")

        self.result = result
        return self

    def set_treestats(self, treestats: Any) -> "Trace":
        """Set the statistics of a tree learning GraphAction.

        Args:
            treestats (TreeStats): Statistics from tree learning activity.

        Returns:
            Trace: Current Trace to support chaining.

        Raises:
            TypeError: If treestats argument is incorrect type.
        """
        if type(treestats).__name__ != "TreeStats":
            raise TypeError("Trace.set_treestats() bad arg type")

        self.treestats = treestats
        return self

    @classmethod
    def _read_file(
        self, id: str, root_dir: str
    ) -> Tuple[str, str, str, Dict[str, "Trace"]]:
        """Read a composite trace file.

        Args:
            id (str): Trace id.
            root_dir (str): Root directory for trace files.

        Returns:
            tuple: (path of pickle file, pickle file name,
                key for entry, current traces in pickle file).

        Raises:
            TypeError: If bad argument types.
            ValueError: If pkl file has bad format.
            FileNotFoundError: If root_dir does not exist.
        """
        if not isinstance(id, str) or not isinstance(root_dir, str):
            raise TypeError("Trace._open() bad arg type")

        is_valid_path(root_dir, False)  # raises FileNotFoundError if invalid

        path, file_name, key = _trace_file_parts(id, root_dir)

        traces = _load_traces(path, file_name)
        if traces is None:
            traces = {}
        elif not isinstance(traces, dict) or not all(
            isinstance(v, Trace) for v in traces.values()
        ):
            raise ValueError("Trace._read_file() bad .pkl.gz file")

        return (path, file_name, key, cast(Dict[str, "Trace"], traces))

    def save(self, root_dir: str) -> None:
        """Save the trace to a composite serialised (pickle) file.

        Args:
            root_dir (str): Root directory under which pickle files saved.

        Raises:
            TypeError: If bad argument types.
            ValueError: If no id defined for trace.
            FileNotFoundError: If root_dir does not exist.
        """
        if "id" not in self.context:
            raise ValueError("Trace.save() called with undefined id")

        path, file_name, key, traces = self._read_file(
            self.context["id"], root_dir
        )

        traces.update({key: self})

        try:
            is_valid_path(path, False)
        except FileNotFoundError:
            makedirs(path, exist_ok=True)

        with open(path + "/" + file_name, "wb") as file:
            dump(traces, file, compression="gzip", set_default_extension=False)

    @classmethod
    def _nums_diff(
        self, s1: Union[int, float], s2: Union[int, float], strict: bool
    ) -> bool:
        """Determine if two numeric values are similar or the same.

        If strict is False, values are similar. If strict is True,
        values are exactly the same to 10 d.p.

        Args:
            s1 (int or float): First numeric value.
            s2 (int or float): Second numeric value.
            strict (bool): Exact or less strict comparison.

        Returns:
            bool: True if (approximately) the same.
        """
        return nums_diff(s1, s2, strict)

    @classmethod
    def _blocked_same(
        self,
        entry: Optional[List[Any]],
        ref: Optional[List[Any]],
        strict: bool,
    ) -> bool:
        """Compare the blocked field from two trace entries.

        The items in the blocked list are sorted so that adds come first,
        then deletes and finally reverses.

        Args:
            entry (list or None): Blocked entry to be compared against ref.
            ref (list or None): Reference blocked field.
            strict (bool): Whether floats are tested to be strictly the
                same or just reasonably similar.

        Returns:
            bool: True if blocked fields are the same.
        """
        return blocked_same(entry, ref, strict, self._nums_diff)

    @classmethod
    def _compare_entry(
        self,
        entry: Dict[str, Any],
        ref: Dict[str, Any],
        strict: bool,
        ignore: set,
    ) -> Optional[DiffType]:
        """Compare an individual entry from trace with reference trace.

        Args:
            entry (dict): Trace entry to be compared against ref.
            ref (dict): Entry from reference trace.
            strict (bool): Whether floats are tested to be strictly the
                same or just reasonably similar.
            ignore (set): Features to ignore in comparison.

        Returns:
            DiffType or None: Type of difference - major (arc or
                activity), score, other or None.
        """
        return compare_entry(entry, ref, strict, ignore, self._nums_diff)

    @classmethod
    def _update_diffs(
        self,
        iter: int,
        trace: Optional[Dict[str, Any]],
        ref: Optional[Dict[str, Any]],
        diffs: Dict[Any, Any],
    ) -> Dict[Any, Any]:
        """Update dictionary of differences keyed on activity and arc.

        Updates with a difference for a specific iteration.

        Args:
            iter (int): Iteration where this difference occurred.
            trace (dict): Trace entry at this iteration.
            ref (dict): Reference trace entry at this iteration.
            diffs (dict): Dictionary of differences keyed on activity
                and arc.

        Returns:
            dict: Differences dictionary with this difference included.
        """
        return update_diffs(iter, trace, ref, diffs)

    @classmethod
    def _merge_opposites(
        self, activity: str, diffs: Dict[Any, Any]
    ) -> Dict[Any, Any]:
        """Merge activities done on opposing arcs.

        Extra add A --> B and missing add A <-- B is merged into
        opposite add A --> B.

        Args:
            activity (str): Activity being merged - add, delete or reverse.
            diffs (dict): Trace differences before merging.

        Returns:
            dict: Trace differences after merging done.
        """
        return merge_opposites(activity, diffs)

    def diffs_from(
        self, ref: "Trace", strict: bool = True
    ) -> Optional[Tuple[Dict[Any, Any], List[int], str]]:
        """Find differences of trace from reference trace.

        Args:
            ref (Trace): Reference trace to compare this one to.
            strict (bool, optional): Whether floats are tested to be
                strictly the same or just reasonably similar. Defaults
                to True.

        Returns:
            tuple or None: (major differences, minor differences,
                textual summary) or None if identical.

        Raises:
            TypeError: If ref is not of type Trace.
            ValueError: If either trace is invalid.
        """
        if not isinstance(ref, Trace):
            raise TypeError("Trace.diffs_from() bad arg type")
        return build_diffs(self, ref, strict, self._nums_diff)

    @classmethod
    def _diffs_summary(
        self,
        diffs: Dict[Any, Any],
        final_score_diff: bool,
        trace_iters: int,
        ref_iters: int,
    ) -> str:
        """Return a human readable summary of the trace differences.

        Args:
            diffs (dict): Differences keyed by activity and diff type.
            final_score_diff (bool): If difference in final score.
            trace_iters (int): Number of iterations in trace.
            ref_iters (int): Number of iterations in reference trace.

        Returns:
            str: A human readable summary of the differences.
        """
        return diffs_summary(diffs, final_score_diff, trace_iters, ref_iters)

    @classmethod
    def context_string(self, context: Dict[str, Any], start: float) -> str:
        """Return a trace context as a human readable string.

        Args:
            context (dict): Individual context information.
            start: Start time information.

        Returns:
            str: Context information in readable form.
        """
        r_str = (
            " randomising {}\n".format(
                ", ".join([r.value for r in context["randomise"]])
            )
            if "randomise" in context
            and context["randomise"] is not False
            and context["randomise"] is not None
            else "\n"
        )
        return (
            "Trace for {}".format(context["id"])
            + " run at {}\n".format(asctime(localtime(start)))
            + "Learning from {}".format(
                "dataset" if "dataset" in context else "distribution"
            )
            + " with {} rows".format(context["N"])
            + " from {}{}".format(context["in"], r_str)
            + (
                "Variable order is: {}{}\n".format(
                    ", ".join(context["var_order"][:20]),
                    "" if len(context["var_order"]) <= 20 else " ...",
                )
                if "var_order" in context
                else ""
            )
            + "{}{} algorithm".format(
                context["external"] + "-" if "external" in context else "",
                context["algorithm"],
            )
            + (
                " with parameters {}{}{}\n\n".format(
                    context["params"],
                    (
                        "\nKnowledge: " + context["knowledge"]
                        if "knowledge" in context
                        else ""
                    ),
                    (
                        " with reference score {}".format(
                            context["score"] if "score" in context else ""
                        )
                    ),
                )
            )
            + "(Using bnbench v{}".format(context["software_version"])
            + ", Python {}".format(context["python"])
            + " and {}\n".format(context["os"])
            + "on {}".format(context["cpu"])
            + " with {} GB RAM)".format(context["ram"])
        )

    def __eq__(self, other: Any) -> bool:
        """Test if other Trace is identical to this one.

        Args:
            other (Trace): Trace to compare with self.

        Returns:
            bool: True if other is identical to self.
        """
        return isinstance(other, Trace) and other.diffs_from(self) is None

    def __str__(self) -> str:
        """Return details of Trace in human-readable printable format.

        Returns:
            str: Trace in printable form.
        """
        treestats = (
            "\n\nTree stats:\n{}".format(self.treestats)
            if hasattr(self, "treestats") and self.treestats is not None
            else ""
        )

        return (
            self.context_string(self.context, self.start)
            + "\n\n{}".format(self.get())
            + treestats
        )


def _validate_context(context: Dict[str, Any]) -> None:
    """Validate a Trace context against CONTEXT_FIELDS and the id rules."""
    if not set(context.keys()).issubset(set(CONTEXT_FIELDS.keys())):
        raise ValueError("Trace() invalid context keys")
    if any(
        v is not None and not isinstance(v, CONTEXT_FIELDS[k])  # type: ignore
        for k, v in context.items()
    ):
        raise TypeError("Trace() invalid context value type")
    if (
        "randomise" in context
        and isinstance(context["randomise"], list)
        and not all(isinstance(r, Randomise) for r in context["randomise"])
    ):
        raise TypeError("Trace() invalid context randomise type")
    if "id" in context and _bad_id(context["id"]):
        raise ValueError("Trace() invalid id")


def _bad_id(id: str) -> bool:
    """Return True when a trace id fails the naming rules."""
    return bool(
        not ID_PATTERN.match(id)
        or ID_ANTIPATTERN1.match(id)
        or ID_ANTIPATTERN2.match(id)
        or ID_ANTIPATTERN3.match(id)
    )


def _map_arc(
    arc: Optional[Tuple[str, str]], name_map: Dict[str, str]
) -> Optional[Tuple[str, str]]:
    """Map the names in a tuple representing an arc."""
    if arc is None:
        return None
    return (
        name_map[arc[0]] if arc[0] in name_map else arc[0],
        name_map[arc[1]] if arc[1] in name_map else arc[1],
    )


def _trace_file_parts(id: str, root_dir: str) -> Tuple[str, str, str]:
    """Split a trace id into directory path, file name and entry key."""
    parts = id.split("/")
    if len(parts) < 2:
        raise ValueError("Trace._read_file() invalid id")
    key = parts.pop()
    file_name = parts.pop() + ".pkl.gz"
    path = root_dir + "/" + "/".join(parts)
    return path, file_name, key


def _load_traces(path: str, file_name: str) -> Any:
    """Load a trace pickle file, or None when it does not exist."""
    try:
        with open(path + "/" + file_name, "rb") as fh:
            # Use compatibility loader instead of compress_pickle.load
            return load_with_compatibility(fh, compression="gzip")
    except FileNotFoundError:
        return None
    except (pickle.UnpicklingError, EOFError, ValueError, BadGzipFile):
        raise ValueError("Trace._read_file() bad .pkl.gz file")
