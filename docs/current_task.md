# Correct metadata for `evaluate_graph` action

Please create a plan to make these changes to the metadata produced by the `evaluate_graph` action.

All parameter values should be placed in parameters section, including those
given no value or taking a default.

The `evaluated_graph` result should not be included (it can be retrieved from the metadata history when that feature is implemented)

In the case where the action fails because there is no learnt graph, the error paramter should not be the reason why the learnt graph was not produced, but rather just say "No graph present"

# Possible future work out of scope for this task

- __Hat 2__ — split `evaluate_graph.py` (223 module statements vs the ~200 advisory limit).

- __Hat 2__ — split the oversize `tests/unit/test_action_evaluate_graph.py`.

- __Cross-repo__ — refresh `causaliq-workflow/docs/architecture/cache_type_model.md` (it still shows `result.reference` and `result.evaluated_graph`).

- __Later audit__ — shared `ActionMetadata` builder once `best_graph`, `summarise`, `merge_graphs` and `plot` adopt the same contract.

