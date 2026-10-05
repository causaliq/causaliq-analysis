# evalute_graph extended to compare PDGs

The `evaluate_graph` action of `causaliq-analysis` performs a structural
comparison of a graph against a reference graph, producing F1, precision,
recall, SHD and low-level edge metrics. It makes use of the `pdag_compare`
method in @causaliq-analysis/src/causaliq-analysis/metrics.py which first computes low-level edge metrics, then derives F1, SHD etc from them.

We wish to extend evaluate_graph so it can also compare PDGs which 
define a probability associated with each edge type between pairs
of variables (A->B, A<-B, A--B and no edge). Since PDGs can represent DAGs, 
PDAGs and CPDAGs this means that evaluate_graph will be able to compare all supported graph types.

I suggest that the functionality in `pdag_compare` can be extended in
a new method `pdg_compare`. Further, the only functionality
within pdag_compare that needs to be changed is the computation of the low-level
edge metrics such as arcs_matched etc. Subsequent logic in pdag_compare can
probably remain the same.

In the current code these low-level metrics are always integers. Their
computation needs to be modified to account for the edge probabilities
present in PDGs as follows:

Suppose we have the following probabilities for the edge between A and B

```
REFERENCE PDG: A->B: 0.6, A<-B: 0.1, A--B: 0.0, no edge: 0.3
    GRAPH PDG: A->B: 0.4, A<-B: 0.3, A--B: 0.1, no edge: 0.2

Each of the four types of edge in the REFERENCE and GRAPH will be combined in 16 fractional low-level edge metric computations as folows:
REF: A->B: 0.6, GRAPH A->B: 0.4 ===> 'arc_matched' = 0.6 x 0.4 = 0.24
REF: A->B: 0.6, GRAPH A<-B: 0.3 ===> 'arc_reversed' = 0.6 x 0.3 = 0.18
... 
REF: no edge: 0.3, GRAPH no edge: 0.2 ===> 'missing_matched' = 0.3 x 0.2 = 0.06
```                  

These fractional low-level edge metrics will add up to 1.0 for each variable. pair.

We need to keep method `pdag_compare` for compatability with existing code.
However, it can now be a wrapper around `pdg_compare`; it just needs to convert its PDAG input arguments to PDGs before calling `pdg_compare`. Existing
tests of `pdag_compare` should therefore continue to pass and will provide a
useful test of the `pdg_compare` method.
