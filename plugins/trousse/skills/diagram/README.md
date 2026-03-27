# Diagramming Skill

Create diagrams and visual explanations with an iterative render-and-check workflow.

## What This Skill Does

Enables Claude to create and refine diagrams:
- SVG generation with proper structure
- PNG rendering via sips (macOS) or rsvg-convert
- Self-critique using CRAP design principles (Contrast, Repetition, Alignment, Proximity)
- Iterative improvement until the diagram is right

## Installation

Install via batterie-de-savoir marketplace: `/plugin marketplace add spm1001/batterie-de-savoir` then `/plugin install trousse`

## When Claude Uses This Skill

Activates on:
- "create a diagram", "draw a chart", "visualize this"
- Venn diagrams, architecture diagrams, flow charts
- Any request for conceptual visuals

## File Structure

```
diagramming/
├── SKILL.md              # Main skill with workflow
└── references/
    └── svg-rendering.md  # Rendering commands and gotchas
```

## Workflow

1. **Create** — Generate SVG with proper viewBox and structure
2. **Render** — Convert to PNG using sips or rsvg-convert
3. **View** — Claude examines the rendered output
4. **Critique** — Apply CRAP principles
5. **Iterate** — Fix issues and re-render

## Requirements

- macOS with `sips` (built-in), or
- `rsvg-convert` (install via `brew install librsvg`)

## Composing with Brand Skills

For branded diagrams, this skill composes with styling skills (e.g., itv-styling):
- diagramming provides the workflow
- brand skill provides colors, fonts, design rules

## License

MIT
