# nb2md - Jupyter Notebook to Markdown Converter

A Python tool to convert Jupyter notebooks to markdown format compatible with mkslides and the LUISS template.

## Features

- Converts Jupyter notebooks (`.ipynb`) to markdown (`.md`)
- Automatically formats code cells with proper syntax highlighting
- Captures and formats cell outputs in `<pre class="code-output"><code>` blocks
- Creates slide separators (`---`) at heading level 2 (`##`)
- Wraps content in `<div class="content-center">` for proper styling
- Preserves all markdown formatting, HTML, and inline styles
- **Supports cell tags** for special slide states and layouts:
  - `front` → Adds `<!-- .slide: data-state="front hide-controls" -->`
  - `break-green` → Adds `<!-- .slide: data-state="break-green hide-controls" -->`
  - `break-blue` → Adds `<!-- .slide: data-state="break-blue hide-controls" -->`
  - `toc-blue` → Adds `<!-- .slide: data-state="toc-blue hide-controls" -->`
  - `auto-animate` → Adds `<!-- .slide: data-auto-animate -->` for Reveal.js auto-animate transitions (requires `slide` tag too)
  - `col` → Creates column layout (see Column Layouts section)
  - `center` → Horizontally centers the cell content
  - `slide` → Forces a new slide to start at this cell (works with any cell type)

## Installation

No additional dependencies required beyond Python 3.6+. The tool uses only standard library modules.

## Usage

### Command Line

Basic usage:
```bash
python nb2md/nb2md.py path/to/notebook.ipynb
```

This will create `notebook.md` in the same directory as the input notebook.

Specify output path:
```bash
python nb2md/nb2md.py path/to/notebook.ipynb -o output/path/slides.md
```

### As a Python Module

```python
from nb2md import NotebookConverter

# Create converter
converter = NotebookConverter('path/to/notebook.ipynb')

# Convert and save
output_path = converter.save('output.md')
print(f"Saved to: {output_path}")

# Or get the markdown as a string
markdown_content = converter.convert()
```

## Example

Convert the P05-Python-Iteration notebook:
```bash
python nb2md/nb2md.py src/P05-Python-Iteration.ipynb
```

This creates `src/P05-Python-Iteration.md` ready to be processed by mkslides.

## Output Format

### Slide Grouping
- Cells are automatically grouped into slides
- A new slide starts when:
  - A markdown cell begins with `##` (heading level 2), OR
  - A cell has Jupyter's native `slide_type='slide'` metadata, OR
  - A cell has the `slide` tag
- All cells following a slide-starting cell are grouped together until the next slide separator
- The title (h1, h2, or h3) from the first cell is extracted and used as the slide heading
- All content within a slide is wrapped in `<div class="content-center">`

### Regular Slides
```markdown
## Slide Title

<div class="content-center">

Markdown content from first cell (after title)...

More markdown content from subsequent cells...

```python
# Code from code cells
print("Hello, World!")
```

<pre class="code-output"><code>Hello, World!</code></pre>

</div>
```

### Special Slides (with tags)
Slides with special tags (`front`, `break-green`, `break-blue`, `toc-blue`) are NOT wrapped in `<div class="content-center">` and preserve their original structure:

```markdown
<!-- .slide: data-state="front hide-controls" -->

<div id="title">Title</div>
<div id="subtitle">Subtitle</div>
<div id="date">Date</div>
```

### Complete Example
```markdown
---
title: "Notebook Title"
---

---

<!-- .slide: data-state="front hide-controls" -->

<div id="title">My Presentation</div>
<div id="subtitle">Introduction to Python</div>

---

## First Topic

<div class="content-center">

Content from multiple cells grouped together...

```python
code_example = "grouped with content"
```

<pre class="code-output"><code>grouped with content</code></pre>

</div>

---

## Second Topic

<div class="content-center">

More content...

</div>
```

## Compatibility

The generated markdown is compatible with:
- mkslides
- reveal.js (via mkslides)
- LUISS custom template

## Using Cell Tags

In Jupyter notebooks, you can add tags to cells to control their appearance in the generated slides:

1. **In Jupyter Notebook/Lab**: 
   - Click on a cell
   - Open the cell toolbar (View → Cell Toolbar → Tags)
   - Add tags like `front`, `break-green`, `break-blue`, `toc-blue`, `col`, `center`, or `slide`

2. **Example**: Tag the first cell with `front` to create a title slide with the front page styling

The converter will automatically detect these tags and add the appropriate slide state comments.

## Column Layouts

Use the `col` tag to create multi-column layouts within a slide:

1. **How it works**:
   - Tag a cell with `col` to start a new column
   - All cells following that cell (until the next `col` tag or slide separator) are included in that column
   - Each column is wrapped in `<div class="col">`

2. **Example**:
   ```
   Cell 1: ## Two Columns (markdown, no tag)
   Cell 2: Content for first column (markdown, tag: col)
   Cell 3: More content for first column (markdown, no tag)
   Cell 4: Content for second column (markdown, tag: col)
   ```
   
   This generates:
   ```markdown
   ## Two Columns
   
   <div class="content-center">
   
   <div class="col">
   
   Content for first column
   
   More content for first column
   
   </div>
   
   <div class="col">
   
   Content for second column
   
   </div>
   
   </div>
   ```

## Centering Content

Use the `center` tag to horizontally center content within a cell:

1. **How it works**:
   - Tag a cell with `center`
   - The cell content will be wrapped in `<div style="text-align: center;">`
   - Works with both markdown and code cells

2. **Example**:
   ```
   Cell with tag "center": This text will be centered
   ```
   
   Generates:
   ```markdown
   <div style="text-align: center;">
   
   This text will be centered
   
   </div>
   ```

## Auto-Animate Transitions

Use the `auto-animate` tag to enable Reveal.js auto-animate transitions between consecutive slides:

1. **How it works**:
   - Add the `auto-animate` tag to **any cell** in a slide (title cell, column cell, etc.)
   - Also add the `slide` tag to ensure the cell starts a new slide
   - The converter will add `<!-- .slide: data-auto-animate -->` to the slide
   - Titles on auto-animate slides automatically get `data-id="title"` to prevent blinking
   - Reveal.js will automatically animate matching elements between consecutive auto-animate slides
   - You can add `data-id` attributes to other elements for smoother transitions

2. **Example**:
   ```
   Cell 1 - Title (tags: slide):
   ## Animation Demo (slide 1)
   
   Cell 2 - Image (tags: auto-animate, col):
   <img src="image.png" style="height: 100px;" />
   
   Cell 3 - Title (tags: slide):
   ## Animation Demo (slide 2)
   
   Cell 4 - Image (tags: auto-animate, col):
   <img src="image.png" style="height: 400px;" />
   
   <div class="col">
   <img src="image.png" style="height: 400px;" />
   </div>
   ```
   
   The image will smoothly grow from 100px to 400px when advancing to the next slide.

3. **Tips**:
   - Use matching structure between slides for best results
   - Add `data-id` attributes to titles if they change between slides to prevent "blinking"
   - Auto-animate works with any CSS property change (size, position, color, etc.)

## Notes

- Empty cells are automatically skipped
- The first cell doesn't get a slide separator before it
- Code outputs support: print statements, return values, and error tracebacks
- ANSI color codes in error messages are automatically cleaned
- Cell tags are read from the cell metadata and converted to slide state comments
- Multiple tags can be combined (e.g., `col` and `center` together)
