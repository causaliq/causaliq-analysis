"""Functional tests for the summarise table output formats."""

import csv
import json
from types import SimpleNamespace
from typing import Any, Dict, List

import pytest

from causaliq_analysis.cli import cli


def _write_cache(path: Any, rows: Dict[str, Dict[str, Any]]) -> str:
    """Write a workflow cache holding result metrics per network.

    Args:
        path: Destination cache path.
        rows: Result metrics keyed by network name.

    Returns:
        The cache path as a string.
    """
    from causaliq_workflow.cache import CacheEntry, WorkflowCache

    with WorkflowCache(str(path)) as cache:
        for network, results in rows.items():
            cache.put(
                {"network": network},
                CacheEntry(metadata={"provenance": {}, "result": results}),
            )
    return str(path)


def _context(networks: List[str]) -> Any:
    """Build a workflow context grouping by network."""
    return SimpleNamespace(
        matrix={"network": networks},
        matrix_values={"network": networks[0]},
        cache=None,
    )


def _run_action(
    cache_paths: List[str],
    metric: List[str],
    output: Any,
    context: Any,
    **extra: Any,
) -> Any:
    """Run the summarise action and return its result."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    parameters: Dict[str, Any] = {
        "metric": metric,
        "input": cache_paths,
        "output": str(output),
    }
    parameters.update(extra)
    return AnalysisActionProvider().run(
        action="summarise",
        parameters=parameters,
        mode="run",
        context=context,
        logger=SimpleNamespace(is_terminal_logging=False),
    )


def _fusion_inputs(tmp_path: Any) -> List[str]:
    """Build the three input caches of the worked example."""
    bnsl = _write_cache(
        tmp_path / "bnsl.db",
        {
            "alarm": {"node_count": 37, "f1": 0.804},
            "asia": {"node_count": 8, "f1": 0.75},
        },
    )
    llm = _write_cache(
        tmp_path / "llm.db",
        {
            "alarm": {"f1": 0.653},
            "asia": {"f1": 0.842},
        },
    )
    fusion = _write_cache(
        tmp_path / "fusion.db",
        {
            "alarm": {"f1": 0.866},
            "asia": {"f1": 1.0},
        },
    )
    return [bnsl, llm, fusion]


_FUSION_METRIC = [
    "node_count[1] as nodes",
    "f1.mean[1] as bnsl",
    "f1.mean[2] as llm",
    "f1.mean[3] as fusion",
    "fusion - max(bnsl, llm) as gain",
]

_FUSION_HEADERS = ["Network", "Nodes", "BNSL", "LLM", "Fusion", "F>best"]

_FUSION_FORMATS = ["", "d", ".3f", ".3f", ".3f", "+.3f"]

_FUSION_FOOTER = ["AVERAGE", "", "mean", "mean", "mean", "mean"]


# Test a workflow table is written as Markdown.
def test_workflow_markdown_table(tmp_path: Any) -> None:
    """The Markdown table holds headers, alignment, rows and a footer."""
    caches = _fusion_inputs(tmp_path)
    output = tmp_path / "table.md"
    _run_action(
        caches,
        _FUSION_METRIC,
        output,
        _context(["alarm", "asia"]),
        headers=_FUSION_HEADERS,
        format=_FUSION_FORMATS,
        footer=_FUSION_FOOTER,
    )

    lines = output.read_text(encoding="utf-8").splitlines()
    assert lines[0] == ("| Network | Nodes | BNSL | LLM | Fusion | F>best |")
    assert lines[1] == "| :--- | ---: | ---: | ---: | ---: | ---: |"
    assert lines[2] == "| alarm | 37 | 0.804 | 0.653 | 0.866 | +0.062 |"
    assert lines[3] == "| asia | 8 | 0.750 | 0.842 | 1.000 | +0.158 |"
    assert lines[4] == "| AVERAGE |  | 0.777 | 0.748 | 0.933 | +0.110 |"


# Test a workflow table is written as a LaTeX tabular fragment.
def test_workflow_latex_table(tmp_path: Any) -> None:
    """The LaTeX table is a tabular fragment with rules and a footer."""
    caches = _fusion_inputs(tmp_path)
    output = tmp_path / "table.tex"
    _run_action(
        caches,
        _FUSION_METRIC,
        output,
        _context(["alarm", "asia"]),
        headers=_FUSION_HEADERS,
        format=_FUSION_FORMATS,
        footer=_FUSION_FOOTER,
    )

    lines = output.read_text(encoding="utf-8").splitlines()
    assert lines[0] == r"\begin{tabular}{lrrrrr}"
    assert lines[1] == (
        r"Network & Nodes & BNSL & LLM & Fusion & F\textgreater{}best \\"
    )
    assert lines[2] == r"\hline"
    assert lines[-3] == r"\hline"
    assert lines[-2] == (r"AVERAGE &  & 0.777 & 0.748 & 0.933 & +0.110 \\")
    assert lines[-1] == r"\end{tabular}"


# Test the CSV output keeps raw values and the declared headers.
def test_workflow_csv_table(tmp_path: Any) -> None:
    """CSV output applies the headers but not the formats."""
    caches = _fusion_inputs(tmp_path)
    output = tmp_path / "table.csv"
    _run_action(
        caches,
        _FUSION_METRIC,
        output,
        _context(["alarm", "asia"]),
        headers=_FUSION_HEADERS,
        format=_FUSION_FORMATS,
        footer=_FUSION_FOOTER,
    )

    with open(output, encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert list(rows[0]) == _FUSION_HEADERS
    assert rows[0]["Fusion"] == "0.866"
    assert float(rows[0]["F>best"]) == pytest.approx(0.062)
    assert len(rows) == 2


# Test the CLI writes a Markdown table with headers and a footer.
def test_cli_markdown_table(cli_runner: Any, tmp_path: Any) -> None:
    """The CLI renders a Markdown table from a metrics JSON file."""
    input_path = tmp_path / "metrics.json"
    input_path.write_text(json.dumps([{"f1": 0.8}, {"f1": 0.9}]))
    output = tmp_path / "table.md"

    result = cli_runner.invoke(
        cli,
        [
            "summarise",
            "-m",
            "f1.mean",
            "-m",
            "f1.count",
            "-i",
            str(input_path),
            "-o",
            str(output),
            "--header",
            "Mean",
            "--header",
            "N",
            "--format",
            ".3f",
            "--format",
            "d",
            "--footer",
            "mean",
            "--footer",
            "count",
        ],
    )

    assert result.exit_code == 0
    lines = output.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "| Mean | N |"
    assert lines[1] == "| ---: | ---: |"
    assert lines[2] == "| 0.850 | 2 |"
    # A footer 'count' counts the table rows, not the summarised values
    assert lines[3] == "| 0.850 | 1 |"


# Test the CLI writes a LaTeX table.
def test_cli_latex_table(cli_runner: Any, tmp_path: Any) -> None:
    """The CLI renders a LaTeX tabular from a metrics JSON file."""
    input_path = tmp_path / "metrics.json"
    input_path.write_text(json.dumps({"f1": 0.8}))
    output = tmp_path / "table.tex"

    result = cli_runner.invoke(
        cli,
        [
            "summarise",
            "-m",
            "f1.mean",
            "-i",
            str(input_path),
            "-o",
            str(output),
            "--format",
            ".3f",
        ],
    )

    assert result.exit_code == 0
    lines = output.read_text(encoding="utf-8").splitlines()
    assert lines[0] == r"\begin{tabular}{r}"
    assert lines[1] == r"f1.mean \\"
    assert lines[2] == r"\hline"
    assert lines[3] == r"0.800 \\"
    assert lines[4] == r"\end{tabular}"


# Test the CLI applies declared headers to CSV output.
def test_cli_csv_headers(cli_runner: Any, tmp_path: Any) -> None:
    """Declared headers label the CSV columns; values stay raw."""
    input_path = tmp_path / "metrics.json"
    input_path.write_text(json.dumps([{"f1": 0.8}]))
    output = tmp_path / "table.csv"

    result = cli_runner.invoke(
        cli,
        [
            "summarise",
            "-m",
            "f1.mean",
            "-i",
            str(input_path),
            "-o",
            str(output),
            "--header",
            "BNSL",
            "--format",
            ".3f",
        ],
    )

    assert result.exit_code == 0
    assert output.read_text(encoding="utf-8").splitlines()[0] == "BNSL"


# Test the CLI rejects a footer with the wrong number of cells.
def test_cli_rejects_footer_count(cli_runner: Any, tmp_path: Any) -> None:
    """A footer must have one cell per metric."""
    input_path = tmp_path / "metrics.json"
    input_path.write_text(json.dumps([{"f1": 0.8}]))

    result = cli_runner.invoke(
        cli,
        [
            "summarise",
            "-m",
            "f1.mean",
            "-m",
            "f1.count",
            "-i",
            str(input_path),
            "-o",
            str(tmp_path / "table.md"),
            "--footer",
            "mean",
        ],
    )

    assert result.exit_code != 0
    assert "--footer must be given 2 times" in result.output


# Test a pre-scanned entry set writes a single-row Markdown table.
def test_entries_mode_markdown_table(tmp_path: Any) -> None:
    """Without an input cache the action writes one accumulated row."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    output = tmp_path / "row.md"
    entries = [
        {
            "matrix_values": {},
            "metadata": {"provenance": {}, "result": {"f1": 0.8}},
            "cache_path": "metrics.db",
        }
    ]
    result = AnalysisActionProvider().run(
        action="summarise",
        parameters={
            "_aggregation_entries": entries,
            "metric": ["f1.mean"],
            "output": str(output),
            "headers": ["F1"],
            "format": [".3f"],
        },
        mode="run",
        context=None,
        logger=SimpleNamespace(is_terminal_logging=False),
    )

    assert result[0] == "success"
    assert result[1]["table_output"] == str(output)
    lines = output.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "| F1 |"
    assert lines[1] == "| ---: |"
    assert lines[2] == "| 0.800 |"


# Test the CLI reports a table it cannot write.
def test_cli_reports_write_failure(cli_runner: Any, tmp_path: Any) -> None:
    """An unwritable table destination is reported as a CLI error."""
    input_path = tmp_path / "metrics.json"
    input_path.write_text(json.dumps([{"f1": 0.8}]))
    output = tmp_path / "table.md"
    output.mkdir()

    result = cli_runner.invoke(
        cli,
        [
            "summarise",
            "-m",
            "f1.mean",
            "-i",
            str(input_path),
            "-o",
            str(output),
        ],
    )

    assert result.exit_code != 0
    assert "Failed to write output" in result.output


# Test the CLI rejects an invalid format specification.
def test_cli_rejects_invalid_format(cli_runner: Any, tmp_path: Any) -> None:
    """A format specification Python cannot apply is rejected."""
    input_path = tmp_path / "metrics.json"
    input_path.write_text(json.dumps([{"f1": 0.8}]))

    result = cli_runner.invoke(
        cli,
        [
            "summarise",
            "-m",
            "f1.mean",
            "-i",
            str(input_path),
            "-o",
            str(tmp_path / "table.md"),
            "--format",
            "i3",
        ],
    )

    assert result.exit_code != 0
    assert "Invalid format spec" in result.output
