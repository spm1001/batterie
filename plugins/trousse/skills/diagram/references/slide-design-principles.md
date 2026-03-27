# Slide Design Principles

Design guidance for presentation context — when diagrams, charts, or visuals are destined for slides. Distilled from production system prompts and real-world formatting at scale.

Some rules here are universal (marked **U**) and reinforce existing CRAP principles with specific thresholds. Others are slide-specific (marked **S**) and only apply when the output lives in a presentation.

---

## Content Density

**U — Max 3-4 key points per slide.** A single slide should have at most 3-4 key points with short supporting text. If you have more, split across multiple slides. This applies to diagrams too — a flow chart with 12 boxes on one canvas is a document, not a visual.

**U — 14pt absolute minimum.** Nothing on any slide or diagram element should be below 14pt. Preferred body text: 16pt. Presentations are viewed at distance — what's readable on a monitor is invisible projected.

**U — Size to fill, not to fit.** "Size text to fill the available space rather than leaving empty room. Prefer more slides with less content over fewer dense slides with small fonts." Same as the diagram skill's 80% canvas fill rule, but the specific guidance is: if there's empty space, the content is too small or there's too little per slide.

**S — Table density limit.** If any table cell needs 3-4 sentences or >40 words, it's too dense for a table. Truncate to one sentence, add footnotes below, or split across slides. Plan row heights upfront (single-line: 28-32pt, two-line: 48-56pt) — set the table to match content, never shrink fonts to fit a fixed height.

---

## Spacing and Overlap

**U — Minimum gap: 0.3".** Elements closer than 0.3" (22pt, ~27px at 96dpi) look cramped or colliding. If two elements are that close, they should either be grouped (proximity) or separated.

**U — Slide edge margin: >= 0.5".** Content should not approach the slide edges closer than 0.5" (36pt). Projectors crop edges unpredictably. For diagrams on slides, this means the 80% canvas fill rule has a hard boundary — not edge-to-edge.

**U — Text inset 10-15pt from shape edges.** When placing text inside shapes (cards, banners, rounded rectangles), inset on all sides so text doesn't touch the border. This reinforces the Proximity principle — the text belongs to the shape, not to the edge.

**U — Even gaps, not uneven.** "No large empty area in one place, cramped in another." This is the Proximity principle's negative space rule made specific: whitespace should be *organised*, pooling between groups, not scattered randomly. The squint test catches this — uneven density is visible at reduced size.

**U — One fix often creates another.** Repositioning to fix an overlap can create a new gap problem. The verification loop (check → fix → re-check) should run at least twice. The diagram skill's render-and-critique cycle is exactly this pattern — the slide context just adds spatial thresholds.

---

## Centering and Composition

**U — Calculate, don't eyeball.** The diagram skill's centering calculation applies identically to slides:

```
left_edge = leftmost content x-coordinate
right_edge = rightmost content x-coordinate
content_center = (left_edge + right_edge) / 2
offset = canvas_center - content_center
```

For slides, canvas dimensions are typically 10" × 5.625" (914400 × 5143500 EMU in Google Slides; 720 × 405pt in PowerPoint). Subtract the 0.5" edge margins to get the usable area: 9" × 4.625".

**U — Balance whitespace left/right, top/bottom.** After centering horizontally, check vertical balance. A diagram that's centered horizontally but crowded to the top with empty space below still looks wrong. The composition check from the diagram skill applies — just account for the title area eating into the top.

**S — Titles anchor to the top.** On slides with titles, the title occupies a fixed zone (~top 15-20% of the slide). Content fills the remaining space. Don't centre content in the full slide height — centre it in the area below the title. This differs from standalone diagrams where the title is part of the visual.

---

## Colour and Contrast

**U — Vary the palette.** "Do NOT default to dark backgrounds. Light, warm, pastel, earthy, vibrant, and muted palettes are all great choices. Match the tone of the content — a playful topic deserves bright colours; a corporate report might use clean whites with accent colours; a nature topic could use greens and earth tones." The diagram skill's default dark background (#1a1a2e) is fine for standalone diagrams but monotonous across a deck.

**U — Contrast at distance.** The diagram skill's squint/reduced-size test is the same as projection-distance viewing. If text disappears at 50% zoom, it disappears on a projected slide. Minimum text contrast on dark backgrounds: #e2e8f0 (from diagram skill) or equivalent WCAG 4.5:1 ratio.

**U — No dark icons on dark backgrounds.** Icon and shape fills must contrast with the slide background. This applies to any visual element — if the diagram includes icons, badges, or status indicators, check their fill against the background explicitly. "Avoid dark icons on dark backgrounds or light icons on light backgrounds."

