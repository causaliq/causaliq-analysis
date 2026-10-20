"""Unit tests for the plot entry point."""

import pytest
from pandas import DataFrame

from causaliq_analysis.plot import run_plot


# Run plot rejects unknown plot kinds.
def test_run_plot_unknown_kind(tmp_path):
    """Test run_plot raises ValueError for unsupported kinds."""
    csv_path = tmp_path / "data.csv"
    DataFrame(
        {
            "subplot": ["a"],
            "group": ["g"],
            "x": [1],
            "y": [0.5],
        }
    ).to_csv(csv_path, index=False)
    with pytest.raises(ValueError, match="Unknown plot type"):
        run_plot(
            input_path=str(csv_path),
            output=str(tmp_path / "out.png"),
            kind="pie",
            subplot="subplot",
            group="group",
            x="x",
            y="y",
        )


# Run plot raises ValueError when the input file is missing.
def test_run_plot_missing_file(tmp_path):
    """Test run_plot raises ValueError for a missing input file."""
    with pytest.raises(ValueError, match="Input file not found"):
        run_plot(
            input_path=str(tmp_path / "missing.csv"),
            output=str(tmp_path / "out.png"),
            kind="line",
            subplot="subplot",
            group="group",
            x="x",
            y="y",
        )


# Run plot raises ValueError when required columns are missing.
def test_run_plot_missing_column(tmp_path):
    """Test run_plot raises ValueError for missing input columns."""
    csv_path = tmp_path / "data.csv"
    DataFrame({"subplot": ["a"]}).to_csv(csv_path, index=False)
    with pytest.raises(ValueError, match="missing required column"):
        run_plot(
            input_path=str(csv_path),
            output=str(tmp_path / "out.png"),
            kind="line",
            subplot="subplot",
            group="group",
            x="x",
            y="y",
        )


# Run plot generates a line chart and metadata.
def test_run_plot_generates_line_chart(tmp_path):
    """Test run_plot produces an output chart file."""
    csv_path = tmp_path / "data.csv"
    DataFrame(
        {
            "subplot": ["a", "a"],
            "group": ["g1", "g1"],
            "x": [1, 2],
            "y": [0.5, 0.6],
        }
    ).to_csv(csv_path, index=False)
    out_path = tmp_path / "charts" / "out.png"
    metadata = run_plot(
        input_path=str(csv_path),
        output=str(out_path),
        kind="line",
        subplot="subplot",
        group="group",
        x="x",
        y="y",
    )
    assert out_path.exists()
    assert out_path.stat().st_size > 0
    assert metadata["type"] == "line"
    assert metadata["columns"] == {
        "subplot": "subplot",
        "group": "group",
        "x": "x",
        "y": "y",
    }


# Run plot logs progress messages when a log function is provided.
def test_run_plot_logging(tmp_path, capsys):
    """Test run_plot calls the log function with progress messages."""
    csv_path = tmp_path / "data.csv"
    DataFrame(
        {
            "subplot": ["a"],
            "group": ["g1"],
            "x": [1],
            "y": [0.5],
        }
    ).to_csv(csv_path, index=False)
    messages = []
    run_plot(
        input_path=str(csv_path),
        output=str(tmp_path / "out.png"),
        kind="line",
        subplot="subplot",
        group="group",
        x="x",
        y="y",
        log_fn=messages.append,
    )
    assert any("Plotting line" in m for m in messages)


# Run plot handles whitespace-padded column names and values.
def test_run_plot_strips_padded_columns(tmp_path):
    """Test run_plot tolerates whitespace-padded summarise CSV output."""
    csv_path = tmp_path / "padded.csv"
    csv_path.write_text(
        " network , series   , sample_size , f1.mean \n"
        " asia    , HC_STD   , 100         , 0.5     \n"
        " asia    , HC_OPT   , 100         , 0.7     \n"
    )
    out_path = tmp_path / "out.png"
    run_plot(
        input_path=str(csv_path),
        output=str(out_path),
        kind="line",
        subplot="network",
        group="series",
        x="sample_size",
        y="f1.mean",
    )
    assert out_path.exists()


