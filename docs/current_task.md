

Please devise a plan for `summarise` to support significance statistics
- initially Wilcoxon signed-rank, two-sided, but the approach should be extensible
so that new metrics can be added as needed.

This perhaps could be done with a syntax like `f1.mean.wilcoxon-signed-rank-2-sided` or
perhaps a more compact, but still understandable name.

The initial aim is to be able to generate the following data produced by
@causaliq-research/papers/pdg-merge/src/main_results.py:

```text
STATISTICAL TESTS (Wilcoxon signed-rank, two-sided)
  Fusion vs BNSL            W=   17.0  p=0.0000 ***
  Fusion vs LLM             W=    3.0  p=0.0000 ***
  Fusion vs best solo       W=   36.0  p=0.0001 ***
```

Any new workflows should be put in the 03_fusion subfolders under
@causaliq-research/papers/pdg-merge/workflows


# Possible future work out of scope for this task

- __Per-column entry predicates in `summarise`.__ Syntax such as `f1.mean[1] where model == 'gemini' as gemini` would allow one metrics cache per ablation family, keyed by `(network, model)`, instead of one cache file per variant. It would also make factorial analyses generally easier. Implementation would touch `ColumnSpec`, column parsing, the `(source, field)` value keys in `collect.py`/`stats.py`/`report.py`, and add unit tests. This is the most useful long-term addition, but it is not needed for the proposed workflow shape.

- __Per-input-group weights or a "require every input" guard in `merge_graphs`.__ Currently `weights` is a flat list over every graph read from every input cache; a missing subset makes the graph count and weight count disagree. A grouped form (`0.5` per input cache, distributed within the cache) plus a skip-if-input-empty rule would remove the barley guard and make fusion steps more robust. The two-stage subset ensemble design already handles this, so it is a convenience feature.

- Use `_aggregation_entries` instead of re-reading every cache per matrix job (the `O(groups × caches)` scan on the roadmap).

- retire the now-redundant `len(entries) != 1` checks inside `evaluate_graph`/`best_graph`

- Shared `ActionMetadata` builder across `best_graph`, `summarise`, `merge_graphs`, `plot`.

- Cross-repo refresh of `causaliq-workflow/docs/architecture/cache_type_model.md`.

- Decide the fate of `validation.validate_metric_specs`: it is public API but now has no caller inside `src` after `summarise` adopted its alias-aware parser.

- Optionally, apply `header`/`format`/`footer` to the CLI terminal table (`cli/common._print_summary_table`) so it matches the file outputs.

- __Cross-repo__ — refresh `causaliq-workflow/docs/architecture/cache_type_model.md` (it still shows `result.reference` and `result.evaluated_graph`).

- __Later audit__ — shared `ActionMetadata` builder once `best_graph`, `summarise`, `merge_graphs` and `plot` adopt the same contract.

