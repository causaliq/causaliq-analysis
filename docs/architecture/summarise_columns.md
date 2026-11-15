# Summarise Columns and Output Formats

This note is the decision record for the `summarise` table model: how the
columns of a summary table are named, which input cache supplies a column,
how derived columns are computed, and how the presentation formats render
the table. The user guide
[Summarising Results](../userguide/summarise.md) documents the same
contract for users.

## Column model

A summary table is an ordered list of columns:

1. **Grouping dimensions** first, in workflow `matrix` order.
2. **Metric columns** next, one per entry of the `metric` parameter, in
   the declared order.

Each metric column is either a **base column**, computed from the metric
values of one or all input caches, or a **derived column**, computed by a
formula over the columns that precede it.

## Aliases

A numeric index names either the one-based source index that selects an
input cache (`f1.mean[2]`) or the one-based element of a list-valued
`argmax` dimension (`f1.argmax.fusion_weights{1}`). A column is never
addressed by its position. Instead a metric declares a short alias with
`as`:

```yaml
metric:
  - f1.mean[1] as bnsl
  - f1.mean[2] as llm
  - fusion - max(bnsl, llm) as gain
```

Aliases are optional, unique, must be identifiers and may not shadow a
formula function. An alias names the column in later formulas and becomes
its default label. Because formulas use names rather than positions, a
numeric literal is always a number and reordering the metric list cannot
change what a formula means.

## Metric grammar

| Form | Meaning |
|------|---------|
| `<field>.<stat>` | The statistic over every input cache (union) |
| `<field>.<stat>[<source>]` | The statistic over one input cache |
| `<field>.argmax.<dimension>[<source>]` | The winning dimension value of one input cache |
| `<field>.argmax.<dimension>{<element>}[<source>]` | One element of a list-valued winning dimension |
| `<field>[<source>]` | The single distinct value of a field |
| `<formula>` | A derived column |

Any of these forms may declare an alias with a trailing ` as <name>`. An
entry that holds an operator or a function call is a formula; anything
else is a metric specification, so the two can never be confused.

A list-valued matrix dimension, such as a declared weight pair
`fusion_weights: [BNSL, LLM]`, is reported whole by an `argmax` column. A
trailing `{n}` selects one element of it, indexed from one like the source
index, so `f1.argmax.fusion_weights{1}` reports the BNSL weight of the
best entry. The element index is written before the source index
(`f1.argmax.fusion_weights{1}[2]`), and an index past the end of the list
reports an empty cell. Only `argmax` columns accept an element index,
because only they expose a matrix dimension's value.

Supported statistics are `mean`, `sd`, `count`, `min`, `max`, `median`
and `unique`. `unique` is action-only: it reports the single distinct
value of a field and rejects a field whose values disagree, which is what
a per-network node count needs. A base column without a source index
keeps the original union behaviour, so existing workflows are unchanged.

## Significance tables

A significance test is a table-level operation, not a column. It pairs the
values of two metric columns across the rows of a table and reports one
statistic and one p-value, so it cannot be expressed as a per-row cell.

Tests are therefore declared with a separate `significance` parameter:

```yaml
metric:
  - f1.mean[1] as bnsl
  - f1.mean[3] as fusion
significance:
  - wilcoxon-signed-rank-2-sided(fusion, bnsl) as "Fusion vs BNSL"
```

Each entry has the grammar `<test>(<left>, <right>) [as <label>]`. The
arguments must name aliases declared by `metric`, which keeps collection and
formula validation in one place. `as` is optional; without it the label is
`<left> vs <right>`. The test name, title, statistic symbol, format and
arity live in a registry, so a new test is an additive change.

A significance table has four fixed columns: `Comparison`, the test's
statistic (for example `W`), `p`, and `Significance`. The existing
`headers` and `format` contract applies to those columns, including a
`null` format entry that hides a column from presentation output while CSV
retains it. `footer` is rejected because a statistic over the W/p rows of
different tests is not meaningful. `caption` supplies the table heading and
defaults to `STATISTICAL TESTS (<test title>)`.

Rows are paired by the workflow grouping dimensions. A row missing either
value is omitted from that test, and fewer than two non-zero differences
reports empty statistic and p-value cells. All tests in one table must use
the same test, so the statistic header and caption are unambiguous.

The table is written to the declared `output`; it is not combined with a
metric table. A workflow that wants both runs a metric `summarise` step and
a significance `summarise` step.


The caches are joined on the grouping dimensions: a row is one matrix
combination, and a source-qualified column takes its values from the
entries of that cache which match the row's dimensions.

A metric that names its input cache therefore requires **every entry of
that cache to carry every grouping dimension**. The workflow scan treats
a missing dimension as a wildcard, which is right for a union but wrong
for a join: an entry without the dimension would contribute to every row.
Such an entry is rejected with an error naming the cache and the
dimension.

## Derived columns

