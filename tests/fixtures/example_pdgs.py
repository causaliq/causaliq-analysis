#
#   Example PDGs for testing and demonstration
#
#   Functions follow a common signature of no arguments to generate a graph
#   and a graph argument to validate that graph e.g. ab() generates the
#   A->B PDG, and ab(graph) validates graph as being the A->B PDG.
#

from causaliq_core.graph import PDAG, PDG, EdgeProbabilities

from causaliq_analysis.merge import source_probabilities


def empty(check=None):
    if check is None:
        return PDG([], {})

    assert isinstance(check, PDG)
    assert check.nodes == []
    assert check.edges == {}
    return None


def a(check=None):
    if check is None:
        return PDG(["A"], {})

    assert isinstance(check, PDG)
    assert check.nodes == ["A"]
    assert check.edges == {}
    return None


def ab(check=None):
    if check is None:
        return PDG(
            ["A", "B"],
            {("A", "B"): EdgeProbabilities(forward=1.0, none=0.0)},
        )

    assert isinstance(check, PDG)
    assert check.nodes == ["A", "B"]
    probs = check.get_probabilities("A", "B")
    assert probs.forward == 1.0
    assert probs.backward == 0.0
    assert probs.undirected == 0.0
    assert probs.none == 0.0
    assert probs.p_exist == 1.0
    return None


def ba(check=None):
    if check is None:
        return PDG(
            ["A", "B"],
            {("A", "B"): EdgeProbabilities(backward=1.0, none=0.0)},
        )

    assert isinstance(check, PDG)
    probs = check.get_probabilities("A", "B")
    assert probs.forward == 0.0
    assert probs.backward == 1.0
    return None


def ab_undirected(check=None):
    if check is None:
        return PDG(
            ["A", "B"],
            {("A", "B"): EdgeProbabilities(undirected=1.0, none=0.0)},
        )

    assert isinstance(check, PDG)
    probs = check.get_probabilities("A", "B")
    assert probs.undirected == 1.0
    return None


def ab_fractional(check=None):  # P(A->B)=0.6, P(B->A)=0.1, no edge=0.3
    if check is None:
        return PDG(
            ["A", "B"],
            {
                ("A", "B"): EdgeProbabilities(
                    forward=0.6, backward=0.1, undirected=0.0, none=0.3
                )
            },
        )

    assert isinstance(check, PDG)
    probs = check.get_probabilities("A", "B")
    assert probs.forward == 0.6
    assert probs.backward == 0.1
    assert probs.undirected == 0.0
    assert probs.none == 0.3
    return None


def ab_fractional2(check=None):  # P(A->B)=0.4, P(B->A)=0.3, A--B=0.1
    if check is None:
        return PDG(
            ["A", "B"],
            {
                ("A", "B"): EdgeProbabilities(
                    forward=0.4, backward=0.3, undirected=0.1, none=0.2
                )
            },
        )

    assert isinstance(check, PDG)
    probs = check.get_probabilities("A", "B")
    assert probs.forward == 0.4
    assert probs.backward == 0.3
    assert probs.undirected == 0.1
    assert probs.none == 0.2
    return None


def ab_forward_undirected(check=None):  # P(A->B)=0.6, P(A--B)=0.4
    if check is None:
        return PDG(
            ["A", "B"],
            {
                ("A", "B"): EdgeProbabilities(
                    forward=0.6, undirected=0.4, none=0.0
                )
            },
        )

    assert isinstance(check, PDG)
    probs = check.get_probabilities("A", "B")
    assert probs.forward == 0.6
    assert probs.undirected == 0.4
    assert probs.none == 0.0
    return None


def from_pdag(pdag):
    """Return a deterministic PDG equivalent to a PDAG or DAG."""
    if not isinstance(pdag, PDAG):
        raise TypeError("from_pdag requires a PDAG or DAG")

    nodes = list(pdag.nodes)
    edges = {}
    for i, node_a in enumerate(nodes):
        for node_b in nodes[i + 1 :]:
            probs = source_probabilities(pdag, node_a, node_b)
            if probs.p_exist > 0.0:
                edges[(node_a, node_b)] = probs
    return PDG(nodes, edges)
