# DOT Graphs for Workflow Diagrams

For complex decision trees in skills, embed DOT graphs:

```dot
digraph workflow {
    "Is test passing?" [shape=diamond];
    "Write test first" [shape=box];
    "npm test" [shape=plaintext];
    "NEVER skip tests" [shape=octagon, style=filled, fillcolor=red];
}
```

Run `scripts/render_graphs.py <skill-path>` to render SVG.

## Node Shapes

- `diamond` — decisions/questions
- `box` — actions (default)
- `plaintext` — literal commands
- `ellipse` — states
- `octagon` (red) — STOP/warnings
- `doublecircle` — entry/exit points