**S — Theme colours over hardcoded RGB.** When working within a branded deck, use theme colour references rather than explicit hex values. This allows the theme to be changed without re-colouring every element. For diagrams embedded in branded presentations, match the brand's colour tokens rather than hardcoding.

---

## Hierarchy

**U — Three levels maximum.** Title > highlighted element > content. The diagram skill already states this. The slide context adds specific size ranges:

| Level | Diagram (SVG) | Slide (pt) |
|-------|--------------|------------|
| Title | 36-40px | 28-36pt |
| Highlight | 24-28px | 20-24pt |
| Labels | 20-24px | 16-18pt |
| Body/content | 18-20px | 14-16pt |

The slide sizes are smaller because slide layouts have more structured real estate — the title placeholder handles the biggest text, leaving the body area for content.

**U — "Go bold or go home."** Reinforce the Contrast principle: wimpy differences (12pt vs 14pt) look like mistakes. If two elements are different levels of hierarchy, the difference should be obvious at a glance. 2x size difference for title vs body is the minimum.

---

## Layout (Slide-Specific)

**S — Use layouts, not blank canvases.** Presentation software provides layout templates with placeholder positions. Using them gives consistent font sizes and positioning. Building from scratch (all text boxes, no placeholders) loses inheritance and looks inconsistent across a deck.

**S — Layout vocabulary.** Standard layouts and when to use them:

| Layout | Use For |
|--------|---------|
| Title Slide | First slide, section dividers |
| Title and Content | Standard content with title + body |
| Two Content | Side-by-side comparison |
| Section Header | Transitions between major sections |
| Title Only | Title + custom shapes/diagrams below |
| Blank | Full-bleed images, diagram-only slides (no text structure) |

Diagrams typically go on **Title Only** (if they need a heading) or **Blank** (if they're the entire slide). "Do NOT use Blank for slides that contain body text."

**S — Master carries the design, slides carry the content.** Backgrounds, accent lines, decorative shapes, brand elements — these go on the master/layout, not repeated per-slide. Font colours come from the master's text styles, not set per-element. The only per-slide styling should be content-specific (highlighting a data point, colouring a specific shape for emphasis).

**S — Three deck types, three strategies.**

| Deck State | Strategy |
|-----------|----------|
| Blank (new deck) | Build theme from scratch on the master first |
| Styled slides, default master | The existing slides ARE the design system — match them |
| Has a template | Preserve it. Ask before restyling. |

---

## Icons and Visual Elements

**U — Never use emoji or Unicode symbols as icons.** They render inconsistently across platforms and look unprofessional. This applies to SVG diagrams too — use proper SVG shapes, not Unicode glyphs.

**S — Three-tier icon fallback.** Vector icons (preferred) > geometric shapes > coloured circles with labels. Only fall to the next tier when the previous one has nothing suitable.

**U — Icon sizing.** 36-48pt inline next to text. 72-144pt for decorative/hero icons. Keep icons consistent in size across one visual. Always remove outlines on icon shapes. Match colours to the visual's accent palette.

---

## Charts

**S — Never simulate charts with shapes.** If data needs to be visualised as a chart, use actual chart objects (OOXML in PowerPoint, Sheets-linked in Google Slides). Geometric shape approximations are non-editable, non-accessible, and look amateur.

**S — Theme colours for series.** Chart series should use theme colour references (accent1-accent6), not hardcoded RGB. This ensures charts match the deck theme. When the theme changes, charts update automatically.

**S — Required chart elements.** Every chart needs: a title, a legend (top position preferred), data labels on every series, and legible font sizes (14pt minimum for all chart text).

---

## Verification Checklist (Slide Context)

After placing a diagram or visual on a slide, verify:

- [ ] Nothing closer than 0.3" to another element (unless deliberately grouped)
- [ ] Nothing closer than 0.5" to slide edges
- [ ] Text inside shapes has 10-15pt inset from borders
- [ ] All text >= 14pt (check at reduced size — problems emerge)
- [ ] Font colour contrasts the background (WCAG 4.5:1 minimum)
- [ ] Icon/shape fills contrast the background
- [ ] Whitespace is balanced, not scattered
- [ ] Content is centred in the usable area (below title, within margins)
- [ ] No leftover placeholder content or empty placeholder frames
- [ ] Visual hierarchy survives the squint test
- [ ] One fix-and-verify cycle completed (no new problems introduced)

This extends the diagram skill's CRAP + Composition check with slide-specific spatial thresholds.
