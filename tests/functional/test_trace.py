#   Test the strucure learning Trace class

from os import remove
from os.path import exists
from shutil import rmtree
from time import sleep

import pytest
from causaliq_core import SOFTWARE_VERSION
from causaliq_core.utils.random import Randomise

import tests.fixtures.example_dags as ex_dag
from causaliq_analysis.graph import GraphAction, GraphActionDetail
from causaliq_analysis.trace import Trace

TESTDATA_DIR = EXPTS_DIR = "tests/data/functional/"


# Constructor bad arg types
def test_trace_constructor_type_error1():
    with pytest.raises(TypeError):
        Trace(True)
    with pytest.raises(TypeError):
        Trace(3.17)


# Bad context value types
def test_trace_constructor_type_error2():
    with pytest.raises(TypeError):
        Trace({"N": "should be int"})


# Bad context value types
def test_trace_constructor_type_error3():
    with pytest.raises(TypeError):
        Trace({"id": 32})
    with pytest.raises(TypeError):
        Trace({"id": "trace/hc", "in": {}})
    with pytest.raises(TypeError):
        Trace({"algorithm": "HC", "id": True})
    with pytest.raises(TypeError):
        Trace({"algorithm": True})
    with pytest.raises(TypeError):
        Trace({"in": 40.3})


# Bad context value types
def test_trace_constructor_type_error4():
    with pytest.raises(TypeError):
        Trace({"params": 32})


# Bad context score types
def test_trace_constructor_type_error5():
    with pytest.raises(TypeError):
        Trace({"score": 10})
    with pytest.raises(TypeError):
        Trace({"score": "invalid"})
    with pytest.raises(TypeError):
        Trace({"score": [-10.1]})


# Bad context var_order type
def test_trace_constructor_type_error6():
    with pytest.raises(TypeError):
        Trace({"var_order": {"A", "B"}})
    with pytest.raises(TypeError):
        Trace({"score": "invalid"})
    with pytest.raises(TypeError):
        Trace({"score": [-10.1]})


# Bad context randomise type
def test_trace_constructor_type_error7():
    with pytest.raises(TypeError):
        Trace({"randomise": True})
    with pytest.raises(TypeError):
        Trace({"randomise": "order"})
    with pytest.raises(TypeError):
        Trace({"randomise": {-10.1}})


# Bad randomise elements type
def test_trace_constructor_type_error8():
    with pytest.raises(TypeError):
        Trace({"randomise": [2]})
    with pytest.raises(TypeError):
        Trace({"randomise": [True, False]})
    with pytest.raises(TypeError):
        Trace({"randomise": ["a", "b"]})
    with pytest.raises(TypeError):
        Trace({"randomise": [Randomise.ORDER, "bad"]})


# Bad context keys
def test_trace_constructor_value_error1():
    with pytest.raises(ValueError):
        Trace({"invalid": 33})
    with pytest.raises(ValueError):
        Trace({"N": 100, "invalid": 33})


# Bad id values
def test_trace_constructor_value_error2():
    with pytest.raises(ValueError):
        Trace({"id": ""})
    with pytest.raises(ValueError):
        Trace({"id": "hi/ee/ww?"})


# More bad id values
def test_trace_constructor_value_error3():
    with pytest.raises(ValueError):
        Trace({"id": "a//b"})
    with pytest.raises(ValueError):
        Trace({"id": "/."})
    with pytest.raises(ValueError):
        Trace({"id": "aa/./bb"})
    with pytest.raises(ValueError):
        Trace({"id": "aa/../bb"})
    with pytest.raises(ValueError):
        Trace({"id": "aa/bb  cc.test1"})
    with pytest.raises(ValueError):
        Trace({"id": "aa/bb--1"})
    with pytest.raises(ValueError):
        Trace({"id": "__"})
    with pytest.raises(ValueError):
        Trace({"id": "  "})


# More bad id values
def test_trace_constructor_value_error4():
    with pytest.raises(ValueError):
        Trace({"id": " a"})
    with pytest.raises(ValueError):
        Trace({"id": " "})
    with pytest.raises(ValueError):
        Trace({"id": "a "})
    with pytest.raises(ValueError):
        Trace({"id": ".a"})
    with pytest.raises(ValueError):
        Trace({"id": "_"})
    with pytest.raises(ValueError):
        Trace({"id": "- "})


