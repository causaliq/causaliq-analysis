"""Functional tests for summarise CLI command and helper functions."""

from causaliq_analysis.cli import cli


def test_summarise_json_input(cli_runner, tmp_path):
    """Test summarise command with JSON file input."""
    import json

    # Create JSON input with metric values
    input_data = [
        {"f1": 0.8, "shd": 2},
        {"f1": 0.9, "shd": 1},
        {"f1": 0.85, "shd": 3},
    ]
    input_path = tmp_path / "metrics.json"
    with open(input_path, "w") as f:
        json.dump(input_data, f)

    output_path = tmp_path / "summary.csv"

    result = cli_runner.invoke(
        cli,
        [
            "summarise",
            "-m",
            "f1.mean",
            "-m",
            "f1.sd",
            "-m",
            "shd.count",
            "-i",
            str(input_path),
            "-o",
            str(output_path),
        ],
    )

    assert result.exit_code == 0
    assert output_path.exists()

    # Read CSV and verify
    import csv

    with open(output_path) as f:
        reader = csv.DictReader(f)
        row = next(reader)
        assert abs(float(row["f1.mean"]) - 0.85) < 0.01
        assert row["shd.count"] == "3"


# Test summarise command with single JSON object.
def test_summarise_single_json_object(cli_runner, tmp_path):
    """Test summarise command with single JSON object input."""
    import json

    input_data = {"precision": 0.9, "recall": 0.85}
    input_path = tmp_path / "single.json"
    with open(input_path, "w") as f:
        json.dump(input_data, f)

    output_path = tmp_path / "summary.csv"

    result = cli_runner.invoke(
        cli,
        [
            "summarise",
            "-m",
            "precision.mean",
            "-i",
            str(input_path),
            "-o",
            str(output_path),
        ],
    )

    assert result.exit_code == 0
    import csv

    with open(output_path) as f:
        reader = csv.DictReader(f)
        row = next(reader)
        assert float(row["precision.mean"]) == 0.9


# Test summarise command with _meta.json format files.
def test_summarise_meta_json_format(cli_runner, tmp_path):
    """Test summarise command with _meta.json format files."""
    import json

    # Create _meta.json format with nested provider/action structure
    meta1 = {
        "matrix_values": {"network": "asia", "seed": 0},
        "metadata": {
            "causaliq-analysis": {
                "evaluate_graph": {
                    "f1": 0.8,
                    "shd": 2,
                }
            }
        },
    }
    meta2 = {
        "matrix_values": {"network": "asia", "seed": 1},
        "metadata": {
            "causaliq-analysis": {
                "evaluate_graph": {
                    "f1": 0.9,
                    "shd": 1,
                }
            }
        },
    }

    input1 = tmp_path / "_meta1.json"
    input2 = tmp_path / "_meta2.json"
    with open(input1, "w") as f:
        json.dump(meta1, f)
    with open(input2, "w") as f:
        json.dump(meta2, f)

    output_path = tmp_path / "summary.csv"

    result = cli_runner.invoke(
        cli,
        [
            "summarise",
            "-m",
            "f1.mean",
            "-m",
            "f1.count",
            "-m",
            "shd.mean",
            "-i",
            str(input1),
            "-i",
            str(input2),
            "-o",
            str(output_path),
        ],
    )

    assert result.exit_code == 0
    import csv

    with open(output_path) as f:
        reader = csv.DictReader(f)
        row = next(reader)
        assert abs(float(row["f1.mean"]) - 0.85) < 0.01
        assert row["f1.count"] == "2"
        assert abs(float(row["shd.mean"]) - 1.5) < 0.01


# Test summarise command with invalid metric spec.
def test_summarise_invalid_metric_spec(cli_runner, tmp_path):
    """Test summarise command rejects invalid metric specification."""
    import json

    input_path = tmp_path / "data.json"
    with open(input_path, "w") as f:
        json.dump([{"f1": 0.8}], f)

    result = cli_runner.invoke(
        cli,
        [
            "summarise",
            "-m",
            "f1",  # Missing '.stat' part
            "-i",
            str(input_path),
            "-o",
            str(tmp_path / "out.csv"),
        ],
    )

    assert result.exit_code != 0
    assert "must be <field>.<stat>" in result.output


