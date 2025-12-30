# Enumerations describing changes made to a graph
# Will be migrated to causaliq_core.graph

from enum import Enum

from causaliq_core.utils import EnumWithAttrs


class GraphActionDetail(Enum):  # details that can be provided on a Trace entry
    ARC = ("arc", tuple)  # Arc that was changed
    DELTA = ("delta/score", float)  # Delta as result of arc changed
    ACTIVITY_2 = ("activity_2", str)  # Arc change with second highest delta
    ARC_2 = ("arc_2", tuple)  # Arc changed in second highest delta
    DELTA_2 = ("delta_2", float)  # second highest delta
    MIN_N = ("min_N", float)  # minimum count in contingency tables' cells
    MEAN_N = ("mean_N", float)  # mean count in contingency tables' cells
    MAX_N = ("max_N", float)  # max count in contingency tables' cells
    LT5 = ("lt5", float)  # number of cells with count <5 in contingency tables
    FPA = ("free_params", float)  # number of free params in contingency tables
    KNOWLEDGE = ("knowledge", tuple)  # Knowledge used in iteration
    BLOCKED = ("blocked", list)  # list of blocked changes


# for PC delete in p-value or use score? some of MIN_N to FPA still relevant?
# need new field for conditioning set
# could arc and arc2 to defined v-structure


class GraphAction(EnumWithAttrs):
    """
    Defines set of Activities than can recorded in trace

    :ivar str value: short string code for activity
    :ivar str label: human-readable label for activity
    :ivar set mandatory: mandatory items for activity
    :ivar int priority: priority order for this activity
    """

    INIT = "init", "initialise", {GraphActionDetail.DELTA}, 0
    ADD = "add", "add arc", {GraphActionDetail.ARC, GraphActionDetail.DELTA}, 3
    DEL = (
        "delete",
        "delete arc",
        {GraphActionDetail.ARC, GraphActionDetail.DELTA},
        2,
    )
    REV = (
        "reverse",
        "reverse arc",
        {GraphActionDetail.ARC, GraphActionDetail.DELTA},
        1,
    )
    STOP = "stop", "stop search", {GraphActionDetail.DELTA}, 4
    PAUSE = "pause", "pause search", {GraphActionDetail.DELTA}, 6
    NONE = (
        "none",
        "no change",
        {GraphActionDetail.ARC, GraphActionDetail.DELTA},
        5,
    )

    # ignore the first param since it's already set by __new__
    def __init__(self, _: str, label: str, mandatory: set, priority: int):
        self._label_ = label
        self._mandatory_ = mandatory
        self._priority_ = priority

    # this makes sure that mandatory is read-only
    @property
    def mandatory(self) -> set:
        return self._mandatory_.copy()

    # this makes sure that priority is read-only
    @property
    def priority(self) -> int:
        return self._priority_


# for PC delete used for removing arc, v-struct needed for v-struct,
# and orientate for arc orientation
