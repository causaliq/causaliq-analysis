"""Unit tests for merge_graphs action with mocked dependencies."""

from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

from .conftest import VALID_GRAPHML, create_mock_graphml_entry  # noqa: F401


# Test invalid weights type raises error.
def test_merge_graphs_invalid_weights_type() -> None:
    """Test that non-list, non-dict weights raises ActionExecutionError."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()

    # Create mock logger
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False

    # Create valid aggregation entries to get past input validation
    mock_entry = create_mock_graphml_entry()
    aggregation_entries: List[Dict[str, Any]] = [
        {
            "entry": mock_entry,
            "cache_path": "test.db",
            "matrix_values": {"seed": 1},
            "metadata": {},
        },
    ]

    # Weights as a string (invalid type)
    with pytest.raises(Exception) as exc_info:
        provider.run(
            action="merge_graphs",
            parameters={
                "_aggregation_entries": aggregation_entries,
                "weights": "invalid_weight_type",
            },
            mode="run",
            context=None,
            logger=mock_logger,
        )
    assert "weights must be a list or dict" in str(exc_info.value)


# Test dry-run mode with aggregation entries (line 388).
def test_merge_graphs_dry_run_aggregation_mode(capsys: Any) -> None:
    """Test dry-run mode logs aggregation count when entries provided."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()

    # Create mock logger with terminal logging enabled
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = True

    # Mock aggregation entries with _aggregation_entries parameter
    aggregation_entries: List[Dict[str, Any]] = [
        {"entry": MagicMock(), "matrix_values": {"seed": 1}},
        {"entry": MagicMock(), "matrix_values": {"seed": 2}},
    ]

    result = provider.run(
        action="merge_graphs",
        parameters={"_aggregation_entries": aggregation_entries},
        mode="dry-run",
        context=None,
        logger=mock_logger,
    )

    assert result[0] == "skipped"
    assert result[1]["aggregation_mode"] is True
    assert result[1]["num_inputs"] == 2

    # Verify it printed the aggregation message
    captured = capsys.readouterr()
    assert "Would merge graphs from 2 aggregated entries" in captured.out


# Test no graphs found error (line 457).
def test_merge_graphs_no_graphs_found() -> None:
    """Test error when no graphs found to merge."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False

    # Mock entry with no graphml objects
    mock_entry = MagicMock()
    mock_entry.object_names.return_value = []

    aggregation_entries: List[Dict[str, Any]] = [
        {
            "entry": mock_entry,
            "cache_path": "test.db",
            "matrix_values": {},
            "metadata": {},
        },
    ]

    with pytest.raises(Exception) as exc_info:
        provider.run(
            action="merge_graphs",
            parameters={"_aggregation_entries": aggregation_entries},
            mode="run",
            context=None,
            logger=mock_logger,
        )
    assert "No graphs found to merge" in str(exc_info.value)


# Test _extract_graphs_from_entries with None entry (line 577).
def test_extract_graphs_entry_is_none() -> None:
    """Test that entries with None entry object are skipped."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()

    # Entry where entry is None
    entries = [
        {"entry": None, "matrix_values": {"seed": 1}, "metadata": {}},
    ]

    graphs, metadata, source_info = provider._extract_graphs_from_entries(
        entries, log_fn=None
    )
    assert graphs == []
    assert metadata == []


# Test _extract_graphs_from_entries skips non-graphml objects (line 589).
def test_extract_graphs_skips_non_graphml_objects() -> None:
    """Test objects that are None or not graphml type are skipped."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()

    # Create mock entry with non-graphml object
    mock_obj = MagicMock()
    mock_obj.type = "json"  # Not graphml

    mock_entry = MagicMock()
    mock_entry.object_names.return_value = ["data.json"]
    mock_entry.get_object.return_value = mock_obj

    entries = [
        {
            "entry": mock_entry,
            "cache_path": "test.db",
            "matrix_values": {"seed": 42},
            "metadata": {},
        },
    ]

    graphs, metadata, source_info = provider._extract_graphs_from_entries(
        entries, log_fn=None
    )
    assert graphs == []
    assert source_info["source_count"] == 0


# Test _extract_graphs_from_entries handles None object (line 589).
def test_extract_graphs_handles_none_object() -> None:
    """Test entries returning None object are handled."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()

    mock_entry = MagicMock()
    mock_entry.object_names.return_value = ["orphan.graphml"]
    mock_entry.get_object.return_value = None

    entries = [
        {
            "entry": mock_entry,
            "cache_path": "test.db",
            "matrix_values": {"seed": 42},
            "metadata": {},
        },
    ]

    graphs, metadata, source_info = provider._extract_graphs_from_entries(
        entries, log_fn=None
    )
    assert graphs == []