# Test summarise command with unsupported statistic.
def test_summarise_unsupported_stat(cli_runner, tmp_path):
    """Test summarise command rejects unsupported statistic."""
    import json

    input_path = tmp_path / "data.json"
    with open(input_path, "w") as f:
        json.dump([{"f1": 0.8}], f)

    result = cli_runner.invoke(
        cli,
        [
            "summarise",
            "-m",
            "f1.median",  # Not supported
            "-i",
            str(input_path),
            "-o",
            str(tmp_path / "out.csv"),
        ],
    )

    assert result.exit_code != 0
    assert "Unknown statistic" in result.output


# Test summarise command with unsupported file type.
def test_summarise_unsupported_file_type(cli_runner, tmp_path):
    """Test summarise command rejects unsupported file types."""
    input_path = tmp_path / "data.txt"
    input_path.write_text("some text")

    result = cli_runner.invoke(
        cli,
        [
            "summarise",
            "-m",
            "f1.mean",
            "-i",
            str(input_path),
            "-o",
            str(tmp_path / "out.csv"),
        ],
    )

    assert result.exit_code != 0
    assert "Unsupported file type" in result.output


# Test summarise command SD with insufficient values.
def test_summarise_sd_insufficient_values(cli_runner, tmp_path):
    """Test summarise command returns None for SD with <2 values."""
    import json

    input_data = [{"f1": 0.8}]  # Only one value
    input_path = tmp_path / "single.json"
    with open(input_path, "w") as f:
        json.dump(input_data, f)

    output_path = tmp_path / "summary.csv"

    result = cli_runner.invoke(
        cli,
        [
            "summarise",
            "-m",
            "f1.sd",
            "-i",
            str(input_path),
            "-o",
            str(output_path),
        ],
    )

    assert result.exit_code == 0
    import csv

    with open(output_path) as f:
        reader = csv.DictReader(f)
        row = next(reader)
        assert row["f1.sd"] == "" or row["f1.sd"] == "None"


# Test summarise command with empty values.
def test_summarise_empty_values(cli_runner, tmp_path):
    """Test summarise command handles no matching values."""
    import json

    input_data = [{"other_field": 0.8}]
    input_path = tmp_path / "data.json"
    with open(input_path, "w") as f:
        json.dump(input_data, f)

    output_path = tmp_path / "summary.csv"

    result = cli_runner.invoke(
        cli,
        [
            "summarise",
            "-m",
            "f1.mean",
            "-i",
            str(input_path),
            "-o",
            str(output_path),
        ],
    )

    assert result.exit_code == 0
    import csv

    with open(output_path) as f:
        reader = csv.DictReader(f)
        row = next(reader)
        assert row["f1.mean"] == "" or row["f1.mean"] == "None"


# Test summarise command with invalid JSON.
def test_summarise_invalid_json(cli_runner, tmp_path):
    """Test summarise command handles invalid JSON file."""
    input_path = tmp_path / "bad.json"
    input_path.write_text("{invalid json")

    result = cli_runner.invoke(
        cli,
        [
            "summarise",
            "-m",
            "f1.mean",
            "-i",
            str(input_path),
            "-o",
            str(tmp_path / "out.csv"),
        ],
    )

    assert result.exit_code != 0
    assert "Invalid JSON file" in result.output


# Test summarise command with multiple input files.
def test_summarise_multiple_inputs(cli_runner, tmp_path):
    """Test summarise command with multiple input files."""
    import json

    input1 = tmp_path / "data1.json"
    input2 = tmp_path / "data2.json"
    with open(input1, "w") as f:
        json.dump([{"f1": 0.8}, {"f1": 0.9}], f)
    with open(input2, "w") as f:
        json.dump([{"f1": 0.7}], f)

    output_path = tmp_path / "summary.csv"

    result = cli_runner.invoke(
        cli,
        [
            "summarise",
            "-m",
            "f1.mean",
            "-m",
            "f1.count",
            "-i",
            str(input1),
            "-i",
            str(input2),
            "-o",
            str(output_path),
        ],
    )

    assert result.exit_code == 0
    import csv

    with open(output_path) as f:
        reader = csv.DictReader(f)
        row = next(reader)
        assert row["f1.count"] == "3"
        assert abs(float(row["f1.mean"]) - 0.8) < 0.01


