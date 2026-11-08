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

A numeric index appears in exactly one place: the one-based source index
that names an input cache (`f1.mean[2]`). A column is never addressed by
its position. Instead a metric declares a short alias with `as`:

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
| `<field>[<source>]` | The single distinct value of a field |
| `<formula>` | A derived column |

Any of these forms may declare an alias with a trailing ` as <name>`. An
entry that holds an operator or a function call is a formula; anything
else is a metric specification, so the two can never be confused.

Supported statistics are `mean`, `sd`, `count`, `min`, `max`, `median`
and `unique`. `unique` is action-only: it reports the single distinct
value of a field and rejects a field whose values disagree, which is what
a per-network node count needs. A base column without a source index
keeps the original union behaviour, so existing workflows are unchanged.

## Joining input caches

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

`headers` labels every column of the table, so it holds one entry per
grouping dimension followed by one per metric; `format` and `footer` use
the same column order. Headers are free text and deliberately independent
of aliases: a header may be narrative or hold markup, it may differ from
the column's alias, and renaming a header cannot break a formula. Without
headers, a column's default label is its alias, or its specification text
when it declares none.

`format` entries are Python format specifications (`.3f`, `+.3f`, `d`),
validated when the parameters are parsed. Width padding is applied
literally but is rarely useful, because both renderers align the columns
themselves; the type character decides the alignment (`s` left, numeric
right, an explicit `<`/`^`/`>` overrides it).

`footer` entries are blank, a statistic name (`mean`, `sd`, `count`,
`min`, `max`, `median`) or literal text. A statistic is computed over the
column's row values, so the footer of a derived column is the mean of the
derived values rather than the formula applied to the footer cells.

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
| `present` | Display columns shared by the renderers, cell formatting |
| `footer` | Footer cells |
| `render_latex`, `render_markdown` | Emitters |
| `render` | Renderer selection, file writing |
| `collect`, `report` | Per-source value collection |

## See Also

- [Summarisation Paradigm](summarisation_paradigm.md) — Aggregation model
- [Summarising Results](../userguide/summarise.md) — User guide