# Test _extract_graphs_from_entries logs success (line 597).
def test_extract_graphs_logs_success(capsys: Any) -> None:
    """Test logging when graph is successfully loaded."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()

    mock_entry = create_mock_graphml_entry()
    entries: List[Dict[str, Any]] = [
        {
            "entry": mock_entry,
            "cache_path": "test.db",
            "matrix_values": {"seed": 42},
            "metadata": {},
        },
    ]

    graphs, metadata, source_info = provider._extract_graphs_from_entries(
        entries, log_fn=print
    )

    assert len(graphs) == 1
    captured = capsys.readouterr()
    assert "Loaded 'graph.graphml' from" in captured.out


# Test _extract_graphs_from_entries with invalid graphml (lines 597-599).
def test_extract_graphs_invalid_graphml_raises_error() -> None:
    """Test that invalid graphml content raises ActionExecutionError."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()

    # Create mock object with invalid graphml content
    mock_obj = MagicMock()
    mock_obj.type = "graphml"
    mock_obj.content = "not valid graphml"

    mock_entry = MagicMock()
    mock_entry.object_names.return_value = ["bad.graphml"]
    mock_entry.get_object.return_value = mock_obj

    entries = [
        {
            "entry": mock_entry,
            "cache_path": "test.db",
            "matrix_values": {"seed": 42},
            "metadata": {},
        },
    ]

    with pytest.raises(Exception) as exc_info:
        provider._extract_graphs_from_entries(entries, log_fn=None)
    assert "Failed to parse graph" in str(exc_info.value)


# Test _extract_graphs_from_entries logs when no graphml (lines 606-607).
def test_extract_graphs_logs_no_graphml_objects(capsys: Any) -> None:
    """Test that entries with no graphml log a message."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()

    mock_entry = MagicMock()
    mock_entry.object_names.return_value = []

    entries = [
        {
            "entry": mock_entry,
            "cache_path": "test.db",
            "matrix_values": {"seed": 99},
            "metadata": {},
        },
    ]

    graphs, metadata, source_info = provider._extract_graphs_from_entries(
        entries, log_fn=print
    )

    captured = capsys.readouterr()
    assert "has no graphml objects" in captured.out


# Test _flatten_entry_metadata with nested metadata (lines 638-648).
def test_flatten_entry_metadata_with_nested_structure() -> None:
    """Test flattening deeply nested metadata structure."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()

    matrix_values = {"seed": 42, "network": "asia"}
    metadata = {
        "causaliq-core": {
            "learn_structure": {
                "algorithm": "PC",
                "num_nodes": 10,
            },
        },
        "simple_key": "simple_value",  # Non-dict provider_data branch
    }

    result = provider._flatten_entry_metadata(matrix_values, metadata)

    # Original matrix values preserved
    assert result["seed"] == 42
    assert result["network"] == "asia"

    # Nested values flattened
    assert result["algorithm"] == "PC"
    assert result["num_nodes"] == 10

    # Qualified keys also present
    assert result["causaliq-core.learn_structure.algorithm"] == "PC"

    # Non-dict provider value handled
    assert result["simple_key"] == "simple_value"


