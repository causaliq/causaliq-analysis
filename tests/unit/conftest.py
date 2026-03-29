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

# Valid minimal PDG graphml with probability attributes.
VALID_PDG_GRAPHML = """<?xml version="1.0" encoding="UTF-8"?>
<graphml xmlns="http://graphml.graphdrawing.org/xmlns">
  <key id="p_forward" for="edge" attr.type="double"/>
  <key id="p_backward" for="edge" attr.type="double"/>
  <key id="p_undirected" for="edge" attr.type="double"/>
  <key id="p_none" for="edge" attr.type="double"/>
  <graph edgedefault="undirected">
    <node id="A"/>
    <node id="B"/>
    <edge source="A" target="B">
      <data key="p_forward">0.8</data>
      <data key="p_backward">0.1</data>
      <data key="p_undirected">0.05</data>
      <data key="p_none">0.05</data>
    </edge>
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