# Run plot generates a scatter chart when type is scatter.
def test_run_plot_scatter(tmp_path):
    """Test run_plot dispatches scatter plots to plot_scatter."""
    csv_path = tmp_path / "data.csv"
    DataFrame(
        {
            "subplot": ["a", "a"],
            "group": ["g1", "g1"],
            "x": [1, 2],
            "y": [0.5, 0.6],
        }
    ).to_csv(csv_path, index=False)
    out_path = tmp_path / "out.png"
    run_plot(
        input_path=str(csv_path),
        output=str(out_path),
        kind="scatter",
        subplot="subplot",
        group="group",
        x="x",
        y="y",
    )
    assert out_path.exists()


# Run plot reads metric rows from a metrics workflow cache.
def test_run_plot_reads_metrics_cache(tmp_path):
    """Test run_plot builds a chart from a metrics workflow cache."""
    import json

    from causaliq_workflow.cache import CacheEntry, WorkflowCache

    cache_path = tmp_path / "metrics.db"
    with WorkflowCache(cache_path) as cache:
        for series, f1 in [("a", 0.5), ("b", 0.7)]:
            entry = CacheEntry()
            entry.add_object("metrics", "json", json.dumps({"f1": f1}))
            cache.put_typed(
                {"series": series, "network": "asia", "sample_size": 100},
                entry,
            )

    out_path = tmp_path / "out.png"
    metadata = run_plot(
        input_path=str(cache_path),
        output=str(out_path),
        kind="line",
        subplot="network",
        group="series",
        x="sample_size",
        y="f1",
    )
    assert out_path.exists()
    assert metadata["type"] == "line"


# Run plot skips cache entries without usable metrics.
def test_run_plot_skips_entries_without_metrics(tmp_path):
    """Test run_plot ignores entries with missing or empty metrics."""
    import json

    from causaliq_workflow.cache import CacheEntry, WorkflowCache

    cache_path = tmp_path / "metrics.db"
    with WorkflowCache(cache_path) as cache:
        valid = CacheEntry()
        valid.add_object("metrics", "json", json.dumps({"f1": 0.5}))
        cache.put_typed(
            {"series": "a", "network": "asia", "sample_size": 100}, valid
        )

        # A failed run writes metadata only, with the cache's object type
        cache.put_failure(
            {"series": "b", "network": "asia", "sample_size": 100},
            {"status": "error"},
            "metrics",
        )

        # A legacy entry with no metrics object
        other = CacheEntry()
        other.add_object("dag", "graphml", "<g/>")
        cache.put(
            {"series": "c", "network": "asia", "sample_size": 100}, other
        )

    out_path = tmp_path / "out.png"
    run_plot(
        input_path=str(cache_path),
        output=str(out_path),
        kind="line",
        subplot="network",
        group="series",
        x="sample_size",
        y="f1",
    )
    assert out_path.exists()


# Run plot reports a missing metrics cache.
def test_run_plot_missing_cache(tmp_path):
    """Test run_plot raises ValueError for a missing metrics cache."""
    with pytest.raises(ValueError, match="No metric entries found"):
        run_plot(
            input_path=str(tmp_path / "missing.db"),
            output=str(tmp_path / "out.png"),
            kind="line",
            subplot="subplot",
            group="group",
            x="x",
            y="y",
        )


# Entry metrics returns None for a missing entry.
def test_entry_metrics_missing_entry() -> None:
    """Test entry metrics returns None for a missing entry."""
    from causaliq_analysis.plot.run import _entry_metrics

    assert _entry_metrics(None) is None


# Entry metrics ignores a non-dict metrics payload.
def test_entry_metrics_ignores_non_dict_payload() -> None:
    """Test entry metrics returns None for a non-dict payload."""
    from causaliq_workflow.cache import CacheEntry

    from causaliq_analysis.plot.run import _entry_metrics

    entry = CacheEntry()
    entry.add_object("metrics", "json", "[1, 2]")

    assert _entry_metrics(entry) is None