# Constructor called with no arg
def test_trace_constructor_1_ok():
    trace = Trace()
    assert trace.context["software_version"] == SOFTWARE_VERSION


# Constructor called with empty dict
def test_trace_constructor_2_ok():
    trace = Trace({})
    assert trace.context["software_version"] == SOFTWARE_VERSION
    assert set(trace.context.keys()) == {
        "cpu",
        "os",
        "python",
        "ram",
        "software_version",
    }


# Constructor called with dict
def test_trace_constructor_3_ok():
    trace = Trace({"N": 250, "id": "my expt"})
    assert trace.context["software_version"] == SOFTWARE_VERSION
    assert trace.context["N"] == 250
    assert trace.context["id"] == "my expt"
    assert set(trace.context.keys()) == {
        "cpu",
        "os",
        "python",
        "ram",
        "software_version",
        "N",
        "id",
    }


# Constructor called with dict
def test_trace_constructor_4_ok():
    trace = Trace(
        {
            "N": 10,
            "id": "another expt",
            "algorithm": "PC",
            "in": "discrete/small/asia.dsc",
            "params": {"alpha": 0.02},
        }
    )
    assert trace.context["software_version"] == SOFTWARE_VERSION
    assert trace.context["N"] == 10
    assert trace.context["id"] == "another expt"
    assert trace.context["algorithm"] == "PC"
    assert trace.context["in"] == "discrete/small/asia.dsc"
    assert trace.context["params"] == {"alpha": 0.02}
    assert set(trace.context.keys()) == {
        "cpu",
        "os",
        "python",
        "ram",
        "in",
        "software_version",
        "N",
        "id",
        "params",
        "algorithm",
    }


# Constructor called with dict incl. know
def test_trace_constructor_5_ok():
    trace = Trace(
        {
            "N": 10,
            "id": "another expt",
            "algorithm": "PC",
            "in": "discrete/small/asia.dsc",
            "params": {"alpha": 0.02},
            "knowledge": 'Ruleset "Swap equivalent add" with limit 5',
        }
    )
    assert set(trace.context.keys()) == {
        "cpu",
        "os",
        "python",
        "ram",
        "in",
        "software_version",
        "N",
        "id",
        "params",
        "algorithm",
        "knowledge",
    }
    assert trace.context["software_version"] == SOFTWARE_VERSION
    assert trace.context["N"] == 10
    assert trace.context["id"] == "another expt"
    assert trace.context["algorithm"] == "PC"
    assert trace.context["in"] == "discrete/small/asia.dsc"
    assert trace.context["params"] == {"alpha": 0.02}
    assert trace.context["knowledge"] == (
        'Ruleset "Swap equivalent add"' + " with limit 5"
    )


# Order randomisation with list
def test_trace_constructor_6_ok():
    trace = Trace(
        {
            "N": 10,
            "id": "another expt",
            "algorithm": "PC",
            "in": "discrete/small/asia.dsc",
            "params": {"alpha": 0.02},
            "randomise": [Randomise.ORDER],
            "var_order": [
                "xray",
                "tub",
                "dysp",
                "either",
                "asia",
                "lung",
                "smoke",
                "bronc",
            ],
        }
    )
    assert set(trace.context.keys()) == {
        "cpu",
        "os",
        "python",
        "ram",
        "in",
        "software_version",
        "N",
        "id",
        "params",
        "algorithm",
        "var_order",
        "randomise",
    }
    assert trace.context["software_version"] == SOFTWARE_VERSION
    assert trace.context["N"] == 10
    assert trace.context["id"] == "another expt"
    assert trace.context["algorithm"] == "PC"
    assert trace.context["in"] == "discrete/small/asia.dsc"
    assert trace.context["params"] == {"alpha": 0.02}
    assert trace.context["var_order"] == [
        "xray",
        "tub",
        "dysp",
        "either",
        "asia",
        "lung",
        "smoke",
        "bronc",
    ]
    assert trace.context["randomise"] == [Randomise.ORDER]


