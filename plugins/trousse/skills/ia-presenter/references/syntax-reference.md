# iA Presenter Syntax Reference

Comprehensive reference from official iA documentation.

## Text Formatting

| Syntax | Result |
|--------|--------|
| `**bold**` or `__bold__` | **bold** |
| `*italic*` or `_italic_` | *italic* |
| `~~strikethrough~~` | ~~strikethrough~~ |
| `==highlight==` | highlighted text |
| `100m^2` | superscript (100m²) |
| `x~z` | subscript |
| `^(a+b)^` | complex superscript |
| `~y,z~` | complex subscript |
| `` `code` `` | inline code |

## Line Breaks

```markdown
Twinkle, Twinkle Little Bat\
How I wonder what you're at!
```
Use `\` at end of line for a line break within a paragraph.

## Comments

```markdown
// This is a comment — only you see it
```

## Headings & Their Purposes

| Heading | Use For |
|---------|---------|
| `# H1` | Cover slide title (presentation title) |
| `## H2` | Centered section title (major sections) |
| `### H3` | Subsection heading |
| `#### H4` | Caption heading (pairs with images) |

## Visibility Rules

| Element | Default | To Make Visible |
|---------|---------|-----------------|
| Headings | Visible | — |
| Paragraphs | Speaker notes | Prefix with `⇥` (tab) |
| Lists | Speaker notes | Prefix each item with `⇥` |
| Blockquotes | Speaker notes | Prefix with `⇥` |
| Images | Visible | — |
| Tables | Visible | — |
| Code blocks | Visible | — |

### Visible Lists
```markdown
⇥- [ ] Milk
⇥- Green
⇥1. Red
```

### Visible Blockquotes
```markdown
⇥> First level quote
⇥>
⇥> > Nested quote
```

### Definition Lists
```markdown
⇥Markdown
⇥: A lightweight markup language with plain text formatting syntax.
⇥: A deliberate reduction in the selling price of retail merchandise.
```

## Kickers (Small Text Above Title)

Press tab, then type text directly above a title:
```markdown
⇥Small kicker text
# Main Title
```

## Slides

### Slide Separation
```markdown
---
```
Three dashes on their own line.

### Cell Structure

Content separated by **blank lines** goes into different cells:
```markdown
### Title

Image or text here
```
This creates 2 cells. One element per cell usually looks better.

**Same cell** (no blank line between):
```markdown
### Title
⇥Subtitle directly below
```

## Layouts

Presenter auto-selects layouts based on:
- Number of visual blocks (cells)
- Types of graphics
- First heading level of each block
- Order of blocks

| Layout | Triggered By |
|--------|--------------|
| Cover | H1 title |
| Section | H2 centered |
| Split (2-3 cols) | 2-3 elements separated by blank lines |
| Grid | 4+ elements |
| Caption | H4 + image |

**Max columns:** 3 elements side by side.

**Grid:** 4+ elements automatically arrange in grid.

## Images

### Basic Syntax

Content Blocks (preferred):
```markdown
/assets/image-name.png

https://source.net/image-name.jpeg
```

Standard Markdown:
```markdown
![Alt text](image-name.png)
```

### Image Folders

| Folder | Purpose |
|--------|---------|
| `/assets/` | Graphics you add to a presentation |
| `/Theme/` | Graphics bundled with a theme |

### Image Options

Add on lines below the image path:

```markdown
/Theme/image1.jpg
size: contain
x: right
y: bottom
background: true
filter: darken
opacity: 50%
```

| Option | Values |
|--------|--------|
| `size:` | `contain`, `cover` |
| `x:` | `left`, `center`, `right` |
| `y:` | `top`, `center`, `bottom` |
| `background:` | `true` (puts behind other elements) |
| `filter:` | `lighten`, `darken`, `grayscale`, `sepia`, `blur` |
| `opacity:` | `0%` to `100%` |
| `Class:` | CSS class from custom theme |
| `title:` | Caption/alt text |

### Image Captions

Use H4 heading with image:
```markdown
#### Caption introducing the image

/assets/photo.jpg
```
Or image first:
```markdown
/assets/photo.jpg

#### Caption below the image
```

## Videos

Same syntax as images:
```markdown
/assets/video.mp4

https://youtube.com/watch?v=xxx
```

Supports: `.mp4`, `.mov`, YouTube links.

## Tables

```markdown
| Name  | Price | Tax |
|-------|------:|:---:|
| Apple | $1.00 | 5%  |
| Pear  | $1.50 | 5%  |
```

- Alignment: `:--` left, `--:` right, `:-:` center
- Merge cells: add `|` at end of cell

## Code Blocks

````markdown
```swift
func hello() {
    print("Hello!")
}
```
````

Specify language after opening backticks for syntax highlighting.

## Math (LaTeX)

Inline:
```markdown
An equation $x+y^2$ within text.
```

Block:
```markdown
$$\frac{1}{n} \sum_{i=1}^{n} x_i$$
```

Uses KaTeX for rendering.

## Footnotes

Inline:
```markdown
This has a footnote[^The footnote text goes here.] in the sentence.
```

Reference-style:
```markdown
This has a footnote[^1] in the sentence.

[^1]: The footnote text.
```

Footnotes appear at the bottom of the slide (if layout allows).

## Citations

```markdown
According to research[p. 23][#Doe:2006], this is true.

[#Doe:2006]: Doe, J. (2006). *Research Paper*. Publisher.
```

## Links

Inline:
```markdown
This is an [inline link](https://example.com).
```

Reference:
```markdown
This is a [reference link][1].

[1]: https://example.com
```

## File Format

`.iapresenter` is a bundle (directory):

```
Presentation.iapresenter/
├── assets/          # Your images/videos
├── info.json        # Metadata
└── text.md          # Markdown content
```

**info.json:**
```json
{
  "creatorIdentifier": "net.ia.presenter",
  "net.ia.presenter": {},
  "transient": false,
  "type": "net.daringfireball.markdown",
  "version": 2
}
```

The `.iapresenter` file is essentially a `.zip` containing these files.

## Custom Themes

Themes consist of:
- CSS definitions
- Presets (CSS variables)
- Custom fonts
- Theme images
- `template.json` and `presets.json`

### Layout CSS Classes

| Layout | Container Class | Content Class |
|--------|----------------|---------------|
| Cover | `.cover-container` | `.layout-cover` |
| Title | `.title-container` | `.layout-title` |
| Section | `.section-container` | `.layout-section` |
| Split | `.v-split-container` | `.layout-v-split` |
| Grid | `.grid-container` | `.layout-grid` |
| Caption | `.caption-container` | `.layout-caption` |
| Default | `.default-container` | `.layout-default` |

Grid also has: `.grid-items-2`, `.grid-items-3`, `.grid-items-4`, etc.

### Appearance Classes

- `.light` — light mode
- `.dark` — dark mode

### Responsive Breakpoint

```css
@media (min-width: 768px) {
  /* Desktop styles */
}
```
Default CSS applies to mobile.