A formula is a Python arithmetic expression over the aliases of the
columns that precede it, parsed with `ast` and evaluated against a
whitelist:

| Element | Supported |
|---------|-----------|
| Operators | `+`, `-`, `*`, `/`, unary `+`/`-`, parentheses |
| Literals | numbers (`0.5`, `100`) |
| References | aliases of earlier columns |
| Functions | `abs`, `max`, `min`, `round` |

```yaml
metric:
  - f1.mean[1] as bnsl
  - f1.mean[2] as llm
  - f1.mean[3] as fusion
  - fusion - max(bnsl, llm) as gain
  - round(gain * 100, 1) as gain_pct
```

Every element is unambiguous: a number is a number, a name is a column.
References are backward only, so a cycle is impossible, and an unknown
name fails validation with the alias it should have declared.

Missing values propagate as they do in a spreadsheet: arithmetic over an
empty cell yields an empty cell, `min` and `max` ignore empty values, and
a division by zero yields an empty cell.

## Presentation formats

The output extension selects the renderer:

| Extension | Renderer | Applies `format`/`footer` |
|-----------|----------|---------------------------|
| `.csv` | Raw table | No |
| `.tex` | LaTeX `tabular` fragment | Yes |
| `.md`, `.markdown` | Markdown table | Yes |

CSV output always holds raw values because a `plot` step reads the file
with `pandas.to_numeric`; formatted cells or a footer row would deform the
chart. The presentation formats are fragments, not documents: `.tex`
emits the `tabular` environment for `\input` inside a paper's own `table`
float, and `.md` emits the bare table so it can be embedded anywhere.

`headers` labels the visible columns, so it holds one entry per visible
grouping dimension followed by one per visible metric. `footer` uses the
same visible column order. `format` is the exception: it holds one entry
per declared column, because a null entry is what hides a column. Headers
are free text and deliberately independent of aliases: a header may be
narrative or hold markup, it may differ from the column's alias, and
renaming a header cannot break a formula. Without headers, a column's
default label is its alias, or its specification text when it declares
none.

`format` entries are Python format specifications (`.3f`, `+.3f`, `d`),
validated when the parameters are parsed. Width padding is applied
literally but is rarely useful, because both renderers align the columns
themselves; the type character decides the alignment (`s` left, numeric
right, an explicit `<`/`^`/`>` overrides it).

`footer` entries are blank, a statistic name (`mean`, `sd`, `count`,
`min`, `max`, `median`) or literal text. A statistic is computed over the
column's row values, so the footer of a derived column is the mean of the
derived values rather than the formula applied to the footer cells.

## Hidden columns

A `null` entry in `format` hides that column from the `.tex` and `.md`
output. The sentinel reuses the existing positional contract instead of
introducing a second list: `format` already holds one entry per declared
column, grouping dimensions first and metrics next, so a null at a
position unambiguously names the column to hide.

Hidden columns remain part of the table model:

- They are still computed, so a later derived column can refer to their
  alias.
- They still appear in CSV output, because CSV holds raw values for a
  `plot` step and never applies `format`. A hidden CSV column keeps its
  default label, because `headers` names only the visible columns.
- They do not need entries in `headers` or `footer`: those lists name the
  visible columns only. `format` remains the one positional list that
  covers every declared column, including hidden ones.
- At least one column must remain visible; an all-null `format` list is
  rejected during validation and again when the presentation columns are
  built.

The CLI cannot express a YAML null through its repeated `--format`
options, so hidden columns are currently a workflow action feature. A
separate `hidden` parameter was considered and rejected because it would
need a second positional or name-matching contract, a new provider
parameter and cross-package documentation for a presentation-only
concern.

LaTeX output escapes markup (`_`, `%`, `&`, `#`, `$`, `{`, `}`, `~`, `^`,
`<`, `>`, `\`) and rules the table with `\hline` after the header and
before the footer. Markdown output escapes `|`, `\`, `<` and newlines, and
derives its alignment row from the format type; it has no rule, so the
footer is simply the last body row.

## Module layout

The action keeps the model in small modules beside the original ones:

| Module | Responsibility |
|--------|----------------|
| `columns` | Column specifications, aliases, label and source-index validation |
| `formula` | Derived-column parsing, validation and evaluation |
| `stats` | Base-column statistics and per-source value lookup |
| `significance` | Significance test registry, pairing and result rows |
| `significance_specs` | Significance specification parsing and validation |
| `present` | Display columns shared by the renderers, hidden-column filtering, cell formatting |
| `footer` | Footer cells |
| `render_latex`, `render_markdown` | Emitters |
| `render_significance` | Significance table emitter |
| `render` | Renderer selection, file writing |
| `collect`, `report` | Per-source value collection |

## See Also

- [Summarisation Paradigm](summarisation_paradigm.md) — Aggregation model
- [Summarising Results](../userguide/summarise.md) — User guide