# Test _flatten_entry_metadata with action value not dict (line 645).
def test_flatten_entry_metadata_action_not_dict() -> None:
    """Test handling when action_data is not a dict."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()

    matrix_values = {}
    metadata = {
        "provider": {
            "action": "scalar_value",  # action_data is not a dict
        },
    }

    result = provider._flatten_entry_metadata(matrix_values, metadata)
    assert result["provider.action"] == "scalar_value"


# Test _compute_weights_from_metadata with zero sum (line 697).
def test_compute_weights_zero_sum_raises_error() -> None:
    """Test error when computed weights sum to zero."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()

    graph_metadata = [
        {"algo": "PC"},
        {"algo": "GES"},
    ]

    # Weight spec where values explicitly set to 0
    weight_spec = {"algo": {"PC": 0.0, "GES": 0.0}}

    with pytest.raises(Exception) as exc_info:
        provider._compute_weights_from_metadata(
            graph_metadata, weight_spec, log_fn=None
        )
    assert "Computed weights sum to zero" in str(exc_info.value)


# Test _compute_weights_from_metadata logs computed weights (line 705).
def test_compute_weights_logs_values(capsys: Any) -> None:
    """Test that computed weights are logged with log_fn."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()

    graph_metadata = [
        {"algo": "PC"},
        {"algo": "GES"},
    ]

    weight_spec = {"algo": {"PC": 2.0, "GES": 1.0}}

    provider._compute_weights_from_metadata(
        graph_metadata, weight_spec, log_fn=print
    )

    captured = capsys.readouterr()
    assert "Computed weights from metadata" in captured.out
    assert "raw=" in captured.out
    assert "normalised=" in captured.out


# Test _read_graphs_from_cache with valid cache (lines 731-787).
def test_read_graphs_from_cache_success(capsys: Any) -> None:
    """Test successful reading of graphs from cache."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()

    # Create mock graphml content (valid minimal graphml)
    graphml_content = """<?xml version="1.0" encoding="UTF-8"?>
<graphml xmlns="http://graphml.graphdrawing.org/xmlns">
  <graph id="G" edgedefault="directed">
    <node id="A"/>
    <node id="B"/>
    <edge source="A" target="B"/>
  </graph>
</graphml>"""

    # Create mock object
    mock_obj = MagicMock()
    mock_obj.type = "graphml"
    mock_obj.content = graphml_content

    # Create mock entry
    mock_entry = MagicMock()
    mock_entry.object_names.return_value = ["graph.graphml"]
    mock_entry.get_object.return_value = mock_obj

    # Create mock cache
    mock_cache = MagicMock()
    mock_cache.list_entries.return_value = [
        {"matrix_values": {"seed": 1}},
        {"matrix_values": {"seed": 2}},
    ]
    mock_cache.get.return_value = mock_entry
    mock_cache.__enter__ = MagicMock(return_value=mock_cache)
    mock_cache.__exit__ = MagicMock(return_value=False)

    with patch(
        "causaliq_workflow.cache.WorkflowCache",
        return_value=mock_cache,
    ):
        graphs, entries_count = provider._read_graphs_from_cache(
            "test.db", log_fn=print
        )

    assert len(graphs) == 2
    assert entries_count == 2

    captured = capsys.readouterr()
    assert "Found 2 entries in cache" in captured.out


# Test _read_graphs_from_cache with FileNotFoundError (line 780).
def test_read_graphs_from_cache_file_not_found() -> None:
    """Test FileNotFoundError raises appropriate ActionExecutionError."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()

    with patch(
        "causaliq_workflow.cache.WorkflowCache",
        side_effect=FileNotFoundError("not found"),
    ):
        with pytest.raises(Exception) as exc_info:
            provider._read_graphs_from_cache("nonexistent.db", log_fn=None)
    assert "Cache file not found" in str(exc_info.value)


# Test _read_graphs_from_cache with generic error (lines 782-785).
def test_read_graphs_from_cache_generic_error() -> None:
    """Test generic exception wrapping in cache read."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()

    with patch(
        "causaliq_workflow.cache.WorkflowCache",
        side_effect=RuntimeError("Database corrupt"),
    ):
        with pytest.raises(Exception) as exc_info:
            provider._read_graphs_from_cache("bad.db", log_fn=None)
    assert "Failed to read from cache" in str(exc_info.value)


