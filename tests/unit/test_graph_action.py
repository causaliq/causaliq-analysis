"""Unit tests for graph module"""

import pytest

from causaliq_analysis.graph import GraphAction, GraphActionDetail


# Test GraphActionDetail enum has all expected members
def test_graph_action_detail_members():
    expected_members = [
        "ARC",
        "DELTA",
        "ACTIVITY_2",
        "ARC_2",
        "DELTA_2",
        "MIN_N",
        "MEAN_N",
        "MAX_N",
        "LT5",
        "FPA",
        "KNOWLEDGE",
        "BLOCKED",
    ]
    actual_members = [member.name for member in GraphActionDetail]
    assert len(actual_members) == len(expected_members)
    for member in expected_members:
        assert member in actual_members


# Test GraphActionDetail ARC has correct value and type
def test_graph_action_detail_arc():
    detail = GraphActionDetail.ARC
    assert detail.value == ("arc", tuple)
    assert detail.name == "ARC"


# Test GraphActionDetail DELTA has correct value and type
def test_graph_action_detail_delta():
    detail = GraphActionDetail.DELTA
    assert detail.value == ("delta/score", float)
    assert detail.name == "DELTA"


# Test GraphActionDetail ACTIVITY_2 has correct value and type
def test_graph_action_detail_activity_2():
    detail = GraphActionDetail.ACTIVITY_2
    assert detail.value == ("activity_2", str)
    assert detail.name == "ACTIVITY_2"


# Test GraphActionDetail ARC_2 has correct value and type
def test_graph_action_detail_arc_2():
    detail = GraphActionDetail.ARC_2
    assert detail.value == ("arc_2", tuple)
    assert detail.name == "ARC_2"


# Test GraphActionDetail DELTA_2 has correct value and type
def test_graph_action_detail_delta_2():
    detail = GraphActionDetail.DELTA_2
    assert detail.value == ("delta_2", float)
    assert detail.name == "DELTA_2"


# Test GraphActionDetail MIN_N has correct value and type
def test_graph_action_detail_min_n():
    detail = GraphActionDetail.MIN_N
    assert detail.value == ("min_N", float)
    assert detail.name == "MIN_N"


# Test GraphActionDetail MEAN_N has correct value and type
def test_graph_action_detail_mean_n():
    detail = GraphActionDetail.MEAN_N
    assert detail.value == ("mean_N", float)
    assert detail.name == "MEAN_N"


# Test GraphActionDetail MAX_N has correct value and type
def test_graph_action_detail_max_n():
    detail = GraphActionDetail.MAX_N
    assert detail.value == ("max_N", float)
    assert detail.name == "MAX_N"


# Test GraphActionDetail LT5 has correct value and type
def test_graph_action_detail_lt5():
    detail = GraphActionDetail.LT5
    assert detail.value == ("lt5", float)
    assert detail.name == "LT5"


# Test GraphActionDetail FPA has correct value and type
def test_graph_action_detail_fpa():
    detail = GraphActionDetail.FPA
    assert detail.value == ("free_params", float)
    assert detail.name == "FPA"


# Test GraphActionDetail KNOWLEDGE has correct value and type
def test_graph_action_detail_knowledge():
    detail = GraphActionDetail.KNOWLEDGE
    assert detail.value == ("knowledge", tuple)
    assert detail.name == "KNOWLEDGE"


# Test GraphActionDetail BLOCKED has correct value and type
def test_graph_action_detail_blocked():
    detail = GraphActionDetail.BLOCKED
    assert detail.value == ("blocked", list)
    assert detail.name == "BLOCKED"


# Test GraphAction enum has all expected members
def test_graph_action_members():
    expected_members = ["INIT", "ADD", "DEL", "REV", "STOP", "PAUSE", "NONE"]
    actual_members = [member.name for member in GraphAction]
    assert len(actual_members) == len(expected_members)
    for member in expected_members:
        assert member in actual_members


# Test GraphAction INIT has correct properties
def test_graph_action_init():
    action = GraphAction.INIT
    assert action.value == "init"
    assert action._label_ == "initialise"
    assert action.mandatory == {GraphActionDetail.DELTA}
    assert action.priority == 0


# Test GraphAction ADD has correct properties
def test_graph_action_add():
    action = GraphAction.ADD
    assert action.value == "add"
    assert action._label_ == "add arc"
    assert action.mandatory == {GraphActionDetail.ARC, GraphActionDetail.DELTA}
    assert action.priority == 3


# Test GraphAction DEL has correct properties
def test_graph_action_del():
    action = GraphAction.DEL
    assert action.value == "delete"
    assert action._label_ == "delete arc"
    assert action.mandatory == {GraphActionDetail.ARC, GraphActionDetail.DELTA}
    assert action.priority == 2


