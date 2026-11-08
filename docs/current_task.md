# Summarise supports multiple inputs and join operation

Please comment on these functional suggestions and devise a staged plan so that the 
`summarise` action can construct a table
of statistics based on metrics from **multiple** input caches.

The output format can either be CSV or LaTeX depending upon the extension of
the output file (`.csv` or `.tex`).

We aim to produce the following kinds of output, where BNSL, LLM, and
Fusion are F1 values computed from different input caches:

```text
Network                   & Nodes &    BNSL &     LLM &  Fusion & F>best \\
\hline
alarm                     &    37 &   0.804 &   0.653 &   0.866 & +0.062 \\
asia                      &     8 &   0.750 &   0.842 &   1.000 & +0.158 \\
\hline
AVERAGE                   &       &   0.662 &   0.572 &   0.760 & +0.056 \\
```

To do this we need a way to define:

1. which input file supplies a particular metrics,
for example `f1.mean[1]` could indicate `f1.mean` computed from F1 values in
the first input file

2. column headers, perhaps a simple list in column order

3. a syntax for derived column values e,g, for Fusion F1 minus best of 
LLM or BNSL

4. cell values formats - perhaps using Python format specifiers

5. specification of an optional footer row

Below is a **possible** syntax - please comment on this

```yaml
steps:
  - name: "summarise fusion metrics"
    uses: "causaliq-analysis"
    with:
      action: "summarise"
      input:
      - bnsl.db
      - llm.db
      - fusion.db
      metrics: 
      - node_count[1]
      - f1.mean[1]
      - f1.mean[2]
      - f1.mean[3]
      - SUBTRACT(5, MAX(3, 4))
      headers:
      - Network
      - Nodes
      - BNSL
      - LLM
      - Fusion
      - F>best
      format:
      - <18s
      - i3
      - f0.3
      - f0.3
      - f0.3
      - +f0.3
      footer:
      - "AVERAGE"
      - ""
      - mean
      - mean
      - mean
      - mean 

```

**Decided**: a derived column refers to earlier columns by a declared
alias (`f1.mean[1] as bnsl`) and is written in Python syntax
(`fusion - max(bnsl, llm)`); `headers` stay free text. See
`docs/architecture/summarise_columns.md`.



# Possible future work out of scope for this task


- __Cross-repo__ — refresh `causaliq-workflow/docs/architecture/cache_type_model.md` (it still shows `result.reference` and `result.evaluated_graph`).

- __Later audit__ — shared `ActionMetadata` builder once `best_graph`, `summarise`, `merge_graphs` and `plot` adopt the same contract.

