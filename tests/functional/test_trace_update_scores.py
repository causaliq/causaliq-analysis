# Test the Trace update_scores function

from os import remove
from shutil import copy

import pytest
from causaliq_core.utils import values_same

from causaliq_analysis.trace import Trace

TESTDATA_DIR = "tests/data/functional/"


# Test no args
def test_trace_update_scores_type_error_1():  # no args
    with pytest.raises(TypeError):
        Trace.update_scores()


# Test missing args
def test_trace_update_scores_type_error_2():  # missing args
    with pytest.raises(TypeError):
        Trace.update_scores(series="HC/STD", networks=["asia"])
    with pytest.raises(TypeError):
        Trace.update_scores(series="HC/ORD", score="bic")
    with pytest.raises(TypeError):
        Trace.update_scores(networks=["sports"], score="bic")


# Test bad arg type
def test_trace_update_scores_type_error_3():  # bad arg type
    with pytest.raises(TypeError):
        Trace.update_scores(series="HC/STD", networks=["asia"])
    with pytest.raises(TypeError):
        Trace.update_scores(series="HC/ORD", score="bic")
    with pytest.raises(TypeError):
        Trace.update_scores(networks=["sports"], score="bic")


# Test unknown score
def test_trace_update_scores_value_error_1_():  # unknown score
    with pytest.raises(ValueError):
        Trace.update_scores(
            series="HC/ORDER/BASE",
            networks=["asia"],
            score="invalid",
            root_dir=TESTDATA_DIR + "trace",
        )


# Test wrong objective score
def test_trace_update_scores_value_error_2_():  # wrong objective score
    with pytest.raises(ValueError):
        Trace.update_scores(
            series="HC/ORDER/BASE",
            networks=["asia"],
            score="bde",
            root_dir=TESTDATA_DIR + "trace",
        )


# Test update asia, bic scores
def test_trace_update_scores_ok_1_():  # update asia, bic scores
    scores = Trace.update_scores(
        series="HC/ORDER/BASE",
        networks=["asia"],
        score="bic",
        root_dir=TESTDATA_DIR + "trace",
    )
    assert len(scores) == 110
    assert values_same(scores[("asia", "N10_0")][0], -45.44360605, sf=10)
    assert values_same(scores[("asia", "N200_6")][1], -491.1460852, sf=10)


# Test update asia, bic scores
def test_trace_update_scores_ok_2_():  # update asia, bic scores and save
    copy(
        TESTDATA_DIR + "trace/HC/ORDER/BASE/asia.pkl.gz",
        TESTDATA_DIR + "trace/tmp/asia.pkl.gz",
    )
    scores = Trace.update_scores(
        series="tmp",
        networks=["asia"],
        score="bic",
        root_dir=TESTDATA_DIR + "trace",
        save=True,
    )
    assert len(scores) == 110
    assert values_same(scores[("asia", "N10_0")][0], -45.44360605, sf=10)
    assert values_same(scores[("asia", "N200_6")][1], -491.1460852, sf=10)
    remove(TESTDATA_DIR + "trace/tmp/asia.pkl.gz")


# Test update asia, loglik scores
def test_trace_update_scores_ok_3_():  # update asia, loglik scores
    scores = Trace.update_scores(
        series="HC/ORDER/BASE",
        networks=["asia"],
        score="loglik",
        root_dir=TESTDATA_DIR + "trace",
    )
    assert len(scores) == 110
    assert scores[("asia", "N10_0")][0] is None
    assert values_same(scores[("asia", "N200_6")][1], -451.4087050, sf=10)


# Test unknown series
def test_trace_update_scores_ok_4_():  # unknown series
    scores = Trace.update_scores(
        series="invalid",
        networks=["asia"],
        score="bic",
        root_dir=TESTDATA_DIR + "trace",
    )
    assert scores == {}


# Test unknown network
def test_trace_update_scores_ok_5_():  # unknown network
    scores = Trace.update_scores(
        series="HC/ORDER/BASE",
        networks=["invalid"],
        score="bic",
        root_dir=TESTDATA_DIR + "trace",
    )
    assert scores == {}