# Test _read_graphs_from_cache with entry returning None (line 751).
def test_read_graphs_from_cache_entry_is_none() -> None:
    """Test cache.get returning None is handled."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()

    # Create mock cache that returns None for get()
    mock_cache = MagicMock()
    mock_cache.list_entries.return_value = [{"matrix_values": {"seed": 1}}]
    mock_cache.get.return_value = None
    mock_cache.__enter__ = MagicMock(return_value=mock_cache)
    mock_cache.__exit__ = MagicMock(return_value=False)

    with patch(
        "causaliq_workflow.cache.WorkflowCache",
        return_value=mock_cache,
    ):
        graphs, entries_count = provider._read_graphs_from_cache(
            "test.db", log_fn=None
        )

    assert graphs == []
    assert entries_count == 0


# Test _read_graphs_from_cache with invalid graphml (lines 768-772).
def test_read_graphs_from_cache_invalid_graphml() -> None:
    """Test invalid graphml in cache raises ActionExecutionError."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()

    mock_obj = MagicMock()
    mock_obj.type = "graphml"
    mock_obj.content = "not valid xml"

    mock_entry = MagicMock()
    mock_entry.object_names.return_value = ["bad.graphml"]
    mock_entry.get_object.return_value = mock_obj

    mock_cache = MagicMock()
    mock_cache.list_entries.return_value = [{"matrix_values": {"seed": 1}}]
    mock_cache.get.return_value = mock_entry
    mock_cache.__enter__ = MagicMock(return_value=mock_cache)
    mock_cache.__exit__ = MagicMock(return_value=False)

    with patch(
        "causaliq_workflow.cache.WorkflowCache",
        return_value=mock_cache,
    ):
        with pytest.raises(Exception) as exc_info:
            provider._read_graphs_from_cache("test.db", log_fn=None)
    assert "Failed to parse graph" in str(exc_info.value)


# Test _read_graphs_from_cache logs no graphml objects (line 775-776).
def test_read_graphs_from_cache_logs_no_graphml(capsys: Any) -> None:
    """Test logging when entry has no graphml objects."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()

    mock_entry = MagicMock()
    mock_entry.object_names.return_value = []

    mock_cache = MagicMock()
    mock_cache.list_entries.return_value = [{"matrix_values": {"seed": 1}}]
    mock_cache.get.return_value = mock_entry
    mock_cache.__enter__ = MagicMock(return_value=mock_cache)
    mock_cache.__exit__ = MagicMock(return_value=False)

    with patch(
        "causaliq_workflow.cache.WorkflowCache",
        return_value=mock_cache,
    ):
        graphs, entries_count = provider._read_graphs_from_cache(
            "test.db", log_fn=print
        )

    captured = capsys.readouterr()
    assert "has no graphml objects" in captured.out


# Test _read_graphs_from_cache skips non-graphml objects (line 757-758).
def test_read_graphs_from_cache_skips_non_graphml() -> None:
    """Test objects with type != graphml are skipped."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()

    mock_obj = MagicMock()
    mock_obj.type = "json"  # Not graphml

    mock_entry = MagicMock()
    mock_entry.object_names.return_value = ["data.json"]
    mock_entry.get_object.return_value = mock_obj

    mock_cache = MagicMock()
    mock_cache.list_entries.return_value = [{"matrix_values": {"seed": 1}}]
    mock_cache.get.return_value = mock_entry
    mock_cache.__enter__ = MagicMock(return_value=mock_cache)
    mock_cache.__exit__ = MagicMock(return_value=False)

    with patch(
        "causaliq_workflow.cache.WorkflowCache",
        return_value=mock_cache,
    ):
        graphs, entries_count = provider._read_graphs_from_cache(
            "test.db", log_fn=None
        )

    assert graphs == []
    assert entries_count == 0


# Test merge_graphs with cache input and entries read (lines 436-440, 454).
def test_merge_graphs_from_cache_input() -> None:
    """Test merge_graphs reading from .db cache file."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False

    # Create valid graphml content
    graphml_content = """<?xml version="1.0" encoding="UTF-8"?>