# Order randomisation with single
def test_trace_constructor_7_ok():
    trace = Trace(
        {
            "N": 10,
            "id": "another expt",
            "algorithm": "PC",
            "in": "discrete/small/asia.dsc",
            "params": {"alpha": 0.02},
            "randomise": Randomise.ORDER,
            "var_order": [
                "xray",
                "tub",
                "dysp",
                "either",
                "asia",
                "lung",
                "smoke",
                "bronc",
            ],
        }
    )
    assert set(trace.context.keys()) == {
        "cpu",
        "os",
        "python",
        "ram",
        "in",
        "software_version",
        "N",
        "id",
        "params",
        "algorithm",
        "var_order",
        "randomise",
    }
    assert trace.context["software_version"] == SOFTWARE_VERSION
    assert trace.context["N"] == 10
    assert trace.context["id"] == "another expt"
    assert trace.context["algorithm"] == "PC"
    assert trace.context["in"] == "discrete/small/asia.dsc"
    assert trace.context["params"] == {"alpha": 0.02}
    assert trace.context["var_order"] == [
        "xray",
        "tub",
        "dysp",
        "either",
        "asia",
        "lung",
        "smoke",
        "bronc",
    ]
    assert trace.context["randomise"] == Randomise.ORDER


# Order randomisation with list
def test_trace_constructor_8_ok():
    trace = Trace(
        {
            "N": 10,
            "id": "another expt",
            "algorithm": "PC",
            "in": "discrete/small/asia.dsc",
            "params": {"alpha": 0.02},
            "randomise": [Randomise.ORDER, Randomise.KNOWLEDGE],
            "var_order": [
                "xray",
                "tub",
                "dysp",
                "either",
                "asia",
                "lung",
                "smoke",
                "bronc",
            ],
        }
    )
    assert set(trace.context.keys()) == {
        "cpu",
        "os",
        "python",
        "ram",
        "in",
        "software_version",
        "N",
        "id",
        "params",
        "algorithm",
        "var_order",
        "randomise",
    }
    assert trace.context["software_version"] == SOFTWARE_VERSION
    assert trace.context["N"] == 10
    assert trace.context["id"] == "another expt"
    assert trace.context["algorithm"] == "PC"
    assert trace.context["in"] == "discrete/small/asia.dsc"
    assert trace.context["params"] == {"alpha": 0.02}
    assert trace.context["var_order"] == [
        "xray",
        "tub",
        "dysp",
        "either",
        "asia",
        "lung",
        "smoke",
        "bronc",
    ]
    assert trace.context["randomise"] == [Randomise.ORDER, Randomise.KNOWLEDGE]


# Score
def test_trace_constructor_9_ok():
    trace = Trace(
        {
            "N": 10,
            "id": "another expt",
            "algorithm": "HC",
            "in": "discrete/small/asia.dsc",
            "params": {"score": "bic", "k": 1},
            "score": -99.99,
        }
    )
    assert set(trace.context.keys()) == {
        "cpu",
        "os",
        "python",
        "ram",
        "in",
        "software_version",
        "N",
        "id",
        "params",
        "algorithm",
        "score",
    }
    assert trace.context["software_version"] == SOFTWARE_VERSION
    assert trace.context["N"] == 10
    assert trace.context["id"] == "another expt"
    assert trace.context["algorithm"] == "HC"
    assert trace.context["in"] == "discrete/small/asia.dsc"
    assert trace.context["params"] == {"score": "bic", "k": 1}
    assert trace.context["score"] == -99.99


# add bad Activity Type
def test_trace_add_type_error1():
    trace = Trace()
    with pytest.raises(TypeError):
        trace.add()
    with pytest.raises(TypeError):
        trace.add(True)
    with pytest.raises(TypeError):
        trace.add("bad arg type")


# add bad details type
def test_trace_add_type_error2():
    trace = Trace()
    with pytest.raises(TypeError):
        trace.add(GraphAction.INIT, 37)


# add empty details dict
def test_trace_add_type_error3():
    trace = Trace()
    with pytest.raises(TypeError):
        trace.add(GraphAction.INIT, {})