# Test summarise command with filter expression.
def test_summarise_with_filter(cli_runner, tmp_path):
    """Test summarise command with filter expression on JSON."""
    import json

    input_data = [
        {"f1": 0.8, "status": "completed"},
        {"f1": 0.5, "status": "failed"},
        {"f1": 0.9, "status": "completed"},
    ]
    input_path = tmp_path / "data.json"
    with open(input_path, "w") as f:
        json.dump(input_data, f)

    output_path = tmp_path / "summary.csv"

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
            str(output_path),
            "-f",
            "status == 'completed'",
        ],
    )

    assert result.exit_code == 0
    import csv

    with open(output_path) as f:
        reader = csv.DictReader(f)
        row = next(reader)
        # Only 2 values pass filter (0.8 and 0.9)
        assert row["f1.count"] == "2"
        assert abs(float(row["f1.mean"]) - 0.85) < 0.01


# Test summarise command with nested field access.
def test_summarise_nested_field(cli_runner, tmp_path):
    """Test summarise command can access nested fields."""
    import json

    input_data = [
        {"metrics": {"f1": 0.8}},
        {"metrics": {"f1": 0.9}},
    ]
    input_path = tmp_path / "nested.json"
    with open(input_path, "w") as f:
        json.dump(input_data, f)

    output_path = tmp_path / "summary.csv"

    result = cli_runner.invoke(
        cli,
        [
            "summarise",
            "-m",
            "metrics.f1.mean",
            "-i",
            str(input_path),
            "-o",
            str(output_path),
        ],
    )

    assert result.exit_code == 0
    import csv

    with open(output_path) as f:
        reader = csv.DictReader(f)
        row = next(reader)
        assert abs(float(row["metrics.f1.mean"]) - 0.85) < 0.01


# Test summarise command skips non-numeric values.
def test_summarise_skips_non_numeric(cli_runner, tmp_path):
    """Test summarise command skips non-numeric values."""
    import json

    input_data = [
        {"f1": 0.8},
        {"f1": "invalid"},
        {"f1": 0.9},
    ]
    input_path = tmp_path / "mixed.json"
    with open(input_path, "w") as f:
        json.dump(input_data, f)

    output_path = tmp_path / "summary.csv"

    result = cli_runner.invoke(
        cli,
        [
            "summarise",
            "-m",
            "f1.count",
            "-i",
            str(input_path),
            "-o",
            str(output_path),
        ],
    )

    assert result.exit_code == 0
    import csv

    with open(output_path) as f:
        reader = csv.DictReader(f)
        row = next(reader)
        # Only 2 numeric values
        assert row["f1.count"] == "2"


# Test summarise command skips non-dict records.
def test_summarise_skips_non_dict_records(cli_runner, tmp_path):
    """Test summarise command skips non-dict items in array."""
    import json

    input_data = [
        {"f1": 0.8},
        "not a dict",
        {"f1": 0.9},
    ]
    input_path = tmp_path / "mixed_types.json"
    with open(input_path, "w") as f:
        json.dump(input_data, f)

    output_path = tmp_path / "summary.csv"

    result = cli_runner.invoke(
        cli,
        [
            "summarise",
            "-m",
            "f1.count",
            "-i",
            str(input_path),
            "-o",
            str(output_path),
        ],
    )

    assert result.exit_code == 0
    import csv

    with open(output_path) as f:
        reader = csv.DictReader(f)
        row = next(reader)
        assert row["f1.count"] == "2"


# Test summarise command handles non-array/object JSON.
def test_summarise_invalid_json_structure(cli_runner, tmp_path):
    """Test summarise command rejects non-object/array JSON root."""
    import json

    input_path = tmp_path / "bad_structure.json"
    with open(input_path, "w") as f:
        json.dump("just a string", f)

    result = cli_runner.invoke(
        cli,
        [
            "summarise",
            "-m",
            "f1.mean",
            "-i",
            str(input_path),
            "-o",
            str(tmp_path / "out.csv"),
        ],
    )

    assert result.exit_code != 0
    assert "must contain object or array" in result.output


