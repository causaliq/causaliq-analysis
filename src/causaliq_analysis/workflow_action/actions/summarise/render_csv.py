"""Writing summary rows to a CSV file."""

import csv
from pathlib import Path
from typing import Any

from causaliq_analysis.workflow_action.types import ActionExecutionError

from .present import _table_columns

__all__ = ["_write_csv"]


def _write_csv(
    request: dict[str, Any],
    matrix_values: dict[str, Any],
    results: dict[str, Any],
    metadata: dict[str, Any],
    log_fn: Any | None,
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
    labels = _csv_labels(request, matrix_values)
    try:
        file_exists = out_file.exists()
        _append_row(out_file, row_data, file_exists, labels)
        verb = "appended to" if file_exists else "written to"
        metadata["csv_output"] = str(out_file)
        if log_fn:
            log_fn(f"Summary {verb} {out_file}")
    except Exception as e:
        raise ActionExecutionError(f"Failed to write CSV output: {e}") from e


def _csv_labels(
    request: dict[str, Any],
    matrix_values: dict[str, Any],
) -> list[str]:
    """Return the CSV column labels, including hidden columns.

    Args:
        request: Summarisation request.
        matrix_values: Matrix values from the workflow context.

    Returns:
        Column labels in column order. Hidden columns keep their default
        label so that the CSV output still names every column.

    """
    columns = _table_columns(
        list(matrix_values),
        request["parsed_metrics"],
        request,
    )
    return [column.label for column in columns]


def _csv_row(
    matrix_values: dict[str, Any],
    results: dict[str, Any],
) -> dict[str, Any]:
    """Build the CSV row holding matrix values then metrics.

    Args:
        matrix_values: Matrix values from the workflow context.
        results: Computed metric values.

    Returns:
        Row mapping column names to values.

    """
    row_data: dict[str, Any] = {}
    for key, value in matrix_values.items():
        row_data[key] = value
    row_data.update(results)
    return row_data


def _append_row(
    out_file: Path,
    row_data: dict[str, Any],
    file_exists: bool,
    labels: list[str],
) -> None:
    """Write a summary row, creating the header when needed.

    Args:
        out_file: CSV file to write to.
        row_data: Row mapping column names to values.
        file_exists: Whether the file already holds a header row.
        labels: Column labels, aligned with the row values.

    """
    mode = "a" if file_exists else "w"
    with open(out_file, mode, encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        if not file_exists:
            writer.writerow(labels)
        writer.writerow(row_data.values())


def _write_report(
    request: dict[str, Any],
    rows: list[tuple[dict[str, Any], dict[str, Any]]],
    log_fn: Any | None,
    labels: list[str] | None = None,
    keys: list[str] | None = None,
) -> None:
    """Write the complete report file, replacing any existing content.

    Args:
        request: Summarisation request.
        rows: Group matrix values and computed results, in report order.
        log_fn: Logging callback for progress reporting.
        labels: Column labels, or None to name the columns after the
            matrix values and metric specifications.
        keys: Value keys to write, or None to use every key in the rows.

    Raises:
        ActionExecutionError: If the CSV file cannot be written.

    """
    output_path = request["output"]
    assert output_path is not None  # Validated by the action validator
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    if keys is None:
        keys = list(rows[0][0]) + list(rows[0][1])
    try:
        _write_rows(out_file, list(labels or keys), keys, rows)
    except Exception as e:
        raise ActionExecutionError(f"Failed to write CSV output: {e}") from e
    if log_fn:
        log_fn(f"Summary written to {out_file}")


def _write_rows(
    out_file: Path,
    header: list[str],
    keys: list[str],
    rows: list[tuple[dict[str, Any], dict[str, Any]]],
) -> None:
    """Write the report header and rows to a file.

    Args:
        out_file: Destination CSV file.
        header: Column labels in report order.
        keys: Row value keys, aligned with the header.
        rows: Group matrix values and computed results, in report order.

    """
    with open(out_file, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        for group, results in rows:
            values = {**group, **results}
            writer.writerow([values.get(key, "") for key in keys])