<graphml xmlns="http://graphml.graphdrawing.org/xmlns">
  <graph id="G" edgedefault="directed">
    <node id="A"/>
    <node id="B"/>
    <edge source="A" target="B"/>
  </graph>
</graphml>"""

    mock_obj = MagicMock()
    mock_obj.type = "graphml"
    mock_obj.content = graphml_content

    mock_entry = MagicMock()
    mock_entry.object_names.return_value = ["graph.graphml"]
    mock_entry.get_object.return_value = mock_obj

    mock_cache = MagicMock()
    mock_cache.list_entries.return_value = [{"matrix_values": {"seed": 1}}]
    mock_cache.get.return_value = mock_entry
    mock_cache.__enter__ = MagicMock(return_value=mock_cache)
    mock_cache.__exit__ = MagicMock(return_value=False)

    with patch(
        "causaliq_workflow.cache.WorkflowCache",
        return_value=mock_cache,
    ):
        result = provider.run(
            action="merge_graphs",
            parameters={"input": ["test.db"]},
            mode="run",
            context=None,
            logger=mock_logger,
        )

    assert result[0] == "success"
    assert result[1]["cache_entries_read"] == 1


# Test metadata-driven weights without aggregation mode (line 470-472).
def test_merge_graphs_dict_weights_without_aggregation() -> None:
    """Test error when dict weights used without aggregation mode."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False

    # Use valid graphml content
    graphml_content = """<?xml version="1.0" encoding="UTF-8"?>
<graphml xmlns="http://graphml.graphdrawing.org/xmlns">
  <graph id="G" edgedefault="directed">
    <node id="A"/>
    <node id="B"/>
    <edge source="A" target="B"/>
  </graph>
</graphml>"""

    mock_obj = MagicMock()
    mock_obj.type = "graphml"
    mock_obj.content = graphml_content

    mock_entry = MagicMock()
    mock_entry.object_names.return_value = ["graph.graphml"]
    mock_entry.get_object.return_value = mock_obj

    mock_cache = MagicMock()
    mock_cache.list_entries.return_value = [{"matrix_values": {"seed": 1}}]
    mock_cache.get.return_value = mock_entry
    mock_cache.__enter__ = MagicMock(return_value=mock_cache)
    mock_cache.__exit__ = MagicMock(return_value=False)

    with patch(
        "causaliq_workflow.cache.WorkflowCache",
        return_value=mock_cache,
    ):
        with pytest.raises(Exception) as exc_info:
            provider.run(
                action="merge_graphs",
                parameters={
                    "input": ["test.db"],
                    "weights": {"algo": {"PC": 1.0}},
                },
                mode="run",
                context=None,
                logger=mock_logger,
            )
    assert "Metadata-driven weights require aggregation" in str(exc_info.value)


# Test empty aggregation entries raises error (no fallback to direct mode).
def test_merge_graphs_empty_aggregation_entries_error() -> None:
    """Test that empty aggregation entries raises error, not fallback."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False

    # Empty list of aggregation entries (no matches for matrix values)
    aggregation_entries: List[Dict[str, Any]] = []

    with pytest.raises(Exception) as exc_info:
        provider.run(
            action="merge_graphs",
            parameters={"_aggregation_entries": aggregation_entries},
            mode="run",
            context=None,
            logger=mock_logger,
        )

    # Should get clear error about no matches, not fall back to direct mode
    assert "No cache entries matched" in str(exc_info.value)


# Test aggregation mode is detected from non-None entries even if empty.
def test_merge_graphs_aggregation_mode_detected_from_empty_list() -> None:
    """Test aggregation mode is triggered by empty list (not None)."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = True

    # Empty list is still aggregation mode (vs None for direct mode)
    aggregation_entries: List[Dict[str, Any]] = []

    result = provider.run(
        action="merge_graphs",
        parameters={"_aggregation_entries": aggregation_entries},
        mode="dry-run",
        context=None,
        logger=mock_logger,
    )

    # Dry-run should indicate aggregation mode with 0 entries
    assert result[0] == "skipped"
    assert result[1]["aggregation_mode"] is True
    assert result[1]["num_inputs"] == 0