# Test summarise command with workflow cache input.
def test_summarise_workflow_cache_input(cli_runner, tmp_path):
    """Test summarise command reads from workflow cache .db file."""
    from causaliq_workflow.cache import CacheEntry, WorkflowCache

    # Create a workflow cache with entries containing metrics
    cache_path = tmp_path / "results.db"
    with WorkflowCache(str(cache_path)) as cache:
        entry1 = CacheEntry(
            metadata={
                "causaliq-analysis": {"evaluate_graph": {"f1": 0.8, "shd": 2}}
            }
        )
        entry2 = CacheEntry(
            metadata={
                "causaliq-analysis": {"evaluate_graph": {"f1": 0.9, "shd": 1}}
            }
        )
        cache.put({"seed": 1}, entry1)
        cache.put({"seed": 2}, entry2)

    output_path = tmp_path / "summary.csv"

    result = cli_runner.invoke(
        cli,
        [
            "summarise",
            "-m",
            "f1.mean",
            "-m",
            "shd.count",
            "-i",
            str(cache_path),
            "-o",
            str(output_path),
        ],
    )

    assert result.exit_code == 0
    import csv

    with open(output_path) as f:
        reader = csv.DictReader(f)
        row = next(reader)
        assert abs(float(row["f1.mean"]) - 0.85) < 0.01
        assert row["shd.count"] == "2"


# Test summarise command with workflow cache filter.
def test_summarise_workflow_cache_with_filter(cli_runner, tmp_path):
    """Test summarise command can filter workflow cache entries."""
    from causaliq_workflow.cache import CacheEntry, WorkflowCache

    cache_path = tmp_path / "results.db"
    with WorkflowCache(str(cache_path)) as cache:
        entry1 = CacheEntry(
            metadata={
                "causaliq-analysis": {
                    "evaluate_graph": {"f1": 0.8, "status": "completed"}
                }
            }
        )
        entry2 = CacheEntry(
            metadata={
                "causaliq-analysis": {
                    "evaluate_graph": {"f1": 0.5, "status": "failed"}
                }
            }
        )
        entry3 = CacheEntry(
            metadata={
                "causaliq-analysis": {
                    "evaluate_graph": {"f1": 0.9, "status": "completed"}
                }
            }
        )
        cache.put({"seed": 1}, entry1)
        cache.put({"seed": 2}, entry2)
        cache.put({"seed": 3}, entry3)

    output_path = tmp_path / "summary.csv"

    result = cli_runner.invoke(
        cli,
        [
            "summarise",
            "-m",
            "f1.mean",
            "-m",
            "f1.count",
            "-i",
            str(cache_path),
            "-o",
            str(output_path),
            "-f",
            "status == 'completed'",
        ],
    )

    assert result.exit_code == 0
    import csv

    with open(output_path) as f:
        reader = csv.DictReader(f)
        row = next(reader)
        # Only 2 completed entries (0.8 and 0.9)
        assert row["f1.count"] == "2"
        assert abs(float(row["f1.mean"]) - 0.85) < 0.01


# Test summarise command handles invalid filter in JSON.
def test_summarise_filter_exception_json(cli_runner, tmp_path):
    """Test summarise command handles filter exception in JSON records."""
    import json

    # Records that will cause filter evaluation to fail
    input_data = [
        {"f1": 0.8, "value": "normal"},
        {"f1": 0.9, "value": "normal"},
    ]
    input_path = tmp_path / "data.json"
    with open(input_path, "w") as f:
        json.dump(input_data, f)

    output_path = tmp_path / "summary.csv"

    # Use a filter that references undefined variable
    result = cli_runner.invoke(
        cli,
        [
            "summarise",
            "-m",
            "f1.count",
            "-i",
            str(input_path),
            "-o",
            str(output_path),
            "-f",
            "undefined_var > 5",
        ],
    )

    # Command should succeed but skip records that fail filter evaluation
    assert result.exit_code == 0
    import csv

    with open(output_path) as f:
        reader = csv.DictReader(f)
        row = next(reader)
        # All records skipped due to filter exception
        assert row["f1.count"] == "0"


# Test summarise command handles write error.
def test_summarise_write_error(cli_runner, tmp_path, monkeypatch):
    """Test summarise command handles write output error."""
    import json

    input_path = tmp_path / "data.json"
    with open(input_path, "w") as f:
        json.dump([{"f1": 0.8}], f)

    # Create a directory where the output file should be
    output_path = tmp_path / "summary.csv"
    output_path.mkdir()  # Make it a directory so write fails

    result = cli_runner.invoke(
        cli,
        [
            "summarise",
            "-m",
            "f1.mean",
            "-i",
            str(input_path),
            "-o",
            str(output_path),
        ],
    )

    assert result.exit_code != 0
    assert "Failed to write output" in result.output