# bad details key type
def test_trace_add_type_error4():
    trace = Trace()
    with pytest.raises(TypeError):
        trace.add(GraphAction.INIT, {"Score": 23.1})


# wrong type for Detail item
def test_trace_add_type_error5():
    trace = Trace()
    with pytest.raises(TypeError):
        trace.add(GraphAction.INIT, {GraphActionDetail.DELTA: "wrong type"})


# unknown Attribute type
def test_trace_add_attribute_error1():
    trace = Trace()
    with pytest.raises(AttributeError):
        trace.add(GraphAction.INIT, {GraphActionDetail.SCORE: +00.09})


# mandatory details not provided
def test_trace_value_error_1():
    trace = Trace()
    with pytest.raises(ValueError):
        trace.add(GraphAction.INIT, {GraphActionDetail.ARC: ("A", "B")})
    with pytest.raises(ValueError):
        trace.add(GraphAction.ADD, {GraphActionDetail.DELTA: 21.0})


# correct trace calls
def test_trace_ok_1():
    trace = Trace()
    sleep(0.02)
    trace.add(GraphAction.INIT, {GraphActionDetail.DELTA: 31.2})
    print("\n\n{}".format(trace.get()))
    trace = trace.get().drop(labels="time", axis=1).to_dict("records")
    assert trace[0] == {
        "activity": "init",
        "arc": None,
        "delta/score": 31.2,
        "activity_2": None,
        "arc_2": None,
        "delta_2": None,
        "min_N": None,
        "mean_N": None,
        "max_N": None,
        "free_params": None,
        "lt5": None,
        "knowledge": None,
        "blocked": None,
    }


# correct trace calls usng chaining
def test_trace_ok_2():
    trace = (
        Trace()
        .add(GraphAction.INIT, {GraphActionDetail.DELTA: -200.8})
        .add(
            GraphAction.ADD,
            {GraphActionDetail.ARC: ("A", "B"), GraphActionDetail.DELTA: 41.4},
        )
        .add(
            GraphAction.DEL,
            {GraphActionDetail.ARC: ("B", "C"), GraphActionDetail.DELTA: 22.7},
        )
        .add(
            GraphAction.REV,
            {GraphActionDetail.ARC: ("A", "B"), GraphActionDetail.DELTA: 39.9},
        )
        .add(GraphAction.STOP, {GraphActionDetail.DELTA: -100.8})
    )
    print("\n\n{}".format(trace.get()))
    trace = trace.get().drop(labels="time", axis=1).to_dict("records")
    assert trace[0] == {
        "activity": "init",
        "arc": None,
        "delta/score": -200.8,
        "activity_2": None,
        "arc_2": None,
        "delta_2": None,
        "min_N": None,
        "mean_N": None,
        "max_N": None,
        "free_params": None,
        "lt5": None,
        "knowledge": None,
        "blocked": None,
    }
    assert trace[1] == {
        "activity": "add",
        "arc": ("A", "B"),
        "delta/score": 41.4,
        "activity_2": None,
        "arc_2": None,
        "delta_2": None,
        "min_N": None,
        "mean_N": None,
        "max_N": None,
        "free_params": None,
        "lt5": None,
        "knowledge": None,
        "blocked": None,
    }
    assert trace[2] == {
        "activity": "delete",
        "arc": ("B", "C"),
        "delta/score": 22.7,
        "activity_2": None,
        "arc_2": None,
        "delta_2": None,
        "min_N": None,
        "mean_N": None,
        "max_N": None,
        "free_params": None,
        "lt5": None,
        "knowledge": None,
        "blocked": None,
    }
    assert trace[3] == {
        "activity": "reverse",
        "arc": ("A", "B"),
        "delta/score": 39.9,
        "activity_2": None,
        "arc_2": None,
        "delta_2": None,
        "min_N": None,
        "mean_N": None,
        "max_N": None,
        "free_params": None,
        "lt5": None,
        "knowledge": None,
        "blocked": None,
    }
    assert trace[4] == {
        "activity": "stop",
        "arc": None,
        "delta/score": -100.8,
        "activity_2": None,
        "arc_2": None,
        "delta_2": None,
        "min_N": None,
        "mean_N": None,
        "max_N": None,
        "free_params": None,
        "lt5": None,
        "knowledge": None,
        "blocked": None,
    }


