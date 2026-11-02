"""Writing summary rows to a CSV file."""

import csv
from pathlib import Path
from typing import Any, Dict, Optional

from causaliq_analysis.workflow_action.types import ActionExecutionError

__all__ = ["_write_csv"]


def _write_csv(
    request: Dict[str, Any],
    matrix_values: Dict[str, Any],
    results: Dict[str, Any],
    metadata: Dict[str, Any],
    log_fn: Optional[Any],
) -> None:
    """Append the summary row to the CSV output file.

    Args:
        request: Summarisation request.
        matrix_values: Matrix values from the workflow context.
        results: Computed metric values.
        metadata: Result metadata, updated with the output path.
        log_fn: Logging callback for progress reporting.

    Raises:
        ActionExecutionError: If the CSV file cannot be written.

    """
    output_path = request["output"]
    assert output_path is not None  # Validated by the action validator
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    row_data = _csv_row(matrix_values, results)
    try:
        file_exists = out_file.exists()
        _append_row(out_file, row_data, file_exists)
        verb = "appended to" if file_exists else "written to"
        metadata["csv_output"] = str(out_file)
        if log_fn:
            log_fn(f"Summary {verb} {out_file}")
    except Exception as e:
        raise ActionExecutionError(f"Failed to write CSV output: {e}") from e


def _csv_row(
    matrix_values: Dict[str, Any],
    results: Dict[str, Any],
) -> Dict[str, Any]:
    """Build the CSV row holding matrix values then metrics.

    Args:
        matrix_values: Matrix values from the workflow context.
        results: Computed metric values.

    Returns:
        Row mapping column names to values.

    """
    row_data: Dict[str, Any] = {}
    for key, value in matrix_values.items():
        row_data[key] = value
    row_data.update(results)
    return row_data


def _append_row(
    out_file: Path,
    row_data: Dict[str, Any],
    file_exists: bool,
) -> None:
    """Write a summary row, creating the header when needed.

    Args:
        out_file: CSV file to write to.
        row_data: Row mapping column names to values.
        file_exists: Whether the file already holds a header row.

    """
    mode = "a" if file_exists else "w"
    with open(out_file, mode, encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        if not file_exists:
            writer.writerow(row_data.keys())
        writer.writerow(row_data.values())
