"""Unit tests for summarise report rendering and reading."""

from typing import Any

import pytest

from causaliq_analysis.workflow_action.actions.summarise.render_csv import (
    _write_report,
)
from causaliq_analysis.workflow_action.actions.summarise.report import (
    _report_entries,
)
from causaliq_analysis.workflow_action.types import ActionExecutionError


# Test report rendering wraps write failures.
def test_write_report_wraps_write_error(tmp_path: Any) -> None:
    """An unwritable destination is reported, not raised raw."""
    rows = [({"network": "asia"}, {"f1.mean": 0.9})]
    with pytest.raises(ActionExecutionError, match="Failed to write"):
        _write_report({"output": str(tmp_path)}, rows, None)


# Test unreadable caches are reported as action errors.
def test_report_entries_wraps_read_error(tmp_path: Any) -> None:
    """A cache that cannot be opened is reported, not raised raw."""
    cache_dir = tmp_path / "broken.db"
    cache_dir.mkdir()
    with pytest.raises(ActionExecutionError, match="Failed to read cache"):
        _report_entries(str(cache_dir))


# Test report rendering reports the number of rows written.
def test_write_report_logs_row_count(tmp_path: Any) -> None:
    """A successful report write reports how many rows were written."""
    messages = []
    rows = [({"network": "asia"}, {"f1.mean": 0.9})]
    output = str(tmp_path / "report.csv")
    _write_report({"output": output}, rows, messages.append)
    assert messages == [f"Summary written to {output}"]
