"""Detection of differences between structure-learning traces.

``DiffType`` and the comparison helpers live here as module-level functions
so that the ``Trace`` class can stay thin. Numeric comparisons take a
``nums_diff`` callable, so ``Trace`` can pass ``self._nums_diff`` (keeping
the method patchable) without this module importing ``Trace``.
"""

from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union, cast

from causaliq_core.utils import values_same
from pandas import DataFrame

from causaliq_analysis.graph import GraphAction

__all__ = ["DiffType", "build_diffs"]

# Callable performing the trace numeric comparison (see Trace._nums_diff)
NumDiff = Callable[[Union[int, float], Union[int, float], bool], bool]

_ACTIVITIES = ("add", "delete", "reverse")
_DIFF_TYPES = ("extra", "missing", "opposite", "score")


class DiffType(Enum):  # different kinds of trace entry difference
    MINOR = "minor"  # difference in secondary score or counts basis
    SCORE = "score"  # difference in score or delta
    MAJOR = "major"  # difference in operation (operation = activity and arc)
    ORDER = "order"  # same operation but at different iteration
    OPPOSITE = "opposite"  # same operation but on opposite orientation arc
    EXTRA = "extra"  # operation in trace but not in reference
    MISSING = "missing"  # operation in reference but not in trace


def nums_diff(
    s1: Union[int, float], s2: Union[int, float], strict: bool
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


def _sorted_blocked(blocked: List[Any]) -> List[Any]:
    """Order blocked items so adds come first, then deletes and reverses."""
    result = [b for b in blocked if b[0] == GraphAction.ADD.value]
    result.extend([b for b in blocked if b[0] == GraphAction.DEL.value])
    result.extend([b for b in blocked if b[0] == GraphAction.REV.value])
    return result


def blocked_same(
    entry: Optional[List[Any]],
    ref: Optional[List[Any]],
    strict: bool,
    nums_diff_fn: NumDiff,
) -> bool:
    """Compare the blocked field from two trace entries.

    The items in the blocked list are sorted so that adds come first,
    then deletes and finally reverses.

    Args:
        entry (list or None): Blocked entry to be compared against ref.
        ref (list or None): Reference blocked field.
        strict (bool): Whether floats are tested to be strictly the
            same or just reasonably similar.
        nums_diff_fn (callable): Numeric comparison to use.

    Returns:
        bool: True if blocked fields are the same.
    """
    if entry is None and ref is None:
        return True
    if entry is None or ref is None or len(entry) != len(ref):
        return False
    return _blocked_lists_same(entry, ref, strict, nums_diff_fn)


def _blocked_lists_same(
    entry: List[Any],
    ref: List[Any],
    strict: bool,
    nums_diff_fn: NumDiff,
) -> bool:
    """Compare sorted blocked lists item by item."""
    for _entry, _ref in zip(_sorted_blocked(entry), _sorted_blocked(ref)):
        if _blocked_item_differs(_entry, _ref, strict, nums_diff_fn):
            return False
    return True


def _blocked_item_differs(
    entry: Any,
    ref: Any,
    strict: bool,
    nums_diff_fn: NumDiff,
) -> bool:
    """Return True when two blocked items differ."""
    return (
        entry[0] != ref[0]
        or entry[1] != ref[1]
        or nums_diff_fn(entry[2], ref[2], strict)
        or entry[3] != ref[3]
    )


def compare_entry(
    entry: Dict[str, Any],
    ref: Dict[str, Any],
    strict: bool,
    ignore: set,
    nums_diff_fn: NumDiff,
) -> Optional[DiffType]:
    """Compare an individual entry from trace with reference trace.

    Args:
        entry (dict): Trace entry to be compared against ref.
        ref (dict): Entry from reference trace.
        strict (bool): Whether floats are tested to be strictly the
            same or just reasonably similar.
        ignore (set): Features to ignore in comparison.
        nums_diff_fn (callable): Numeric comparison to use.

    Returns:
        DiffType or None: Type of difference - major (arc or
            activity), score, other or None.
    """
    if _arcs_and_activity_differ(entry, ref):
        return DiffType.MAJOR
    if _score_differs(entry, ref, strict, nums_diff_fn):
        return DiffType.SCORE
    if _other_numeric_diff(entry, ref, strict, nums_diff_fn):
        return DiffType.MINOR
    if _blocked_diff(entry, ref, strict, ignore, nums_diff_fn):
        return DiffType.MINOR
    return _knowledge_diff(entry, ref, ignore)


def _arcs_and_activity_differ(
    entry: Dict[str, Any], ref: Dict[str, Any]
) -> bool:
    """Return True when the arc or activity fields differ."""
    arcs_differ = (
        "arc" in entry and "arc" in ref and entry["arc"] != ref["arc"]
    )
    return bool(arcs_differ or entry["activity"] != ref["activity"])


def _score_differs(
    entry: Dict[str, Any],
    ref: Dict[str, Any],
    strict: bool,
    nums_diff_fn: NumDiff,
) -> bool:
    """Return True when delta/score differs, printing the two values."""
    if not nums_diff_fn(entry["delta/score"], ref["delta/score"], strict):
        return False
    print(
        "Different scores are {} and {}".format(
            entry["delta/score"], ref["delta/score"]
        )
    )
    return True


def _other_numeric_diff(
    entry: Dict[str, Any],
    ref: Dict[str, Any],
    strict: bool,
    nums_diff_fn: NumDiff,
) -> bool:
    """Return True when another numeric field differs, printing the diff."""
    keys = list(
        set(ref.keys())
        - {"arc", "activity", "delta/score", "blocked", "knowledge"}
    )
    for key in keys:
        if nums_diff_fn(entry[key], ref[key], strict):
            print("*** Diff for {}: {}, {}".format(key, entry[key], ref[key]))
            return True
    return False


def _blocked_diff(
    entry: Dict[str, Any],
    ref: Dict[str, Any],
    strict: bool,
    ignore: set,
    nums_diff_fn: NumDiff,
) -> bool:
    """Return True when the blocked fields differ and are not ignored."""
    if "blocked" not in entry or "blocked" not in ref:
        return False
    if "blocked" in ignore:
        return False
    return not blocked_same(
        entry["blocked"], ref["blocked"], strict, nums_diff_fn
    )


def _knowledge_diff(
    entry: Dict[str, Any], ref: Dict[str, Any], ignore: set
) -> Optional[DiffType]:
    """Return the knowledge-field difference type, if any."""
    if "knowledge" not in ref or "knowledge" not in entry:
        return None
    if entry["knowledge"] == ref["knowledge"]:
        return None
    print(ignore)
    if "act_cache" not in ignore:
        return DiffType.MINOR
    return _act_cache_diff(entry, ref)


def _act_cache_diff(
    entry: Dict[str, Any], ref: Dict[str, Any]
) -> Optional[DiffType]:
    """Return None when the knowledge difference is only act_cache noise."""
    ref_none = ref["knowledge"] is None
    ent_none = entry["knowledge"] is None
    ref_a_c = not ref_none and ref["knowledge"][0] == "act_cache"
    ent_a_c = not ent_none and entry["knowledge"][0] == "act_cache"
    if (
        (ref_a_c and ent_none)
        or (ref_none and ent_a_c)
        or (ref_a_c and ent_a_c)
    ):
        return None
    return DiffType.MINOR


def update_diffs(
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


def merge_opposites(activity: str, diffs: Dict[Any, Any]) -> Dict[Any, Any]:
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
    if extra not in diffs or missing not in diffs:
        return diffs
    for arc in list(diffs[extra].keys()):
        _merge_opposite_arc(activity, arc, diffs, extra, missing)
    return diffs


def _merge_opposite_arc(
    activity: str,
    arc: Any,
    diffs: Dict[Any, Any],
    extra: Any,
    missing: Any,
) -> None:
    """Merge a single extra arc with its opposing missing arc, if present."""
    opp_arc = (arc[1], arc[0])
    if opp_arc not in diffs[missing]:
        return
    opposite = (activity, DiffType.OPPOSITE.value)
    if opposite not in diffs:
        diffs[opposite] = {}
    ref_iters = diffs[missing][opp_arc]
    diffs[opposite].update({arc: [diffs[extra][arc][0], ref_iters[1]]})
    del diffs[extra][arc]
    del diffs[missing][opp_arc]


def _summary_head(
    diffs: Dict[Any, Any],
    final_score_diff: bool,
    trace_iters: int,
    ref_iters: int,
) -> str:
    """Return the header line of the human readable summary."""
    return (
        "Trace has {} initial score".format(
            "different" if ("init", DiffType.SCORE.value) in diffs else "same"
        )
        + ", {} final score".format(
            "different" if final_score_diff else "same"
        )
        + " in {} versus {} iterations".format(trace_iters, ref_iters)
    )


def diffs_summary(
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
    summary = _summary_head(diffs, final_score_diff, trace_iters, ref_iters)
    for activity in _ACTIVITIES:
        summary += _activity_lines(activity, diffs)
    return summary


def _activity_lines(activity: str, diffs: Dict[Any, Any]) -> str:
    """Return the summary lines for one activity, if present."""
    return "".join(
        _activity_line(activity, diff_type, diffs) for diff_type in _DIFF_TYPES
    )


def _activity_line(
    activity: str, diff_type: str, diffs: Dict[Any, Any]
) -> str:
    """Return one summary line for an activity/diff-type pair, if present."""
    key = (activity, diff_type)
    if key not in diffs:
        return ""
    return "\n{} {} {}(s): {}".format(
        len(diffs[key]), diff_type, activity, diffs[key]
    )


def _diff_type(iters: Any) -> DiffType:
    """Classify a (trace, ref) iteration pair into a DiffType."""
    if len(iters[0]) > len(iters[1]):
        return DiffType.EXTRA
    if len(iters[0]) < len(iters[1]):
        return DiffType.MISSING
    if iters[0] != iters[1]:
        return DiffType.ORDER
    return DiffType.SCORE


def _reorganise_diffs(_diffs: Dict[Any, Any]) -> Dict[Any, Any]:
    """Reorganise differences to be keyed by (activity, difference type)."""
    diffs: Dict[Any, Any] = {}
    for diff, iters in _diffs.items():
        key = (diff[0], _diff_type(iters).value)
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
    return diffs


def _merge_all_opposites(diffs: Dict[Any, Any]) -> Dict[Any, Any]:
    """Merge opposing add/delete/reverse activities."""
    for activity in _ACTIVITIES:
        diffs = merge_opposites(activity, diffs)
    return diffs


def _ignore_features(trace: Any, ref: Any) -> set:
    """Return trace features to ignore for the pre/post v177 boundary."""
    if (trace.context["software_version"] - 176.5) * (
        ref.context["software_version"] - 176.5
    ) > 0.0:
        return set()
    return {"blocked", "act_cache"}


def _comparison_columns(trace_df: DataFrame, ref_df: DataFrame) -> List[str]:
    """Return the columns to compare across the two traces."""
    return list(
        set(trace_df.columns[trace_df.notnull().any()]).intersection(
            set(ref_df.columns[ref_df.notnull().any()])
        )
        - {"time"}
        | {"arc", "activity", "delta/score"}
    )


def _records(df: DataFrame, compare: List[str]) -> List[Dict[str, Any]]:
    """Return a DataFrame subset as a list of record dictionaries."""
    # DataFrame subset .to_dict() - pandas stubs differ across versions
    # Mypy on Python 3.11 sees df[list] as Series, ignore and cast
    subset = df[compare]
    records = subset.to_dict(  # type: ignore[call-overload,unused-ignore]  # noqa: E501
        orient="records"
    )
    return cast(List[Dict[str, Any]], records)


def _comparison_records(
    trace: Any, ref: Any
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Return the (trace, reference) records to compare."""
    ref_df = ref.get()
    trace_df = trace.get()
    compare = _comparison_columns(trace_df, ref_df)
    return _records(trace_df, compare), _records(ref_df, compare)


def _validate_records(
    trace_records: List[Dict[str, Any]],
    ref_records: List[Dict[str, Any]],
) -> None:
    """Raise ValueError unless both traces have the expected shape."""
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


def _collect_raw_diffs(
    trace_records: List[Dict[str, Any]],
    ref_records: List[Dict[str, Any]],
    strict: bool,
    ignore: set,
    nums_diff_fn: NumDiff,
) -> Tuple[Dict[Any, Any], List[int]]:
    """Loop through the entries collecting per-iteration differences."""
    _diffs: Dict[Any, Any] = {}
    minor: List[int] = []
    for iter in range(0, len(trace_records)):
        if iter >= len(ref_records):
            _diffs = update_diffs(iter, trace_records[iter], None, _diffs)
            continue
        diff = compare_entry(
            trace_records[iter],
            ref_records[iter],
            strict,
            ignore,
            nums_diff_fn,
        )
        if diff in [DiffType.MAJOR, DiffType.SCORE]:
            _diffs = update_diffs(
                iter, trace_records[iter], ref_records[iter], _diffs
            )
            continue
        if diff is not None:
            minor.append(iter)
    for iter in range(len(trace_records), len(ref_records)):
        _diffs = update_diffs(iter, None, ref_records[iter], _diffs)
    return _diffs, minor


def build_diffs(
    trace: Any, ref: Any, strict: bool, nums_diff_fn: NumDiff
) -> Optional[Tuple[Dict[Any, Any], List[int], str]]:
    """Find differences of trace from reference trace.

    Args:
        trace: Trace to compare.
        ref: Reference trace to compare against.
        strict (bool): Whether floats are tested to be strictly the
            same or just reasonably similar.
        nums_diff_fn (callable): Numeric comparison to use.

    Returns:
        tuple or None: (major differences, minor differences,
            textual summary) or None if identical.
    """
    ignore = _ignore_features(trace, ref)
    trace_records, ref_records = _comparison_records(trace, ref)
    _validate_records(trace_records, ref_records)
    _diffs, minor = _collect_raw_diffs(
        trace_records, ref_records, strict, ignore, nums_diff_fn
    )
    if not len(_diffs) and not len(minor):
        return None
    diffs = _merge_all_opposites(_reorganise_diffs(_diffs))
    final_score_diff = (
        compare_entry(
            trace_records[-1], ref_records[-1], strict, ignore, nums_diff_fn
        )
        == DiffType.SCORE
    )
    summary = diffs_summary(
        diffs, final_score_diff, len(trace_records) - 1, len(ref_records) - 1
    )
    return (diffs, minor, summary)