# correct trace calls usng chaining including blocked
def test_trace_ok_3():
    trace = (
        Trace()
        .add(GraphAction.INIT, {GraphActionDetail.DELTA: -200.8})
        .add(
            GraphAction.ADD,
            {
                GraphActionDetail.ARC: ("A", "B"),
                GraphActionDetail.DELTA: 41.4,
                GraphActionDetail.BLOCKED: [],
            },
        )
        .add(
            GraphAction.DEL,
            {
                GraphActionDetail.ARC: ("B", "C"),
                GraphActionDetail.DELTA: 22.7,
                GraphActionDetail.BLOCKED: [],
            },
        )
        .add(
            GraphAction.REV,
            {
                GraphActionDetail.ARC: ("A", "B"),
                GraphActionDetail.DELTA: 39.9,
                GraphActionDetail.BLOCKED: [
                    (GraphAction.ADD, ("B", "A"), 3.0, {})
                ],
            },
        )
        .add(GraphAction.STOP, {GraphActionDetail.DELTA: -100.8})
    )
    print("\n\n{}".format(trace.get()))
    trace = trace.get().drop(labels="time", axis=1).to_dict("records")
    assert trace[0] == {
        "activity": "init",
        "arc": None,
        "delta/score": -200.8,
        "activity_2": None,
        "arc_2": None,
        "delta_2": None,
        "min_N": None,
        "mean_N": None,
        "max_N": None,
        "free_params": None,
        "lt5": None,
        "knowledge": None,
        "blocked": None,
    }
    assert trace[1] == {
        "activity": "add",
        "arc": ("A", "B"),
        "delta/score": 41.4,
        "activity_2": None,
        "arc_2": None,
        "delta_2": None,
        "min_N": None,
        "mean_N": None,
        "max_N": None,
        "free_params": None,
        "lt5": None,
        "knowledge": None,
        "blocked": [],
    }
    assert trace[2] == {
        "activity": "delete",
        "arc": ("B", "C"),
        "delta/score": 22.7,
        "activity_2": None,
        "arc_2": None,
        "delta_2": None,
        "min_N": None,
        "mean_N": None,
        "max_N": None,
        "free_params": None,
        "lt5": None,
        "knowledge": None,
        "blocked": [],
    }
    assert trace[3] == {
        "activity": "reverse",
        "arc": ("A", "B"),
        "delta/score": 39.9,
        "activity_2": None,
        "arc_2": None,
        "delta_2": None,
        "min_N": None,
        "mean_N": None,
        "max_N": None,
        "free_params": None,
        "lt5": None,
        "knowledge": None,
        "blocked": [(GraphAction.ADD, ("B", "A"), 3.0, {})],
    }
    assert trace[4] == {
        "activity": "stop",
        "arc": None,
        "delta/score": -100.8,
        "activity_2": None,
        "arc_2": None,
        "delta_2": None,
        "min_N": None,
        "mean_N": None,
        "max_N": None,
        "free_params": None,
        "lt5": None,
        "knowledge": None,
        "blocked": None,
    }


# bad result type
def test_trace_set_result_type_error():
    with pytest.raises(TypeError):
        Trace().set_result("bad type")


# set Trace result
def test_trace_set_result_ok():
    trace = (
        Trace()
        .add(GraphAction.INIT, {GraphActionDetail.DELTA: 0.0})
        .add(
            GraphAction.ADD,
            {
                GraphActionDetail.ARC: ("A", "B"),
                GraphActionDetail.DELTA: 31.3,
                GraphActionDetail.ACTIVITY_2: "add",
                GraphActionDetail.ARC_2: ("B", "C"),
                GraphActionDetail.DELTA_2: 10.77,
            },
        )
        .set_result(ex_dag.ab())
    )
    ex_dag.ab(trace.result)


#   Tests on save and read functions


# no argument type
def test_trace_read_type_error_1():
    with pytest.raises(TypeError):
        Trace.read()


