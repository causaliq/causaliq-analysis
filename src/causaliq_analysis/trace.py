#   Implements code for detailed tracing of structure learning

import gzip
import pickle
from enum import Enum
from gzip import BadGzipFile
from os import makedirs
from re import compile
from time import asctime, localtime, time
from typing import Any, Dict, List, Optional, Tuple, Union, cast

from causaliq_core import SOFTWARE_VERSION
from causaliq_core.graph import DAG, SDG, extend_pdag
from causaliq_core.utils import environment, is_valid_path, values_same
from causaliq_core.utils.random import Randomise
from causaliq_data import NumPy
from causaliq_data.score import dag_score
from compress_pickle import dump  # type: ignore[import-untyped]
from pandas import DataFrame

from causaliq_analysis.graph import GraphAction, GraphActionDetail


class CompatibilityUnpickler(pickle.Unpickler):
    """Custom unpickler that handles module path changes for backward
    compatibility.

    Maps specific classes that have been moved between modules.
    """

    # Mapping of (old_module, class_name) to new_module
    CLASS_MAPPING = {
        ("core.common", "EdgeMark"): "causaliq_core.graph",
        ("core.common", "EdgeType"): "causaliq_core.graph",
        ("core.common", "EnumWithAttrs"): "causaliq_core.utils",
        ("core.common", "rndsf"): "causaliq_core.utils",
        ("core.common", "ln"): "causaliq_core.utils",
        ("core.common", "BAYESYS_VERSIONS"): "causaliq_core.graph",
        ("core.common", "adjmat"): "causaliq_core.graph",
        ("core.common", "environment"): "causaliq_core.utils",
        ("core.common", "RandomIntegers"): "causaliq_core.utils.random",
        ("core.common", "Randomise"): "causaliq_core.utils.random",
        ("core.common", "stable_random"): "causaliq_core.utils.random",
        ("core.common", "init_stable_random"): "causaliq_core.utils.random",
        (
            "core.common",
            "generate_stable_random",
        ): "causaliq_core.utils.random",
        ("core.common", "random_generator"): "causaliq_core.utils.random",
        ("core.common", "set_random_seed"): "causaliq_core.utils.random",
        ("core.timing", "Timing"): "causaliq_core.utils.timing",
        ("core.timing", "MetaTiming"): "causaliq_core.utils.timing",
        ("core.timing", "TimeoutError"): "causaliq_core.utils.timing",
        ("core.timing", "run_with_timeout"): "causaliq_core.utils.timing",
        ("core.timing", "with_timeout"): "causaliq_core.utils.timing",
        # Graph class mappings for the modular refactoring
        ("core.graph", "SDG"): "causaliq_core.graph.sdg",
        ("core.graph", "PDAG"): "causaliq_core.graph.pdag",
        ("core.graph", "DAG"): "causaliq_core.graph.dag",
        ("core.graph", "NotDAGError"): "causaliq_core.graph.dag",
        ("core.graph", "NotPDAGError"): "causaliq_core.graph.pdag",
        # Trace class mapping for the import refactoring
        ("learn.trace", "Trace"): "causaliq_analysis.trace",
        ("learn.trace", "CONTEXT_FIELDS"): "causaliq_analysis.trace",
        ("learn.trace", "DiffType"): "causaliq_analysis.trace",
        # Add more specific class mappings as needed
    }

    class PlaceholderEnum:
        """Placeholder class for missing enum-like classes from legacy modules.

        This handles unpickling of enum instances that reference classes not
        available in the current environment (e.g., learn.hc_worker.Prefer).

        The issue: Legacy pickle files contain references to EnumWithAttrs
        classes from the 'learn' module that don't exist in standalone
        causaliq_analysis. When unpickling, Python tries to instantiate these
        enums with arguments, but a simple empty class fails with
        "takes no arguments" error.

        This placeholder accepts any arguments during construction to allow
        successful unpickling while maintaining compatibility with the
        discovery repo.
        """

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            # Accept any arguments during unpickling to avoid TypeError
            self.args = args
            self.kwargs = kwargs

        def __new__(cls, *args: Any, **kwargs: Any) -> Any:
            # Create instance that can be unpickled successfully
            return object.__new__(cls)

    def find_class(self, module: str, name: str) -> Any:
        """Override find_class to handle module path changes.

        Args:
            module (str): Original module name from pickle.
            name (str): Class name.

        Returns:
            The class object from the new location.
        """
        # Check if this specific class has been moved
        if (module, name) in self.CLASS_MAPPING:
            module = self.CLASS_MAPPING[(module, name)]
            return super().find_class(module, name)

        # Handle missing learn.* classes with safe fallback
        if module.startswith("learn.") and module != "learn.trace":
            try:
                # Try to import the real class first
                # (for discovery repo compatibility)
                return super().find_class(module, name)
            except ModuleNotFoundError:
                # If module doesn't exist, return a placeholder class
                # that can handle enum-like behavior
                return type(name, (self.PlaceholderEnum,), {})

        return super().find_class(module, name)


