# Checking causal-discovery produces same **graphs** as BNSL legacy code.

Update `evaluate_graph` capability so that `reference` argument can be a workflow cache rather than just a single ground-truth reference graph. This will allow it to compare graphs in different caches which have identical cache keys (e.g. network='asia', sample_size=100). In this case  , `evaluate_graph` must check:

* `reference` cache has same key structure as `input` cache
* report errors if entries in `reference` cache do not contain graphs
* update entries in `input` cache with the metrics in the same way as now when a single ground-truth reference is used

Planning phase needs to:
 * Explore how causaliq-workflow stores, keys, and extracts graph objects from its cache.
 * Identify the exact input types and interfaces evaluate_graph currently accepts.
 * Draft the updated function signature and internal parsing logic needed to resolve a graph from the workflow cache.