# bad id argument
def test_trace_read_type_error_2():
    with pytest.raises(TypeError):
        Trace.read(True, TESTDATA_DIR + "/experiments")
    with pytest.raises(TypeError):
        Trace.read(39, TESTDATA_DIR + "/experiments")
    with pytest.raises(TypeError):
        Trace.read(-11.2, TESTDATA_DIR + "/experiments")
    with pytest.raises(TypeError):
        Trace.read([-11.2], TESTDATA_DIR + "/experiments")
    with pytest.raises(TypeError):
        Trace.read("misc/trace", 32)
    with pytest.raises(TypeError):
        Trace.read("misc/trace", {"name": "what"})


# non-existent root directory
def test_trace_read_filenotfound_error():
    with pytest.raises(FileNotFoundError):
        Trace.read("test/test1", "nonexistent")


# partial id is zero length
def test_trace_read_value_error_1():
    with pytest.raises(ValueError):
        Trace.read("", TESTDATA_DIR)


# binary file
def test_trace_read_value_error_2():
    with pytest.raises(ValueError):
        Trace.read("trace/null.sys", TESTDATA_DIR)


# textual file
def test_trace_read_value_error_3():
    with pytest.raises(ValueError):
        Trace.read("trace/a_1.csv", TESTDATA_DIR)


# textual file
def test_trace_read_value_error_4():
    with pytest.raises(ValueError):
        Trace.read("trace/ab_cb.dsc", TESTDATA_DIR)


# serialised file, but not Trace
def test_trace_read_value_error_5():
    with pytest.raises(ValueError):
        Trace.read("trace/list", TESTDATA_DIR)


# empty trace file treated as non-existent
def test_trace_value_error_6():
    with pytest.raises(ValueError):
        Trace.read("empty", TESTDATA_DIR + "/trace")


# non-existent trace file
def test_trace_read_ok_1():
    traces = Trace.read("trace/nonexistent", TESTDATA_DIR)
    assert traces is None


# read OK from single entry file
def test_trace_read_ok_2():
    traces = Trace.read("single", TESTDATA_DIR + "trace/HC_N_1")
    assert isinstance(traces, dict)
    assert "entry1" in traces
    assert isinstance(traces["entry1"], Trace)
    assert traces["entry1"].context["id"] == "HC_N_1/single/entry1"


# non-existent entry
def test_trace_read_ok_3():
    traces = Trace.read("nonexistent", TESTDATA_DIR + "trace/HC_N_1")
    assert traces is None


# read OK from double entry file
def test_trace_read_ok_4():
    traces = Trace.read("double", TESTDATA_DIR + "trace/HC_N_1")
    assert isinstance(traces, dict)
    assert "entry1" in traces
    assert isinstance(traces["entry1"], Trace)
    assert traces["entry1"].context["id"] == "HC_N_1/double/entry1"
    assert "entry2" in traces
    assert isinstance(traces["entry2"], Trace)
    assert traces["entry2"].context["id"] == "HC_N_1/double/entry2"


# non-existent entry
def test_trace_read_ok_5():
    trace = Trace.read("nonexistent", TESTDATA_DIR + "trace/HC_N_1")
    assert trace is None


# check KS_R16_E100 trace containing knowledge
def test_trace_read_ok_7():
    traces = Trace.read("HC/KS_R16_E100/asia", TESTDATA_DIR + "/trace")
    trace = traces["N10"].trace
    assert trace["activity"] == ["init", "add", "add", "stop"]
    assert trace["arc"] == [None, ("xray", "bronc"), ("smoke", "tub"), None]
    assert trace["knowledge"] == [
        None,
        ("reqd_arc", True, "stop_del", ("either", "dysp")),
        ("reqd_arc", True, "stop_del", ("either", "dysp")),
        ("reqd_arc", True, "stop_del", ("either", "dysp")),
    ]


# no argument specified
def test_trace_save_type_error_1():
    with pytest.raises(TypeError):
        Trace({"id": "test"}).save(None)