def load_with_compatibility(
    file_handle: Any, compression: str = "gzip", **kwargs: Any
) -> Any:
    """Load pickled data with module compatibility handling.

    Args:
        file_handle: File handle to read from.
        compression (str): Compression type.

    Returns:
        Unpickled object.
    """
    if compression == "gzip":
        # For gzip compressed files, we need to decompress first
        file_handle.seek(0)
        with gzip.GzipFile(fileobj=file_handle, mode="rb") as gz_file:
            return CompatibilityUnpickler(gz_file).load()
    else:
        # For uncompressed files
        file_handle.seek(0)
        return CompatibilityUnpickler(file_handle).load()


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


class DiffType(Enum):  # different kinds of trace entry difference
    MINOR = "minor"  # difference in secondary score or counts basis
    SCORE = "score"  # difference in score or delta
    MAJOR = "major"  # difference in operation (operation = activity and arc)
    ORDER = "order"  # same operation but at different iteration
    OPPOSITE = "opposite"  # same operation but on opposite orientation arc
    EXTRA = "extra"  # operation in trace but not in reference
    MISSING = "missing"  # operation in reference but not in trace


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

        if not set(context.keys()).issubset(set(CONTEXT_FIELDS.keys())):
            raise ValueError("Trace() invalid context keys")

        if any(
            [
                v is not None
                and not isinstance(v, CONTEXT_FIELDS[k])  # type: ignore
                for k, v in context.items()
            ]
        ):
            raise TypeError("Trace() invalid context value type")
        if (
            "randomise" in context
            and isinstance(context["randomise"], list)
            and not all(
                [isinstance(r, Randomise) for r in context["randomise"]]
            )
        ):
            raise TypeError("Trace() invalid context randomise type")

        if "id" in context and (
            not ID_PATTERN.match(context["id"])
            or ID_ANTIPATTERN1.match(context["id"])
            or ID_ANTIPATTERN2.match(context["id"])
            or ID_ANTIPATTERN3.match(context["id"])
        ):
            raise ValueError("Trace() invalid id")

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

        def _map(
            arc: Optional[Tuple[str, str]],
        ) -> Optional[Tuple[str, str]]:  # maps names in tuple representing arc
            return (
                None
                if arc is None
                else (
                    name_map[arc[0]] if arc[0] in name_map else arc[0],
                    name_map[arc[1]] if arc[1] in name_map else arc[1],
                )
            )

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

        self.trace["arc"] = [_map(a) for a in self.trace["arc"]]
        self.trace["arc_2"] = [_map(a) for a in self.trace["arc_2"]]
        self.trace["knowledge"] = [
            ((k[0], k[1], k[2], _map(k[3])) if k is not None else k)
            for k in self.trace["knowledge"]
        ]
        self.trace["blocked"] = [
            [(e[0], _map(e[1]), e[2], e[3]) for e in b] if b is not None else b
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
        if (
            not isinstance(series, str)
            or not isinstance(networks, list)
            or not isinstance(score, str)
            or not isinstance(root_dir, str)
        ):
            raise TypeError("Trace.ipdate_scores() bad arg types")

        params = {"base": "e", "unistate_ok": True}

        scores: Dict[Tuple[str, str], Tuple[Optional[float], float]] = {}
        for network in networks:

            # read traces for this network

            print("\nReading {} traces for {} ...".format(series, network))
            traces = Trace.read(series + "/" + network, root_dir)
            if traces is None:
                print(" ... no traces found for {}".format(network))
                continue

            # Determine sample sizes used for this network and read in enough
            # data for largest sample size.

            Ns = {int(id.split("_")[0][1:]) for id in traces}
            print(Ns)
            dstype = "continuous" if network.endswith("_c") else "categorical"
            gauss = "" if dstype == "categorical" else "-g"
            N_reqd = 1000000 if test is True else None
            data = NumPy.read(
                root_dir + "/datasets/" + network + ".data.gz",
                dstype=dstype,  # type: ignore
                N=N_reqd,
            )
            N_data = data.N

            # Obtain scores for initial graphs unless doing log likelihood

            if score != "loglik":
                initial = DAG(list(data.get_order()), [])
                initial_score = {}
                for N in Ns:
                    if N > N_data:
                        continue
                    data.set_N(N)
                    initial_score[N] = (
                        dag_score(initial, data, score + gauss, params)[
                            score + gauss
                        ]
                    ).sum()

            # Loop through all traces determining score of learnt graph

            for id, trace in traces.items():

                # unless loglik score arg should match objective score used

                if (
                    score != "loglik"
                    and "score" in trace.context["params"]
                    and score + gauss != trace.context["params"]["score"]
                ):
                    raise ValueError("update_trace_scores bad arg values")

                # set subset of data matching N for this trace

                N = int(id.split("_")[0][1:])
                if N > N_data:
                    continue
                if test is True:
                    seed = int(id.split("_")[1]) if "_" in id else 0
                    print(f"Seed is {seed}")
                    data.set_N(N, seed=seed, random_selection=True)
                if N != data.N:
                    data.set_N(N)
                learnt = trace.result

                # ensure learnt CPDAG turned to DAG then score it

                try:
                    learnt = extend_pdag(learnt)  # type: ignore
                    learnt_score = (
                        dag_score(learnt, data, score + gauss, params)[
                            score + gauss
                        ]
                    ).sum()
                except ValueError:
                    print("\n*** Cannot extend PDAG for {}\n".format(id))
                    learnt_score = float("nan")

                # loglik score stored in trace context, but for other scores
                # initial and learnt score stored in trace entries

                if score == "loglik":
                    print(
                        "{} {}: {}{} score --> {:.3e}".format(
                            network,
                            id,
                            ("test " if test is True else "train "),
                            score,
                            learnt_score,
                        )
                    )
                    trace.context["lltest" if test is True else "loglik"] = (
                        learnt_score
                    )
                    scores[(network, id)] = (None, learnt_score)

                else:
                    print(
                        "{} {}: {} score {:.3e} --> {:.3e}".format(
                            network, id, score, initial_score[N], learnt_score
                        )
                    )
                    trace.trace["delta/score"][0] = initial_score[N]
                    trace.trace["delta/score"][-1] = learnt_score
                    scores[(network, id)] = (initial_score[N], learnt_score)

                if save is True:
                    trace.save(root_dir)

        return scores

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

        parts = id.split("/")
        if len(parts) < 2:
            raise ValueError("Trace._read_file() invalid id")
        key = parts.pop()
        file_name = parts.pop() + ".pkl.gz"
        path = root_dir + "/" + "/".join(parts)
        # print("Path: {}, file: {}, key: {}".format(path, file_name, key))

        # Try and open pkl file, checking its format

        try:
            with open(path + "/" + file_name, "rb") as fh:
                # Use compatibility loader instead of compress_pickle.load
                traces = load_with_compatibility(fh, compression="gzip")
                if not isinstance(traces, dict) or not all(
                    [isinstance(v, Trace) for v in traces.values()]
                ):
                    raise ValueError()
        except FileNotFoundError:
            traces = {}
        except (pickle.UnpicklingError, EOFError, ValueError, BadGzipFile):
            raise ValueError("Trace._read_file() bad .pkl.gz file")

        return (path, file_name, key, traces)

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
        return (
            (
                not strict
                and not values_same(s1, s2, sf=4)
                and (s1 > s2 + 0.5 or s1 < s2 - 0.5)
            )
            or (
                strict
                and not values_same(s1, s2, sf=10)
                and (s1 > s2 + 1.0e-8 or s1 < s2 - 1.0e-8)
            )
            if (isinstance(s1, float) or isinstance(s2, float))
            else s1 != s2
        )

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

        def _sorted(blocked: List[Any]) -> List[Any]:
            result = [b for b in blocked if b[0] == GraphAction.ADD.value]
            result.extend(
                [b for b in blocked if b[0] == GraphAction.DEL.value]
            )
            result.extend(
                [b for b in blocked if b[0] == GraphAction.REV.value]
            )
            return result

        same = None
        if entry is None and ref is None:
            same = True

        elif entry is None or ref is None or len(entry) != len(ref):
            same = False

        else:
            same = True
            for _entry, _ref in zip(_sorted(entry), _sorted(ref)):
                if (
                    _entry[0] != _ref[0]
                    or _entry[1] != _ref[1]
                    or self._nums_diff(_entry[2], _ref[2], strict)
                    or _entry[3] != _ref[3]
                ):
                    same = False
                    break

        return same

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

        # compare entries arc and activity fields - difference -> MAJOR

        if (
            "arc" in entry and "arc" in ref and entry["arc"] != ref["arc"]
        ) or entry["activity"] != ref["activity"]:
            return DiffType.MAJOR

        # compare delta/score to reqd accuracy - difference -> SCORE

        if self._nums_diff(entry["delta/score"], ref["delta/score"], strict):
            print(
                "Different scores are {} and {}".format(
                    entry["delta/score"], ref["delta/score"]
                )
            )
            return DiffType.SCORE

        # compare other numeric fields - difference -> MINOR

        for key in list(
            set(ref.keys())
            - {"arc", "activity", "delta/score", "blocked", "knowledge"}
        ):
            if self._nums_diff(entry[key], ref[key], strict):
                print(
                    "*** Diff for {}: {}, {}".format(key, entry[key], ref[key])
                )
                return DiffType.MINOR

        # compare blocked fields if reqd - difference -> MINOR

        if (
            "blocked" in entry
            and "blocked" in ref
            and "blocked" not in ignore
            and not self._blocked_same(
                entry["blocked"], ref["blocked"], strict
            )
        ):
            return DiffType.MINOR

        # compare knowledge fields - difference -> MINOR

        if (
            "knowledge" in ref
            and "knowledge" in entry
            and entry["knowledge"] != ref["knowledge"]
        ):
            print(ignore)
            if "act_cache" not in ignore:
                return DiffType.MINOR

            ref_none = ref["knowledge"] is None
            ent_none = entry["knowledge"] is None
            ref_a_c = not ref_none and ref["knowledge"][0] == "act_cache"
            ent_a_c = not ent_none and entry["knowledge"][0] == "act_cache"

            return (
                None
                if (
                    (ref_a_c and ent_none)
                    or (ref_none and ent_a_c)
                    or (ref_a_c and ent_a_c)
                )
                else DiffType.MINOR
            )

        return None

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
        if trace:
            key = (trace["activity"], trace["arc"] if "arc" in trace else None)
            if key not in diffs:
                diffs[key] = ([], [])
            diffs[key][0].append(iter)
        if ref:
            key = (ref["activity"], ref["arc"] if "arc" in ref else None)
            if key not in diffs:
                diffs[key] = ([], [])
            diffs[key][1].append(iter)
        return diffs

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
        extra = (activity, DiffType.EXTRA.value)  # key for extra entry
        missing = (activity, DiffType.MISSING.value)  # key for missing entry

        if extra in diffs and missing in diffs:

            # Merging only possible if there are some extra and some missing
            # activities. Loop over extra activities in trace looking for
            # opposing arc missing from trace

            for arc, iters in diffs[extra].copy().items():
                opp_arc = (arc[1], arc[0])
                if opp_arc in diffs[missing]:

                    # set up key for opposites in diffs and add new entry

                    opposite = (activity, DiffType.OPPOSITE.value)
                    if opposite not in diffs:
                        diffs[opposite] = {}
                    ref_iters = diffs[missing][opp_arc]
                    diffs[opposite].update({arc: [iters[0], ref_iters[1]]})

                    # remove matching entry in extra and missing

                    del diffs[extra][arc]
                    del diffs[missing][opp_arc]
        return diffs

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

        # hc_worker processing changed at v177 so determine if which
        # trace properties/entries have to be ignored.

        ignore = (
            set()
            if (self.context["software_version"] - 176.5)
            * (ref.context["software_version"] - 176.5)
            > 0.0
            else {"blocked", "act_cache"}
        )

        #   Will only compare columns which have some values in them in BOTH
        #   trace and reference, and will not compare time column

        ref_df = ref.get()
        trace_df = self.get()
        compare: List[str] = list(
            set(trace_df.columns[trace_df.notnull().any()]).intersection(
                set(ref_df.columns[ref_df.notnull().any()])
            )
            - {"time"}
            | {"arc", "activity", "delta/score"}
        )

        # DataFrame subset .to_dict() - pandas stubs differ across versions
        # Mypy on Python 3.11 sees df[list] as Series, ignore and cast
        ref_df_subset = ref_df[compare]
        ref_dict = ref_df_subset.to_dict(  # type: ignore[call-overload,unused-ignore]  # noqa: E501
            orient="records"
        )
        ref_records = cast(List[Dict[str, Any]], ref_dict)

        trace_df_subset = trace_df[compare]
        trace_dict = trace_df_subset.to_dict(  # type: ignore[call-overload,unused-ignore]  # noqa: E501
            orient="records"
        )
        trace_records = cast(List[Dict[str, Any]], trace_dict)

        if (
            len(ref_records) < 2
            or len(trace_records) < 2
            or "activity" not in ref_records[0]
            or "delta/score" not in ref_records[0]
            or trace_records[0]["activity"] != "init"
            or ref_records[0]["activity"] != "init"
            or trace_records[-1]["activity"] != "stop"
            or ref_records[-1]["activity"] != "stop"
        ):
            raise ValueError("Trace.diffs_from() bad trace format")

        #   Loop through trace entries detecting differences with ref

        _diffs: Dict[Any, Any] = {}
        minor = []
        for iter in range(0, len(trace_records)):
            if iter >= len(ref_records):
                # print(iter, trace_records[iter], None)
                _diffs = self._update_diffs(
                    iter, trace_records[iter], None, _diffs
                )
            else:
                diff = self._compare_entry(
                    trace_records[iter], ref_records[iter], strict, ignore
                )
                if diff in [DiffType.MAJOR, DiffType.SCORE]:
                    # print(iter, trace_records[iter], ref_records[iter])
                    _diffs = self._update_diffs(
                        iter, trace_records[iter], ref_records[iter], _diffs
                    )
                elif diff is not None:
                    minor.append(iter)

        #   Loop through any extra entries in ref

        for iter in range(len(trace_records), len(ref_records)):
            # print(iter, None, ref_records[iter])
            _diffs = self._update_diffs(iter, None, ref_records[iter], _diffs)

        # if no major, score or minor errors, traces are identical

        if not len(_diffs) and not len(minor):
            return None

        # Reorganise differences to be keyed by (activity, difference type)

        diffs: Dict[Any, Any] = {}
        for diff, iters in _diffs.items():
            if len(iters[0]) > len(iters[1]):
                type = DiffType.EXTRA
            elif len(iters[0]) < len(iters[1]):
                type = DiffType.MISSING
            elif iters[0] != iters[1]:
                type = DiffType.ORDER
            else:
                type = DiffType.SCORE
            key = (diff[0], type.value)
            if key not in diffs:
                diffs[key] = {}
            diffs[key].update(
                {
                    diff[1]: (
                        iters[0][0] if iters[0] else None,
                        iters[1][0] if iters[1] else None,
                    )
                }
            )
            # print(type, diff, iters)

        # Merge activities on opposing arcs

        for activity in ["add", "delete", "reverse"]:
            diffs = self._merge_opposites(activity, diffs)

        final_score_diff = (
            self._compare_entry(
                trace_records[-1], ref_records[-1], strict, ignore
            )
            == DiffType.SCORE
        )
        summary = self._diffs_summary(
            diffs,
            final_score_diff,
            len(trace_records) - 1,
            len(ref_records) - 1,
        )

        return (diffs, minor, summary)

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
        summary = (
            "Trace has {} initial score".format(
                "different"
                if ("init", DiffType.SCORE.value) in diffs
                else "same"
            )
            + ", {} final score".format(
                "different" if final_score_diff else "same"
            )
            + " in {} versus {} iterations".format(trace_iters, ref_iters)
        )

        for activity in ["add", "delete", "reverse"]:
            for type in ["extra", "missing", "opposite", "score"]:
                key = (activity, type)
                if key in diffs:
                    summary += "\n{} {} {}(s): {}".format(
                        len(diffs[key]), type, activity, diffs[key]
                    )

        return summary

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