# Test summarise command handles cache read error.
def test_summarise_cache_read_error(cli_runner, tmp_path):
    """Test summarise command handles workflow cache read error."""
    # Create an invalid .db file
    cache_path = tmp_path / "invalid.db"
    cache_path.write_text("not a valid sqlite database")

    result = cli_runner.invoke(
        cli,
        [
            "summarise",
            "-m",
            "f1.mean",
            "-i",
            str(cache_path),
            "-o",
            str(tmp_path / "out.csv"),
        ],
    )

    assert result.exit_code != 0
    assert "Failed to read cache" in result.output


# Test _flatten_metadata helper function.
def test_flatten_metadata_nested_structure():
    """Test _flatten_metadata flattens provider/action structure."""
    from causaliq_analysis.cli import _flatten_metadata

    metadata = {
        "causaliq-analysis": {
            "evaluate_graph": {"f1": 0.9, "shd": 2},
            "other_action": {"score": 0.5},
        },
        "simple_provider": "simple_value",
    }

    flat = _flatten_metadata(metadata)

    # Simple keys from nested structure
    assert flat["f1"] == 0.9
    assert flat["shd"] == 2
    assert flat["score"] == 0.5

    # Qualified keys also present
    assert flat["causaliq-analysis.evaluate_graph.f1"] == 0.9
    assert flat["causaliq-analysis.other_action.score"] == 0.5

    # Non-dict provider value
    assert flat["simple_provider"] == "simple_value"


# Test _flatten_metadata with action data not a dict.
def test_flatten_metadata_action_not_dict():
    """Test _flatten_metadata handles non-dict action data."""
    from causaliq_analysis.cli import _flatten_metadata

    metadata = {
        "provider": {
            "action": "scalar_value",  # Not a dict
        }
    }

    flat = _flatten_metadata(metadata)
    assert flat["provider.action"] == "scalar_value"


# Test _get_nested_value helper function.
def test_get_nested_value_direct_key():
    """Test _get_nested_value with direct key access."""
    from causaliq_analysis.cli import _get_nested_value

    data = {"f1": 0.9, "precision": 0.85}
    assert _get_nested_value(data, "f1") == 0.9
    assert _get_nested_value(data, "precision") == 0.85


# Test _get_nested_value with dotted path.
def test_get_nested_value_dotted_path():
    """Test _get_nested_value with dotted path traversal."""
    from causaliq_analysis.cli import _get_nested_value

    data = {"metrics": {"f1": 0.9, "nested": {"value": 42}}}
    assert _get_nested_value(data, "metrics.f1") == 0.9
    assert _get_nested_value(data, "metrics.nested.value") == 42


# Test _get_nested_value returns None for missing keys.
def test_get_nested_value_missing_key():
    """Test _get_nested_value returns None for missing keys."""
    from causaliq_analysis.cli import _get_nested_value

    data = {"f1": 0.9}
    assert _get_nested_value(data, "missing") is None
    assert _get_nested_value(data, "a.b.c") is None


# Test summarise command handles filter exception in workflow cache.
def test_summarise_workflow_cache_filter_exception(cli_runner, tmp_path):
    """Test summarise skips cache entries that fail filter evaluation."""
    from causaliq_workflow.cache import CacheEntry, WorkflowCache

    cache_path = tmp_path / "results.db"
    with WorkflowCache(str(cache_path)) as cache:
        entry = CacheEntry(
            metadata={"causaliq-analysis": {"evaluate_graph": {"f1": 0.8}}}
        )
        cache.put({"seed": 1}, entry)

    output_path = tmp_path / "summary.csv"

    # Use a filter that references undefined variable
    result = cli_runner.invoke(
        cli,
        [
            "summarise",
            "-m",
            "f1.count",
            "-i",
            str(cache_path),
            "-o",
            str(output_path),
            "-f",
            "undefined_var > 5",
        ],
    )

    # Command should succeed but skip entries that fail filter evaluation
    assert result.exit_code == 0
    import csv

    with open(output_path) as f:
        reader = csv.DictReader(f)
        row = next(reader)
        # Entry skipped due to filter exception
        assert row["f1.count"] == "0"


