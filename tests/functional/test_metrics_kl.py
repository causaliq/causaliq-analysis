import pytest
from causaliq_core.bn import BN
from causaliq_core.bn.io import read_bn
from causaliq_core.utils import values_same
from causaliq_data.pandas import Pandas
from numpy import nan
from pandas import Series

from causaliq_analysis.metrics import kl

TESTDATA_DIR = "tests/data/functional"


# Test TypeError for bad argument types
def test_kl_type_error():
    with pytest.raises(TypeError):
        kl()
    with pytest.raises(TypeError):
        kl("bad arg")
    with pytest.raises(TypeError):
        kl("bad arg", "bad arg")
    dist = Series(data={"a": 0.2, "b": 0.8})
    with pytest.raises(TypeError):
        kl(3.2, dist)
    with pytest.raises(TypeError):
        kl(dist, True)


# Test ValueError for inconsistent indices
def test_kl_value_error1():
    dist1 = Series(data={"a": 0.2, "b": 0.8})
    dist2 = Series(data={"a": 0.2, "c": 0.8})
    with pytest.raises(ValueError):
        kl(dist1, dist2)
    dist3 = Series(data={"a": 0.2, "b": 0.7, "c": 0.1})
    with pytest.raises(ValueError):
        kl(dist1, dist3)
    with pytest.raises(ValueError):
        kl(dist3, dist1)


# Test ValueError for nan numbers
def test_kl_value_error2():
    dist1 = Series(data={"a": 0.2, "b": nan})
    dist2 = Series(data={"a": 0.2, "b": 0.8})
    with pytest.raises(ValueError):
        kl(dist1, dist2)
    with pytest.raises(ValueError):
        kl(dist2, dist1)
    dist3 = Series(data={"a": nan, "b": nan})
    with pytest.raises(ValueError):
        kl(dist1, dist3)
    with pytest.raises(ValueError):
        kl(dist3, dist1)


# Test ValueError for bad values
def test_kl_value_error3():
    dist1 = Series(data={"a": 0.2, "b": 1.1})
    dist2 = Series(data={"a": 0.2, "b": 0.8})
    dist3 = Series(data={"a": -0.1, "b": 0.8})
    with pytest.raises(ValueError):
        kl(dist1, dist2)
    with pytest.raises(ValueError):
        kl(dist2, dist3)


# Check can cope with one distribution having 0 probability
def test_kl_value_ok1():
    dist1 = Series(data={"a": 0.2, "b": 0.8})
    dist2 = Series(data={"a": 0.0, "b": 1.0})
    assert values_same(kl(dist1, dist2), 6.867869874)


# Check can cope with both distributions having 0 probability
def test_kl_value_ok2():
    dist1 = Series(data={"a": 1.0, "b": 0.0})
    dist2 = Series(data={"a": 0.0, "b": 1.0})
    assert values_same(kl(dist1, dist2), 36.84136149)


# Test Kullback-Leibler divergence Wikipedia example
def test_metrics_kl_wiki_ok():
    p = Series(data={"0": 0.36, "1": 0.48, "2": 0.16})
    q = Series(data={"0": 1 / 3, "1": 1 / 3, "2": 1 / 3})

    # Check get KL values reported in Wikipedia article

    assert values_same(kl(p, q), 0.0852996, sf=6)
    assert values_same(kl(q, p), 0.097455, sf=5)

    # Check KL of distribution with itself is zero

    assert values_same(kl(p, p), 0)
    assert values_same(kl(q, q), 0)


# Test KL divergence of sample from true distribution in A --> B
def test_metrics_kl_ab_ok():
    ab = read_bn(TESTDATA_DIR + "/ab.dsc")  # get A-->B BN

    limit = ab.global_distribution()  # theoretical distribution
    limit = limit.set_index(ab.dag.nodes).squeeze()  # convert to Series

    print("\nKL divergence of sample from true distribution: A --> B")
    for N in [50, 100, 200, 500, 1000, 2000, 5000]:
        data = Pandas(df=ab.generate_cases(N))
        dist = data.sample.value_counts().divide(N)  # df to count series
        print("KL is {:.3E} at sample size {}".format(kl(dist, limit), N))

        fit = BN.fit(ab.dag, data)  # re-fit BN so CPTs match data
        dist2 = fit.global_distribution()
        dist2 = dist2.set_index(ab.dag.nodes).squeeze()
        assert kl(dist, dist2) < 1e-10


# Test KL divergence of sample from true in A --> B --> C
def test_metrics_kl_abc_ok():
    abc = read_bn(TESTDATA_DIR + "/abc.dsc")  # get A-->B-->C BN

    limit = abc.global_distribution()  # theoretical distribution
    limit = limit.set_index(abc.dag.nodes).squeeze()  # convert to Series

    print("\nKL divergence of sample from true distribution: A --> B --> C")
    for N in [50, 100, 200, 500, 1000, 2000, 5000]:
        # for N in [10000]:
        data = abc.generate_cases(N)  # generate data for N cases
        dist = data.value_counts().divide(N)  # dataframe to count series
        print("KL is {:.3E} at sample size {}".format(kl(dist, limit), N))


# Test KL divergence of sample from true in A --> B <-- C
def test_metrics_kl_ab_cb_ok():
    ab_cb = read_bn(TESTDATA_DIR + "/ab_cb.dsc")  # get A-->B<--C BN

    limit = ab_cb.global_distribution()  # theoretical distribution
    limit = limit.set_index(ab_cb.dag.nodes).squeeze()  # convert to Series

    print("\nKL divergence of sample from true distribution: A --> B <-- C")
    for N in [200, 500, 1000, 2000, 5000]:
        data = ab_cb.generate_cases(N)  # generate data for N cases
        dist = data.value_counts().divide(N)  # dataframe to count series
        print("KL is {:.3E} at sample size {}".format(kl(dist, limit), N))
