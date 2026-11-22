# Design Principles for Visual Critique

Based on Robin Williams' "The Non-Designer's Design Book". Use these principles to diagnose what's wrong with a visualization and know how to fix it.

## The CRAP Framework

Four principles, in order of typical application:

1. **Proximity** — Group related items together
2. **Alignment** — Create visual connections through placement
3. **Repetition** — Establish consistency through repeated elements
4. **Contrast** — Create hierarchy and interest through difference

---

## Proximity

### The Principle
Items relating to each other should be grouped close together. Physical closeness implies relationship.

### Why It Works
When several items are in close proximity, they become one visual unit rather than several separate units. The brain automatically groups nearby elements. This reduces cognitive load and helps readers find information.

### Signs of Violation
- Scattered elements with equal spacing everywhere
- Headlines equidistant from text above and below (unclear which text they belong to)
- White space "trapped" in random pockets rather than organized around groups
- Reader's eye wanders without clear path
- Count the visual elements: more than 3-5 separate items suggests ungrouped content

### Specific Interventions
- **Group labels with their data:** Place axis labels, data point labels, and legend items physically close to what they describe
- **Create clear groups:** Reduce space within groups, increase space between groups
- **Headlines closer to content:** A title should be noticeably closer to its content than to unrelated elements
- **Let white space form around groups:** Don't scatter it—let it pool in meaningful areas

### For SVG Charts Specifically
- Data labels should be adjacent to their data points, not in a distant legend
- Group related Y-axis labels together if they form categories
- Title → subtitle → chart area should feel like one unit with clear spacing to any footer/source text

---

## Alignment

### The Principle
Nothing should be placed on the page arbitrarily. Every element should have a visual connection with something else on the page.

### Why It Works
Our eyes like to see order. Alignment creates invisible lines that connect elements, producing a calm, organized feeling. Even elements far apart can feel unified if they share an alignment edge.

### Signs of Violation
- Elements feel "scattered" or randomly placed
- Multiple alignment systems competing (some centered, some left-aligned, some right-aligned)
- Centered text by default without intentional choice
- Hard edges that don't line up with anything
- No strong "invisible line" connecting elements

### Specific Interventions
- **Choose one alignment and commit:** All flush-left, OR all flush-right, OR intentionally centered. Don't mix.
- **Create strong edges:** Flush-left or flush-right creates stronger visual lines than centered
- **If centering, make it obvious:** Centered alignment should look intentional, not accidental. Add extra emphasis.
- **Align across distance:** Elements far apart should still align to the same invisible line
- **Break alignment consciously:** If you break alignment, do it dramatically so it looks intentional

### For SVG Charts Specifically
- All Y-axis labels should share the same right edge (right-aligned) or left edge
- Data labels should align consistently (all left of points, or all right)
- Title, subtitle, axis titles should share a common left edge
- Grid lines create natural alignment guides—use them
- If an element breaks the grid, make it dramatically different (not slightly off)

---

## Repetition

### The Principle
Repeat visual elements throughout the design. Consistency in style creates unity.

### Why It Works
Repetition ties separate parts together. It signals "these belong together" and creates a sense that someone is in charge—a thoughtful design decision. It also helps readers predict where to find information.

### Signs of Violation
- Every element styled differently
- Inconsistent spacing, colors, or typography across similar elements
- No visual rhythm or pattern
- Reader can't predict what similar elements will look like
- "Orphan" styles that appear only once

### Specific Interventions
- **Identify repeatable elements:** Colors, fonts, stroke weights, spacing, shapes
- **Create a system:** All data series use the same stroke weight. All labels use the same font size. All spacing between elements follows a ratio.
- **Push repetition further:** If you already repeat something, make it more prominent. Turn weak repetition into a strong visual motif.
- **Repetition + Contrast:** Repeat most elements, but consciously break repetition for emphasis

### For SVG Charts Specifically
- All data lines: same stroke-width (e.g., 4px)
- All labels: same font-family, same size within category
- All axis ticks: same length, same stroke
- Color palette: limited set, reused consistently
- Spacing rhythm: consistent margins and padding throughout

---

## Contrast

### The Principle
If two elements are not the same, make them *very* different. Contrast creates visual interest and establishes hierarchy.

### Why It Works
Contrast draws the eye and signals importance. It organizes information by showing what's primary, secondary, and tertiary. Without contrast, everything competes equally and nothing stands out.

### Signs of Violation
- Everything looks the same weight/size/color
- Hierarchy is flat—unclear what to read first
- "Wimpy" differences: 12pt vs 14pt, dark brown vs black, thin line vs slightly-thinner line
- Multiple elements competing for attention
- Subtle variations that look like mistakes rather than choices

### Specific Interventions
- **Go bold or go home:** If you're going to contrast, make it obvious. Don't contrast 12pt with 14pt—contrast 12pt with 24pt or 36pt.
- **Contrast multiple properties:** Size AND weight AND color, not just one
- **Create clear hierarchy:** One focal point, clear secondary elements, everything else recedes
- **Test with squint:** Squint at the design. The hierarchy should still be visible.
- **Remove competing elements:** If two things fight for attention, one must win decisively

### For SVG Charts Specifically
- Title: 2x or larger than body text (e.g., 40px vs 16px)
- Primary data: thick strokes (4-5px). Secondary/reference data: thin strokes (1-2px)
- Active state vs inactive: full opacity vs 30% opacity
- Actual vs projected: solid line vs dashed line (obvious dash pattern, not subtle)
- Key insight: highlighted color. Context: muted/gray

---

## Principle Interactions

### Proximity + Alignment
Group related items (proximity) AND align them to a common edge (alignment). These reinforce each other.

### Repetition + Contrast
Repeat most elements for unity, then break the pattern for one focal point. The contrast gains power from the consistency around it.

### When Principles Conflict
1. **Proximity trumps alignment** — Don't spread related items apart just to align them with distant elements
2. **Contrast trumps repetition** — Break consistency to create necessary hierarchy
3. **Alignment supports proximity** — Use alignment to reinforce groupings

---

## Critique Checklist

Before finalizing a visualization, verify:

### Proximity
- [ ] Related items are grouped together
- [ ] Unrelated items have clear separation
- [ ] Labels are adjacent to what they describe
- [ ] White space is organized, not scattered

### Alignment
- [ ] Every element aligns with something else
- [ ] One dominant alignment system (not mixed)
- [ ] Strong invisible lines connect elements
- [ ] Any alignment breaks are dramatic and intentional

### Repetition
- [ ] Consistent styling across similar elements
- [ ] Clear visual rhythm and pattern
- [ ] Limited color palette, reused systematically
- [ ] Typography hierarchy is consistent

### Contrast
- [ ] Clear visual hierarchy (primary → secondary → tertiary)
- [ ] Title/headline dramatically larger than body
- [ ] Key data stands out from context
- [ ] No "wimpy" differences—all contrasts are bold
