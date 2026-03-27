# SVG Recipes

Common code patterns for charts and diagrams.

## Canvas Setup

### Standard 16:9 (Presentations)
```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="1280" height="720">
  <rect x="0" y="0" width="1280" height="720" fill="#0F2323"/>
  <!-- Content -->
</svg>
```

## Text Elements

### Multi-line Text (Grouped for Editing)
```xml
<g transform="translate(250, 175)">
  <text x="0" y="0" text-anchor="middle" font-family="Public Sans, system-ui, sans-serif"
        fill="#4ECDC4" font-size="22" font-weight="600">Line One</text>
  <text x="0" y="28" text-anchor="middle" font-family="Public Sans, system-ui, sans-serif"
        fill="#4ECDC4" font-size="22" font-weight="600">Line Two</text>
</g>
```

### Text Anchoring
- `text-anchor="start"` — Left-aligned (default)
- `text-anchor="middle"` — Center-aligned
- `text-anchor="end"` — Right-aligned

## Shapes

### Circle with Semi-transparent Fill
```xml
<circle cx="440" cy="420" r="240"
        fill="#4ECDC4" fill-opacity="0.25"
        stroke="#4ECDC4" stroke-width="3"/>
```

### Venn Diagram (Two Circles)
```xml
<!-- Left circle -->
<circle cx="440" cy="420" r="240" fill="#4ECDC4" fill-opacity="0.25" stroke="#4ECDC4" stroke-width="3"/>
<!-- Right circle -->
<circle cx="840" cy="420" r="240" fill="#4169E1" fill-opacity="0.25" stroke="#4169E1" stroke-width="3"/>
```

Overlap naturally occurs where circles intersect. Position content in:
- Left-only zone: x ≈ 310
- Overlap zone: x = 640 (canvas center)
- Right-only zone: x ≈ 970

### Rounded Rectangle
```xml
<rect x="100" y="200" width="300" height="150" rx="8" ry="8"
      fill="#2a2a4a" stroke="#4ECDC4" stroke-width="2"/>
```

### Database Cylinder
```xml
<g transform="translate(100, 200)">
  <!-- Top ellipse -->
  <ellipse cx="75" cy="15" rx="75" ry="15" fill="#4ECDC4"/>
  <!-- Body -->
  <rect x="0" y="15" width="150" height="80" fill="#4ECDC4"/>
  <!-- Bottom ellipse -->
  <ellipse cx="75" cy="95" rx="75" ry="15" fill="#3BA89F"/>
  <!-- Label -->
  <text x="75" y="60" text-anchor="middle" fill="#0F2323" font-size="14">Database</text>
</g>
```

## Lines and Arrows

### Arrow Marker Definition
```xml
<defs>
  <marker id="arrow" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
    <polygon points="0 0, 10 3.5, 0 7" fill="#4ECDC4"/>
  </marker>
</defs>
```

### Line with Arrow
```xml
<line x1="200" y1="300" x2="400" y2="300"
      stroke="#4ECDC4" stroke-width="2" marker-end="url(#arrow)"/>
```

### Curved Path with Arrow
```xml
<path d="M 200 300 Q 300 200, 400 300"
      stroke="#4ECDC4" stroke-width="2" fill="none" marker-end="url(#arrow)"/>
```

**Note:** `sips` doesn't render markers. Use `rsvg-convert` for arrows.

### Dashed Line (Speculative/Projected)
```xml
<line x1="200" y1="300" x2="400" y2="300"
      stroke="#4ECDC4" stroke-width="2" stroke-dasharray="18,10"/>
```

## Smooth Curves

### Quadratic Bezier (Simple Curve)
```xml
<path d="M 100 400 Q 300 200, 500 400" stroke="#4ECDC4" stroke-width="4" fill="none"/>
```
- M = Move to start
- Q = Quadratic curve (control point, end point)

### Cubic Bezier (S-Curve)
```xml
<path d="M 100 400 C 200 200, 400 600, 500 400" stroke="#4ECDC4" stroke-width="4" fill="none"/>
```
- C = Cubic curve (control1, control2, end)

## Rendering

### rsvg-convert (Full Feature)
```bash
rsvg-convert -w 1280 -h 720 input.svg -o output.png
```

### sips (Fast, No Markers)
```bash
sips -s format png -z 720 1280 input.svg --out output.png
```

## Common Gotchas

1. **Text clipping** — Keep 20px margin from edges. Long titles may need line breaks.
2. **Font fallback** — Always include system-ui fallback: `font-family="Public Sans, system-ui, sans-serif"`
3. **Opacity stacking** — Semi-transparent overlapping shapes create darker intersections (usually desired for Venn)
4. **Coordinate origin** — (0,0) is top-left. Y increases downward.
