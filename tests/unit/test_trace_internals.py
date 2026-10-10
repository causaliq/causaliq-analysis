# Focused tests for the thin Trace delegating helpers and diff branches

from causaliq_analysis.graph import GraphAction, GraphActionDetail
from causaliq_analysis.trace import DiffType, Trace


# _blocked_same delegates to the diff helper
def test_trace_blocked_same_delegates():
    trace = Trace()
    assert trace._blocked_same(None, None, strict=False) is True
    assert trace._blocked_same([], [("delete",)], strict=False) is False


# _update_diffs delegates to the diff helper
def test_trace_update_diffs_delegates():
    trace = Trace()
    entry = {"activity": "add", "arc": ("A", "B")}
    diffs = trace._update_diffs(3, entry, None, {})
    assert diffs[("add", ("A", "B"))][0] == [3]


# _diffs_summary delegates to the diff helper
def test_trace_diffs_summary_delegates():
    trace = Trace()
    summary = trace._diffs_summary({}, False, 4, 4)
    assert summary == (
        "Trace has same initial score, same final score "
        "in 4 versus 4 iterations"
    )


# blocked fields are ignored when 'blocked' is in the ignore set
def test_compare_entry_blocked_ignored():
    entry = {
        "activity": "add",
        "arc": ("A", "B"),
        "delta/score": 1.0,
        "blocked": [],
    }
    ref = {
        "activity": "add",
        "arc": ("A", "B"),
        "delta/score": 1.0,
        "blocked": [("delete", ("A", "B"), 1.0, {})],
    }
    result = Trace._compare_entry(entry, ref, strict=False, ignore={"blocked"})
    assert result is None


# knowledge difference returns MINOR when it is not act_cache noise
def test_compare_entry_knowledge_minor():
    entry = {
        "activity": "add",
        "arc": ("A", "B"),
        "delta/score": 1.0,
        "knowledge": ("equiv_add", True),
    }
    ref = {
        "activity": "add",
        "arc": ("A", "B"),
        "delta/score": 1.0,
        "knowledge": ("other", True),
    }
    result = Trace._compare_entry(
        entry, ref, strict=False, ignore={"act_cache"}
    )
    assert result == DiffType.MINOR


# pre-v177 traces ignore the blocked and act_cache features
def test_diffs_from_ignores_legacy_features():
    trace = Trace({"id": "a"})
    ref = Trace({"id": "b"})
    trace.context["software_version"] = 176.0
    ref.context["software_version"] = 177.0
    trace.add(GraphAction.INIT, {GraphActionDetail.DELTA: 0.0})
    trace.add(GraphAction.STOP, {GraphActionDetail.DELTA: 1.0})
    ref.add(GraphAction.INIT, {GraphActionDetail.DELTA: 0.0})
    ref.add(GraphAction.STOP, {GraphActionDetail.DELTA: 1.0})
    assert trace.diffs_from(ref) is None
