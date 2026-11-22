# SVG Editor Interoperability

Notes on how different editors handle SVG import, particularly multi-line text grouping.

## The Problem

When Claude creates SVGs, multi-line labels (e.g., "Audience\nMeasurement") need to stay together as one selectable object for human editing. If each line becomes a separate object, users must select and move multiple items — tedious and error-prone.

## Editor Compatibility

### Inkscape ✓
**Status:** Works correctly

Both approaches preserve text grouping:
- `<tspan>` within single `<text>` element
- Multiple `<text>` elements as siblings in a `<g transform="...">`

Multi-line text imports as a single selectable object.

**Caveats:** Inkscape on macOS can be crashy (race condition on startup). May need multiple launch attempts.

### Affinity Designer ✗
**Status:** Breaks text grouping on import

Tested approaches that all failed:
- `<tspan>` elements — broken into separate objects
- `<g>` groups — ignored, contents ungrouped
- Transform groups with text siblings — still broken apart
- Transparent rect containers — no effect

**Affinity-native multi-line text** (created in Affinity, exported to SVG) uses a different structure that Affinity respects on re-import, but this structure doesn't help when creating SVGs externally.

**Workaround:** If target editor is Affinity, accept that user will need to manually re-group text after import, or keep labels on single lines where possible.

### FigJam ✗
**Status:** Severely breaks text

FigJam (web-based) completely mangles SVG text on import — breaks characters into vertical stacks, loses positioning. Not usable for SVG editing.

### Other Editors (Untested)
- **Sketch** — Unknown
- **Adobe Illustrator** — Likely good support, untested
- **Linearity Curve (Vectornator)** — Free Mac app, untested
- **Boxy SVG** — Web-based, simple, untested

## Recommended SVG Structure

For maximum compatibility, use transform groups with relative positioning:

```xml
<g transform="translate(250, 175)">
  <text x="0" y="0" text-anchor="middle" fill="#COLOR" font-size="22">Line One</text>
  <text x="0" y="28" text-anchor="middle" fill="#COLOR" font-size="22">Line Two</text>
</g>
```

This works in Inkscape. For Affinity users, document that re-grouping may be needed.

## Object Model Principles

Beyond text grouping, consider:

1. **Minimize discrete objects** — Fewer objects = easier human editing
2. **Avoid overlays** — Don't put text as separate object over a colored rectangle; use SVG properties instead where possible
3. **Use semantic grouping** — Group elements that belong together conceptually
4. **Consistent positioning** — Use relative coordinates within groups for easier repositioning

## Future Work

- Test Linearity Curve, Boxy SVG for Mac-friendly alternatives
- Investigate if Affinity has import settings that preserve grouping
- Consider PDF export as alternative interchange format
