# Image Generation Prompting Reference

Extended reference for crafting effective Imagen prompts. See SKILL.md for quick reference.

## Source

Based on Max Woolf's research: https://minimaxir.com/2025/11/nano-banana-prompts/

## Core Principles

### 1. Structure Over Prose

**Bad:**
```
I want a picture of a sunset over mountains with warm colors and some clouds in the sky,
maybe with a lake in the foreground reflecting the light.
```

**Good:**
```
Sunset over mountain range.

Requirements:
- Warm color palette: oranges, pinks, purples
- Cirrus clouds in upper third of frame
- Still lake in foreground with reflections
- Golden hour lighting
```

### 2. CAPS for Constraints

The model pays more attention to CAPITALIZED requirements:

```
Professional headshot.

Aspects that MUST be followed EXACTLY:
- Subject MUST be centered in frame
- Background MUST be solid neutral gray
- Lighting MUST be soft and even
```

### 3. Hex Colors Over Names

Color names are ambiguous. Hex codes are precise:

| Instead of | Use |
|------------|-----|
| "magenta" | `#FF00FF` |
| "teal" | `#008080` |
| "coral" | `#FF7F50` |
| "navy blue" | `#000080` |

Example:
```
Abstract geometric pattern.

Color requirements:
- Primary: #E8E557 (bright yellow)
- Secondary: #4ECDC4 (teal)
- Background: #0F2323 (dark green)
```

### 4. Composition Rules

Use photography/design terminology:

| Term | Effect |
|------|--------|
| "rule of thirds" | Subject at intersection points |
| "negative space" | Empty areas for balance |
| "depth of field" | Blurred background |
| "leading lines" | Lines drawing eye to subject |
| "symmetrical composition" | Balanced, formal feel |
| "dynamic angle" | Energy, movement |

### 5. Style Elevators

Aspirational references improve quality:

**Publication targets:**
- "Pulitzer Prize-winning photograph"
- "National Geographic cover"
- "Vanity Fair portrait"
- "Architectural Digest feature"

**Camera/technical specs:**
- "Canon EOS R5, 85mm f/1.4"
- "Hasselblad medium format"
- "4K cinematic still"
- "DSLR with macro lens"

**Lighting descriptors:**
- "neutral diffuse 3PM lighting"
- "golden hour backlight"
- "studio three-point lighting"
- "dramatic Rembrandt lighting"

### 6. Negative Constraints

Explicitly exclude unwanted elements:

```
Do not include:
- Any text, watermarks, or logos
- People in frame
- Modern elements (cars, phones, power lines)
- Oversaturated colors
```

## Template Library

### Professional Headshot

```
Professional corporate headshot of [description].

Aspects that MUST be followed EXACTLY:
- Shot from shoulders up, centered in frame
- Neutral background with soft gradient
- Natural lighting from 45-degree angle
- Sharp focus on eyes, slight background blur
- Professional, approachable expression

Vanity Fair executive portrait style, Canon EOS R5, 85mm f/1.4.

Do not include any text, logos, props, or distracting elements.
```

### Product Photography

```
Professional product photo of [product].

Aspects that MUST be followed EXACTLY:
- Product centered on pure white background (#FFFFFF)
- Studio lighting with soft shadows
- High resolution, commercial quality
- [angle] view showing [key features]

Commercial advertising photography, Hasselblad H6D.

Do not include any text, watermarks, or additional objects.
```

### Conceptual Illustration

```
[Concept] represented as visual metaphor.

Aspects that MUST be followed EXACTLY:
- Clear visual hierarchy with [main element] prominent
- Color palette: [colors with hex codes]
- [Composition style] composition
- Abstract/stylized treatment, not photorealistic

Editorial illustration for Harvard Business Review.

Do not include any text or literal representations.
```

### Presentation Hero Image

```
Hero image for presentation about [topic].

Aspects that MUST be followed EXACTLY:
- Wide aspect ratio (16:9)
- Clear focal point in [position]
- Ample negative space for text overlay on [side]
- Color scheme: [brand colors with hex]
- Professional, modern aesthetic

Corporate presentation design, clean and impactful.

Do not include any text, busy patterns, or distracting details.
```

### Abstract Background

```
Abstract background pattern for [use case].

Aspects that MUST be followed EXACTLY:
- Seamless/tileable design
- Color palette limited to: [hex codes]
- Subtle, non-distracting pattern
- [Style] aesthetic (geometric/organic/gradient)

Modern digital art, suitable for professional context.

Do not include any recognizable objects, faces, or text.
```

## ITV Brand Prompts

When composing with `itv-styling`, use these brand-aligned patterns:

### ITV Presentation Image

```
Corporate presentation image for broadcast media company.

Aspects that MUST be followed EXACTLY:
- Dark background #0F2323
- Accent elements in #E8E557 (yellow) or #4ECDC4 (teal)
- Clean, modern, premium aesthetic
- Ample space for text overlay
- Professional broadcast industry feel

High-end corporate photography, sleek and confident.

Do not include busy patterns, off-brand colors, or cluttered elements.
```

### ITV Data Visualization Background

```
Abstract background for data visualization.

Aspects that MUST be followed EXACTLY:
- Base color #0F2323 (dark green)
- Subtle geometric or data-inspired patterns
- Gradient accents using #4ECDC4 at 20% opacity
- Clean negative space in center for chart overlay

Modern data design aesthetic, premium feel.

Do not include any actual numbers, text, or specific chart elements.
```

## Limitations and Workarounds

### Style Transfer

**Doesn't work:**
```
Studio Ghibli style landscape
Pixar-style character
Van Gogh style painting
```

**Workaround:** Describe the style structurally:
```
Animated landscape with soft watercolor textures.

Aspects that MUST be followed EXACTLY:
- Hand-painted appearance with visible brushstrokes
- Soft, dreamy color palette
- Simplified, stylized shapes
- Whimsical, fantastical atmosphere
```

### Text in Images

Text generation is unreliable. Instead:
1. Generate image without text
2. Add text as overlay in image editor or presentation software

### Exact Positioning

Precise placement is difficult. Use:
- Compositional rules ("rule of thirds", "centered")
- Relative positions ("in the foreground", "upper left quadrant")
- Iterate with refinement prompts

### Consistency Across Images

For series of related images:
- Use identical style/composition sections
- Specify exact colors with hex codes
- Use edit mode to refine from a base image

## Iteration Patterns

### Draft → Refine

1. Generate with Flash model for speed
2. Review, identify issues
3. Use edit mode with specific refinements:
   ```
   Make the lighting warmer, increase contrast, move subject slightly left
   ```

### Variation Exploration

Generate multiple variations by tweaking one element:
- Same subject, different angles
- Same composition, different color palettes
- Same style, different subjects