# bad argument type
def test_trace_save_type_error_2():
    with pytest.raises(TypeError):
        Trace({"id": "test"}).save(37)
    with pytest.raises(TypeError):
        Trace({"id": "test"}).save(True)
    with pytest.raises(TypeError):
        Trace({"id": "test"}).save(-11.2)
    with pytest.raises(TypeError):
        Trace({"id": "test"}).save([-11.2])
    with pytest.raises(TypeError):
        Trace({"id": "test"}).save("misc/trace", 32)
    with pytest.raises(TypeError):
        Trace({"id": "test"}).save("misc/trace", {"name": "what"})


# non-existent root_dir
def test_trace_save_filenotfound_error():
    with pytest.raises(FileNotFoundError):
        Trace({"id": "test"}).save("nonexistent")


# id not defined
def test_trace_save_value_error_1():
    with pytest.raises(ValueError):
        Trace().save(EXPTS_DIR)


# invalid id
def test_trace_save_value_error_2():
    with pytest.raises(ValueError):
        Trace({"id": "invalid"}).save(EXPTS_DIR)


# try to save to binary file
def test_trace_save_value_error_3():
    with pytest.raises(ValueError):
        Trace({"id": "trace/null"}).save(TESTDATA_DIR)


# try to save to textual file
def test_trace_save_value_error_4():
    with pytest.raises(ValueError):
        Trace({"id": "trace/a_1.csv/test"}).save(TESTDATA_DIR)


# textual file
def test_trace_save_value_error_5():
    with pytest.raises(ValueError):
        Trace({"id": "trace/ab_cb.dsc/test"}).save(TESTDATA_DIR)


# serialised file, but not Trace
def test_trace_save_value_error_6():
    with pytest.raises(ValueError):
        Trace({"id": "trace/list/test"}).save(TESTDATA_DIR)


# save to file at root_dir, 1 entry
def test_trace_save_ok_1():
    Trace({"id": "single/entry1"}).save(TESTDATA_DIR + "trace/tmp")
    assert exists(TESTDATA_DIR + "trace/tmp/single.pkl.gz")
    traces = Trace.read("single", TESTDATA_DIR + "trace/tmp")
    assert isinstance(traces, dict)
    assert set(traces.keys()) == {"entry1"}
    assert isinstance(traces["entry1"], Trace)
    assert traces["entry1"].context["id"] == "single/entry1"
    remove(TESTDATA_DIR + "trace/tmp/single.pkl.gz")


# save to file at root_dir, 2 entries
def test_trace_save_ok_2():
    Trace({"id": "double/entry1"}).save(TESTDATA_DIR + "trace/tmp")
    assert exists(TESTDATA_DIR + "trace/tmp/double.pkl.gz")
    traces = Trace.read("double", TESTDATA_DIR + "trace/tmp")
    assert isinstance(traces, dict)
    assert set(traces.keys()) == {"entry1"}
    assert isinstance(traces["entry1"], Trace)
    assert traces["entry1"].context["id"] == "double/entry1"
    Trace({"id": "double/entry2"}).save(TESTDATA_DIR + "trace/tmp")
    assert exists(TESTDATA_DIR + "trace/tmp/double.pkl.gz")
    traces = Trace.read("double", TESTDATA_DIR + "trace/tmp")
    assert isinstance(traces, dict)
    assert set(traces.keys()) == {"entry1", "entry2"}
    assert isinstance(traces["entry1"], Trace)
    assert traces["entry1"].context["id"] == "double/entry1"
    assert isinstance(traces["entry2"], Trace)
    assert traces["entry2"].context["id"] == "double/entry2"
    remove(TESTDATA_DIR + "trace/tmp/double.pkl.gz")


# save the trace file, creating the required subdirectory
def test_trace_save_ok_3():
    Trace({"id": "newdir/single/entry1"}).save(TESTDATA_DIR + "trace/tmp")
    assert exists(TESTDATA_DIR + "trace/tmp/newdir/single.pkl.gz")
    traces = Trace.read("newdir/single", TESTDATA_DIR + "trace/tmp")
    assert isinstance(traces, dict)
    assert set(traces.keys()) == {"entry1"}
    assert isinstance(traces["entry1"], Trace)
    assert traces["entry1"].context["id"] == "newdir/single/entry1"
    rmtree(TESTDATA_DIR + "trace/tmp/newdir")
