"""Shared fixtures and helpers for unit tests of workflow actions."""

from unittest.mock import MagicMock

import pytest

# Valid minimal graphml for testing.
VALID_GRAPHML = """<?xml version="1.0" encoding="UTF-8"?>
<graphml xmlns="http://graphml.graphdrawing.org/xmlns">
  <graph id="G" edgedefault="directed">
    <node id="A"/>
    <node id="B"/>
    <edge source="A" target="B"/>
  </graph>
</graphml>"""


def create_mock_graphml_entry() -> MagicMock:
    """Create mock entry with valid graphml object."""
    mock_obj = MagicMock()
    mock_obj.type = "dag"
    mock_obj.format = "graphml"
    mock_obj.content = VALID_GRAPHML

    mock_entry = MagicMock()
    mock_entry.object_types.return_value = ["dag"]
    mock_entry.get_object.return_value = mock_obj
    return mock_entry


@pytest.fixture
def mock_graphml_entry() -> MagicMock:
    """Fixture providing a mock entry with valid graphml object."""
    return create_mock_graphml_entry()


@pytest.fixture
def valid_graphml() -> str:
    """Fixture providing valid graphml content for testing."""
    return VALID_GRAPHML