# Test GraphAction REV has correct properties
def test_graph_action_rev():
    action = GraphAction.REV
    assert action.value == "reverse"
    assert action._label_ == "reverse arc"
    assert action.mandatory == {GraphActionDetail.ARC, GraphActionDetail.DELTA}
    assert action.priority == 1


# Test GraphAction STOP has correct properties
def test_graph_action_stop():
    action = GraphAction.STOP
    assert action.value == "stop"
    assert action._label_ == "stop search"
    assert action.mandatory == {GraphActionDetail.DELTA}
    assert action.priority == 4


# Test GraphAction PAUSE has correct properties
def test_graph_action_pause():
    action = GraphAction.PAUSE
    assert action.value == "pause"
    assert action._label_ == "pause search"
    assert action.mandatory == {GraphActionDetail.DELTA}
    assert action.priority == 6


# Test GraphAction NONE has correct properties
def test_graph_action_none():
    action = GraphAction.NONE
    assert action.value == "none"
    assert action._label_ == "no change"
    assert action.mandatory == {GraphActionDetail.ARC, GraphActionDetail.DELTA}
    assert action.priority == 5


# Test GraphAction mandatory property is read-only
def test_graph_action_mandatory_read_only():
    action = GraphAction.ADD
    original_mandatory = action.mandatory

    # Verify we get the expected set
    assert original_mandatory == {
        GraphActionDetail.ARC,
        GraphActionDetail.DELTA,
    }

    # Verify the property returns a set (not the internal _mandatory_)
    assert isinstance(action.mandatory, set)

    # Test that modifying the returned set doesn't affect the original
    returned_set = action.mandatory
    returned_set.add(GraphActionDetail.BLOCKED)
    assert action.mandatory == original_mandatory  # Should be unchanged


# Test GraphAction priority property is read-only
def test_graph_action_priority_read_only():
    action = GraphAction.ADD
    original_priority = action.priority

    # Verify we get the expected priority
    assert original_priority == 3

    # Verify the property returns an int
    assert isinstance(action.priority, int)


# Test GraphAction priority ordering
def test_graph_action_priority_ordering():
    priorities = [(action.priority, action.name) for action in GraphAction]
    priorities.sort()

    expected_order = [
        (0, "INIT"),
        (1, "REV"),
        (2, "DEL"),
        (3, "ADD"),
        (4, "STOP"),
        (5, "NONE"),
        (6, "PAUSE"),
    ]

    assert priorities == expected_order


# Test GraphAction can be used in comparisons based on priority
def test_graph_action_priority_comparison():
    assert GraphAction.INIT.priority < GraphAction.REV.priority
    assert GraphAction.REV.priority < GraphAction.DEL.priority
    assert GraphAction.DEL.priority < GraphAction.ADD.priority
    assert GraphAction.ADD.priority < GraphAction.STOP.priority
    assert GraphAction.STOP.priority < GraphAction.NONE.priority
    assert GraphAction.NONE.priority < GraphAction.PAUSE.priority


# Test GraphAction enum values are unique
def test_graph_action_values_unique():
    values = [action.value for action in GraphAction]
    assert len(values) == len(set(values))  # All values should be unique


# Test GraphAction labels are unique
def test_graph_action_labels_unique():
    labels = [action._label_ for action in GraphAction]
    assert len(labels) == len(set(labels))  # All labels should be unique


# Test GraphAction mandatory sets contain only GraphActionDetail members
def test_graph_action_mandatory_contains_valid_details():
    for action in GraphAction:
        for detail in action.mandatory:
            assert isinstance(detail, GraphActionDetail)


# Test GraphAction can be retrieved by value
def test_graph_action_by_value():
    assert GraphAction("init") == GraphAction.INIT
    assert GraphAction("add") == GraphAction.ADD
    assert GraphAction("delete") == GraphAction.DEL
    assert GraphAction("reverse") == GraphAction.REV
    assert GraphAction("stop") == GraphAction.STOP
    assert GraphAction("pause") == GraphAction.PAUSE
    assert GraphAction("none") == GraphAction.NONE


# Test invalid GraphAction value raises ValueError
def test_graph_action_invalid_value():
    with pytest.raises(ValueError):
        GraphAction("invalid_action")


# Test GraphActionDetail can be retrieved by name
def test_graph_action_detail_by_name():
    assert GraphActionDetail["ARC"] == GraphActionDetail.ARC
    assert GraphActionDetail["DELTA"] == GraphActionDetail.DELTA
    assert GraphActionDetail["BLOCKED"] == GraphActionDetail.BLOCKED


# Test invalid GraphActionDetail name raises KeyError
def test_graph_action_detail_invalid_name():
    with pytest.raises(KeyError):
        GraphActionDetail["INVALID_DETAIL"]
