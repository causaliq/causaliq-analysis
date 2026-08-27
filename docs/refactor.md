# Refactor code

Refactor code to make modules smaller and more comprehensible to humans and LLMs alike. Aim is to reduce token counts in LLM requests.

| Module        | Lines | Stmts | Issues |
|---------------|-------|-------|--------|
| \_\_init\_\_  |    74 |    23 | None   |
| cli           |  1260 |   485 | click.options scattered through file <br/>Can the click.options aruments be specified more cleanly in a structure?<br/>Should the xxx_cmd files be moved to their own modules<br/>Is there any code duplication with `workflow_action.py`<br/>migrate_trace[60], merge_graphs[258], evaluate_graph[153], best_graph[96], summarise[257], plot[50]       |
| graph         |    77 |    33 | None (just an enumeration) |
| merge         |   389 |   132 | merge_graphs[136] a little long |