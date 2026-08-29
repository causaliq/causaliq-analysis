# Values of the `plot` `properties` can be Python types

The `properties` parameter of the `causaliq-analysis plot` action is defined as a 
list of strings which works well as it allows us to define multiple properties in 
the workflow `.yml` as follows:

```yml
steps:
  - name: "Generate HC F1 graph"
    uses: "causaliq-analysis"
    with:
      action: "plot"
      ... other parameters ...
      properties:
        - figure.title:Test HC Figure
        - yaxis.ticks_fontsize:16
```

However, some plot properties need to be specified as lists, sets, tuples or dicts.
It is suggested we may change the format of the properties's string elements to support
this, using the following syntax:

```yml
   with:
      action: "plot"
      ... other parameters ...
      properties:
        - string.property='string value'
        - int.property=22
        - float.propety=0.23
        - tuple.property=(2, 'dad')
        - list.property=['a', 1, 2.3]
        - dict.property={'key1': 1, 'key2': 'me'}
        - set.property={1, 'two'}
```

so that values are specified in Python syntax _within_ the string element. We replace the colon between property name and value with an equals sign to be more intuitive. This would
also allow us to specify multiple properties on the CLI (less conveniently) using

```bash
cqalys plot --property 'int.property=22' --property 'string.property="value"'
```

Would this work?

## Resolution

Yes — this works and has been implemented in v0.5.0.

The `properties` parameter of the `plot` action now accepts the
`<name>=<value>` format, where `<value>` is written in Python literal
syntax. Values are parsed with `ast.literal_eval` (safe, no code
execution), so integers, floats, quoted strings, tuples, lists, dicts
and sets can be specified directly:

```yml
properties:
  - string.property='string value'
  - int.property=22
  - float.property=0.23
  - tuple.property=(2, 'dad')
  - list.property=['a', 1, 2.3]
  - dict.property={'key1': 1, 'key2': 'me'}
  - set.property={1, 'two'}
```

Values which are not valid Python literals (e.g. `lightgray`) are
treated as plain strings, a blank value (`figure.title=`) sets an empty
string and `¬` sets `None`.

Notes for users migrating from the old `:` format:

- The legacy `<name>:<value>` separator is no longer accepted and now
  raises a clear error directing users to `=`.
- On the CLI, quote the whole property string so the shell does not
  split it: `causaliq-analysis plot -p "dict.property={'a': 1}"`.
- In workflow YAML, dict values contain `: ` which ends a plain scalar,
  so double-quote the property string:
  `- "dict.property={'key1': 1, 'key2': 'me'}"`.