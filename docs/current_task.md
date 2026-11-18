# Replicating the original pdg-merge charts__

- Figure styling: `theme` (Seaborn axes style, merged under the explicit properties), `figure.size`, `figure.layout` (`tight`/`constrained`), `figure.bbox_inches`, `figure.title_fontweight` and `subplot.title_fontweight`.
- Panel tags: `subplot.tag` and `subplot.tag_fontsize` draw the bold `A`/`B` labels in the axes corners.
- In-panel legends: `legend.subplots` (a list of subplot names, or `all`) removes the grid legend and rebuilds it inside the named panels; `legend.framealpha` sets its opacity and an empty `legend.title` suppresses the title.
- Scatter styling: `scatter.markers`, `scatter.size` and `scatter.alpha`, plus `scatter.connect_colour` and `scatter.connect_linewidth`. `scatter.connect_key` pairs the connectors by a row column so networks sharing an x value get one connector each; the column is carried into the long-form data as `row_key`.
- Bars: `bar.alpha` sets the patch opacity.
- Fixed a latent duplicate-keyword bug: `sharex`, `sharey` and `legend_out` are now passed to `catplot` directly rather than through `facet_kws` (matplotlib raised when both were given).
- New modules `plot.style` and `plot.legend` keep `plot.charts` within the module size target.


# Possible future work out of scope for this task

- the `evaluate_graph` → `analyse_graph` rename and the wider cache consolidation remain separate tasks, as agreed.

- __Per-input-group weights or a "require every input" guard in `merge_graphs`.__ Currently `weights` is a flat list over every graph read from every input cache; a missing subset makes the graph count and weight count disagree. A grouped form (`0.5` per input cache, distributed within the cache) plus a skip-if-input-empty rule would remove the barley guard and make fusion steps more robust. The two-stage subset ensemble design already handles this, so it is a convenience feature.

- Use `_aggregation_entries` instead of re-reading every cache per matrix job (the `O(groups × caches)` scan on the roadmap).

- retire the now-redundant `len(entries) != 1` checks inside `evaluate_graph`/`best_graph`

- Shared `ActionMetadata` builder across `best_graph`, `summarise`, `merge_graphs`, `plot`.

- Cross-repo refresh of `causaliq-workflow/docs/architecture/cache_type_model.md`.

- Decide the fate of `validation.validate_metric_specs`: it is public API but now has no caller inside `src` after `summarise` adopted its alias-aware parser.

- Optionally, apply `header`/`format`/`footer` to the CLI terminal table (`cli/common._print_summary_table`) so it matches the file outputs.

- __Cross-repo__ — refresh `causaliq-workflow/docs/architecture/cache_type_model.md` (it still shows `result.reference` and `result.evaluated_graph`).

- __Later audit__ — shared `ActionMetadata` builder once `best_graph`, `summarise`, `merge_graphs` and `plot` adopt the same contract.