# Test summarise command with terminal output using "-o -".
def test_summarise_terminal_output(cli_runner, tmp_path):
    """Test summarise command outputs to terminal with -o -."""
    import json

    input_data = [
        {"f1": 0.8, "shd": 2},
        {"f1": 0.9, "shd": 1},
    ]
    input_path = tmp_path / "data.json"
    with open(input_path, "w") as f:
        json.dump(input_data, f)

    result = cli_runner.invoke(
        cli,
        [
            "summarise",
            "-m",
            "f1.mean",
            "-m",
            "shd.count",
            "-i",
            str(input_path),
            "-o",
            "-",
        ],
    )

    assert result.exit_code == 0
    # Check formatted table output
    assert "f1.mean" in result.output
    assert "shd.count" in result.output
    assert "0.85" in result.output
    assert "2" in result.output


# Test summarise command terminal output with None values.
def test_summarise_terminal_output_with_none(cli_runner, tmp_path):
    """Test summarise terminal output formats None values correctly."""
    import json

    # Single value means SD will be None
    input_data = [{"f1": 0.8}]
    input_path = tmp_path / "data.json"
    with open(input_path, "w") as f:
        json.dump(input_data, f)

    result = cli_runner.invoke(
        cli,
        [
            "summarise",
            "-m",
            "f1.sd",
            "-i",
            str(input_path),
            "-o",
            "-",
        ],
    )

    assert result.exit_code == 0
    assert "f1.sd" in result.output
    assert "None" in result.output  # None displayed in output


# Test summarise command terminal output with empty results.
def test_summarise_terminal_output_empty(cli_runner, tmp_path):
    """Test summarise terminal output with no matching data."""
    import json

    # No matching field
    input_data = [{"other": 0.8}]
    input_path = tmp_path / "data.json"
    with open(input_path, "w") as f:
        json.dump(input_data, f)

    result = cli_runner.invoke(
        cli,
        [
            "summarise",
            "-m",
            "f1.count",
            "-i",
            str(input_path),
            "-o",
            "-",
        ],
    )

    assert result.exit_code == 0
    assert "f1.count" in result.output
    assert "0" in result.output  # count is 0


# Test _print_summary_table helper function directly.
def test_print_summary_table_formatting(capsys):
    """Test _print_summary_table formats output correctly."""
    from causaliq_analysis.cli import _print_summary_table

    results = {
        "f1.mean": 0.85,
        "f1.sd": 0.03535533905932738,
        "shd.count": 5,
        "missing.value": None,
    }

    _print_summary_table(results)

    captured = capsys.readouterr()
    output = captured.out

    # Check metric names are in header row
    assert "f1.mean" in output
    assert "f1.sd" in output
    assert "shd.count" in output
    assert "missing.value" in output

    # Check values are formatted
    assert "0.8500" in output  # 4 decimal places for float
    assert "0.0354" in output  # 4 decimal places for float
    assert "5" in output  # integers as-is

    # Check separator line exists
    assert "---" in output


# Test _print_summary_table with empty results.
def test_print_summary_table_empty_results(capsys):
    """Test _print_summary_table handles empty results dict."""
    from causaliq_analysis.cli import _print_summary_table

    _print_summary_table({})

    captured = capsys.readouterr()
    assert "No results to display" in captured.out


# Test summarise rejects duplicate --output option.
def test_summarise_duplicate_output_rejected(cli_runner, tmp_path):
    """Test summarise raises error if --output specified multiple times."""
    import json

    input_data = [{"f1": 0.8}]
    input_path = tmp_path / "data.json"
    with open(input_path, "w") as f:
        json.dump(input_data, f)

    result = cli_runner.invoke(
        cli,
        [
            "summarise",
            "-m",
            "f1.mean",
            "-i",
            str(input_path),
            "-o",
            "out1.csv",
            "-o",
            "out2.csv",
        ],
    )

    assert result.exit_code != 0
    assert "specified multiple times" in result.output


# Test summarise rejects duplicate --filter option.
def test_summarise_duplicate_filter_rejected(cli_runner, tmp_path):
    """Test summarise raises error if --filter specified multiple times."""
    import json

    input_data = [{"f1": 0.8}]
    input_path = tmp_path / "data.json"
    with open(input_path, "w") as f:
        json.dump(input_data, f)

    result = cli_runner.invoke(
        cli,
        [
            "summarise",
            "-m",
            "f1.mean",
            "-i",
            str(input_path),
            "-o",
            "out.csv",
            "-f",
            "x > 1",
            "-f",
            "y < 5",
        ],
    )

    assert result.exit_code != 0
    assert "specified multiple times" in result.output
