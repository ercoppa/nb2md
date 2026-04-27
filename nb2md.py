#!/usr/bin/env python3
"""
Jupyter Notebook to Markdown Converter for mkslides
Converts Jupyter notebooks to markdown format compatible with mkslides and LUISS template.
"""

import json
import sys
import argparse
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple


class NotebookConverter:
    """Convert Jupyter notebooks to mkslides-compatible markdown."""
    
    def __init__(self, notebook_path: str):
        """
        Initialize converter with notebook path.
        
        Args:
            notebook_path: Path to the Jupyter notebook file
        """
        self.notebook_path = Path(notebook_path)
        if not self.notebook_path.exists():
            raise FileNotFoundError(f"Notebook not found: {notebook_path}")
        
        with open(self.notebook_path, 'r', encoding='utf-8') as f:
            self.notebook = json.load(f)
        
        self.cells = self.notebook.get('cells', [])
    
    def _get_cell_tags(self, cell: Dict[str, Any]) -> List[str]:
        """
        Get tags from a cell's metadata.
        
        Args:
            cell: Notebook cell dictionary
            
        Returns:
            List of tag strings
        """
        metadata = cell.get('metadata', {})
        return metadata.get('tags', [])
    
    def _is_slideshow_fragment(self, cell: Dict[str, Any]) -> bool:
        """
        Check if a cell has slideshow fragment metadata.
        
        Args:
            cell: Notebook cell dictionary
            
        Returns:
            True if cell has slideshow slide_type set to 'fragment'
        """
        metadata = cell.get('metadata', {})
        slideshow = metadata.get('slideshow', {})
        return slideshow.get('slide_type') == 'fragment'
    
    def _get_slide_state_comment(self, tags: List[str]) -> str:
        """
        Generate slide state comment based on cell tags.
        
        Args:
            tags: List of cell tags
            
        Returns:
            Slide state comment or empty string
        """
        if 'auto-animate' in tags:
            return '<!-- .slide: data-auto-animate -->\n\n'
        elif 'front' in tags:
            return '<!-- .slide: data-state="front hide-controls" -->\n\n'
        elif 'break-green' in tags:
            return '<!-- .slide: data-state="break-green hide-controls" -->\n\n'
        elif 'break-blue' in tags:
            return '<!-- .slide: data-state="break-blue hide-controls" -->\n\n'
        elif 'toc-blue' in tags:
            return '<!-- .slide: data-state="toc-blue hide-controls" -->\n\n'
        return ''
    
    def _process_markdown_cell(self, cell: Dict[str, Any]) -> str:
        """
        Process a markdown cell.
        
        Args:
            cell: Notebook cell dictionary
            
        Returns:
            Formatted markdown string
        """
        source = cell.get('source', [])
        if isinstance(source, list):
            content = ''.join(source)
        else:
            content = source
        
        # Get tags and slide state comment
        tags = self._get_cell_tags(cell)
        slide_state = self._get_slide_state_comment(tags)

        # Map title/subtitle/date style tags to template-specific ids
        title_id_map = {
            'title': 'title',
            'title-2': 'title-2',
            'subtitle': 'subtitle',
            'subtitle-2': 'subtitle-2',
            'date': 'date',
        }
        title_id = None
        for tag in tags:
            if tag in title_id_map:
                title_id = title_id_map[tag]
                break

        if title_id:
            # Remove any markdown or HTML heading markup inside title cells
            content_no_headings = self._strip_heading_markup(content).strip()
            return slide_state + f"<div id=\"{title_id}\">{content_no_headings}</div>"

        # Check if this cell has special tags that shouldn't be wrapped
        special_tags = {'front', 'break-green', 'break-blue', 'toc-blue'}
        has_special_tag = bool(set(tags) & special_tags)
        
        # Wrap content in content-center div for proper styling
        if content.strip().startswith('##') or has_special_tag:
            # This is a slide title or special slide, don't wrap it
            return slide_state + content.strip()
        else:
            # Regular content, wrap in content-center
            return slide_state + f"<div class=\"content-center\">\n\n{content.strip()}\n\n</div>"
    
    def _process_code_cell(self, cell: Dict[str, Any]) -> str:
        """
        Process a code cell with its output.
        
        Args:
            cell: Notebook cell dictionary
            
        Returns:
            Formatted markdown string with code and output
        """
        source = cell.get('source', [])
        if isinstance(source, list):
            code = ''.join(source)
        else:
            code = source
        
        outputs = cell.get('outputs', [])
        
        # Get tags and slide state comment
        tags = self._get_cell_tags(cell)
        slide_state = self._get_slide_state_comment(tags)
        
        # Build the markdown
        result = slide_state + "<div class=\"content-center\">\n\n"
        
        # Add code block
        result += f"```python\n{code.strip()}\n```\n"
        
        # Process outputs if any
        if outputs:
            output_text = self._extract_output_text(outputs)
            if output_text:
                result += f"\n<pre class=\"code-output\"><code>{output_text}</code></pre>\n"
        
        result += "\n</div>"
        
        return result
    
    def _extract_output_text(self, outputs: List[Dict[str, Any]]) -> str:
        """
        Extract text from cell outputs.
        
        Args:
            outputs: List of output dictionaries
            
        Returns:
            Combined output text
        """
        output_parts = []
        
        for output in outputs:
            output_type = output.get('output_type', '')
            
            if output_type == 'stream':
                # Standard output (print statements)
                text = output.get('text', [])
                if isinstance(text, list):
                    output_parts.append(''.join(text))
                else:
                    output_parts.append(text)
            
            elif output_type == 'execute_result':
                # Return value of cell
                data = output.get('data', {})
                if 'text/plain' in data:
                    text = data['text/plain']
                    if isinstance(text, list):
                        output_parts.append(''.join(text))
                    else:
                        output_parts.append(text)
            
            elif output_type == 'error':
                # Error output
                traceback = output.get('traceback', [])
                if traceback:
                    # Clean ANSI codes from traceback
                    import re
                    clean_traceback = []
                    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
                    for line in traceback:
                        clean_traceback.append(ansi_escape.sub('', line))
                    output_parts.append('\n'.join(clean_traceback))
            
            elif output_type == 'display_data':
                # Display data (images, etc.)
                data = output.get('data', {})
                if 'text/plain' in data:
                    text = data['text/plain']
                    if isinstance(text, list):
                        output_parts.append(''.join(text))
                    else:
                        output_parts.append(text)
        
        return ''.join(output_parts).strip()
    
    def _get_cell_content(self, cell: Dict[str, Any]) -> str:
        """
        Get the text content from a cell.
        
        Args:
            cell: Notebook cell dictionary
            
        Returns:
            Cell content as string
        """
        source = cell.get('source', [])
        if isinstance(source, list):
            return ''.join(source)
        return source
    
    def _extract_title(self, content: str) -> Optional[str]:
        """
        Extract h1, h2, or h3 title from markdown content.
        
        Args:
            content: Markdown content
            
        Returns:
            Title text without # markers, or None if no title found
        """
        # Match h1, h2, or h3 at the start of content
        match = re.match(r'^(#{1,3})\s+(.+?)\s*$', content.strip(), re.MULTILINE)
        if match:
            return match.group(2).strip()
        return None

    def _strip_heading_markup(self, content: str) -> str:
        """Remove markdown and HTML heading markup (h1–h6) from content.

        This is used for cells that are mapped to template-specific title
        elements (e.g., tagged with "title", "title-2", "subtitle",
        "subtitle-2", or "date") so that the emitted markdown/HTML does not
        contain redundant heading markup.
        """
        text = content

        # Strip markdown headings at the start of lines: #, ##, ..., ######
        text = re.sub(r"^\s*#{1,6}\s*(.+?)\s*$", r"\1", text, flags=re.MULTILINE)

        # Strip HTML headings <h1>..</h1> to <h6>..</h6>, keeping inner text
        text = re.sub(r"<h[1-6][^>]*>(.*?)</h[1-6]>", r"\1", text, flags=re.IGNORECASE | re.DOTALL)

        return text
    
    def _is_slide_separator(self, cell: Dict[str, Any]) -> bool:
        """
        Check if a cell should trigger a new slide.
        
        Args:
            cell: Notebook cell dictionary
            
        Returns:
            True if this should start a new slide
        """
        # Check Jupyter's native slideshow metadata
        metadata = cell.get('metadata', {})
        slideshow = metadata.get('slideshow', {})
        slide_type = slideshow.get('slide_type', '')
        
        # slide_type='slide' means start a new slide
        if slide_type == 'slide':
            return True
        
        # Check if cell has 'slide' tag or any special template tag to force new slide
        tags = self._get_cell_tags(cell)
        if 'slide' in tags:
            return True

        # Special template slides (front, break, toc) should always start a new slide
        special_tags = {'front', 'break-green', 'break-blue', 'toc-blue'}
        if set(tags) & special_tags:
            return True
        
        # DO NOT automatically create new slides based on ## headings
        # Only the explicit tags/metadata above should trigger new slides
        
        return False
    
    def _group_cells_into_slides(self) -> List[List[Dict[str, Any]]]:
        """
        Group cells into slides based on slide separators.
        
        Returns:
            List of slides, where each slide is a list of cells
        """
        slides = []
        current_slide = []
        
        for cell in self.cells:
            # Skip hidden cells (omit from markdown entirely)
            if 'hide' in self._get_cell_tags(cell):
                continue
            # Skip empty cells
            source = cell.get('source', [])
            if not source or (isinstance(source, list) and not ''.join(source).strip()):
                continue
            
            # Check if this starts a new slide
            if self._is_slide_separator(cell) and current_slide:
                # Save current slide and start new one
                slides.append(current_slide)
                current_slide = [cell]
            else:
                current_slide.append(cell)
        
        # Add the last slide
        if current_slide:
            slides.append(current_slide)
        
        return slides
    
    def _group_cells_into_columns(self, cells: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[List[Dict[str, Any]]], List[Dict[str, Any]], str]:
        """
        Group cells into columns based on 'col' or 'column' tag.
        
        Args:
            cells: List of cells to group
            
        Returns:
            Tuple of (pre_column_cells, columns, post_column_cells, alignment) where:
            - pre_column_cells: cells before the first column tag
            - columns: list of columns, where each column is a list of cells
            - post_column_cells: cells after a 'no-column' tag
            - alignment: 'top' or 'center' for column alignment
        """
        pre_column_cells = []
        columns = []
        post_column_cells = []
        current_column = []
        in_columns = False
        after_columns = False
        alignment = 'center'  # Default alignment
        
        for cell in cells:
            tags = self._get_cell_tags(cell)
            
            if 'no-column' in tags:
                # Exit column mode
                if current_column:
                    columns.append(current_column)
                    current_column = []
                in_columns = False
                after_columns = True
                # Add the no-column cell to post_column_cells if it has content
                cell_content = self._get_cell_content(cell).strip()
                if cell_content:
                    post_column_cells.append(cell)
            elif 'top-col' in tags or 'top-column' in tags:
                # Start a new top-aligned column
                alignment = 'top'
                in_columns = True
                after_columns = False
                if current_column:
                    columns.append(current_column)
                # Start new column and include this cell if it has content
                cell_content = self._get_cell_content(cell).strip()
                if cell_content:
                    current_column = [cell]
                else:
                    current_column = []
            elif 'col' in tags or 'column' in tags:
                # Start a new center-aligned column
                in_columns = True
                after_columns = False
                if current_column:
                    columns.append(current_column)
                # Start new column and include this cell if it has content
                cell_content = self._get_cell_content(cell).strip()
                if cell_content:
                    current_column = [cell]
                else:
                    current_column = []
            else:
                if after_columns:
                    post_column_cells.append(cell)
                elif in_columns:
                    current_column.append(cell)
                else:
                    # Before any column tag
                    pre_column_cells.append(cell)
        
        # Add the last column
        if current_column:
            columns.append(current_column)
        
        return pre_column_cells, columns, post_column_cells, alignment

    def _has_table_row_tags(self, cells: List[Dict[str, Any]]) -> bool:
        """Check if any cells have table-row tags."""
        for cell in cells:
            tags = self._get_cell_tags(cell)
            if 'table-row' in tags:
                return True
        return False

    def _render_table_columns(self, columns: List[List[Dict[str, Any]]], alignment: str) -> str:
        """Render columns as an HTML table for row-aligned content.
        
        Each cell's content is split into individual lines/items that become separate table rows.
        
        Args:
            columns: List of columns, where each column is a list of cells
            alignment: 'top' or 'center' for vertical alignment
            
        Returns:
            HTML table string
        """
        if not columns:
            return ""
        
        # Extract and split content from each column into row items
        # Also collect any br tags from cells (take the maximum)
        column_rows = []
        max_br_count = 0
        
        for col_cells in columns:
            col_items = []
            for cell in col_cells:
                # Check for br tags before formatting
                tags = self._get_cell_tags(cell)
                br_count = self._get_br_count(tags)
                max_br_count = max(max_br_count, br_count)
                
                # Get raw content and format it manually for table cells
                # Don't use _format_cell_content as it adds br tags inline
                cell_type = cell.get('cell_type', '')
                if cell_type == 'markdown':
                    cell_content = self._get_cell_content(cell)
                    
                    # Normalize <br> tags to <br/> before processing
                    cell_content = re.sub(r'<br\s*/?\s*>', '<br/>', cell_content)
                    
                    content = self._separate_display_math(cell_content.strip())
                    content = self._escape_math_for_reveal_markdown(content)
                else:
                    content = ""
                
                if content:
                    # Split by empty lines (double newlines) to get separate rows
                    # This allows users to control row boundaries with blank lines
                    row_blocks = re.split(r'\n\s*\n', content.strip())
                    
                    for block in row_blocks:
                        block = block.strip()
                        if not block or block in ['<br/>', '<br>', '<br />']:
                            continue
                        
                        # Each block is a separate row
                        # Convert single newlines within the block to <br/> tags
                        # This preserves line breaks within the same row
                        # But don't double-convert if <br/> already exists
                        block = block.replace('\n', '<br/>')
                        
                        # Check if block starts with a list marker
                        has_list_marker = re.match(r'^[-*+]\s+', block) or re.match(r'^\d+\.\s+', block)
                        if has_list_marker:
                            # Remove markdown marker and wrap in bullet span
                            block = re.sub(r'^[-*+]\s+', '', block)
                            block = re.sub(r'^\d+\.\s+', '', block)
                            col_items.append(f'<span class="bullet">•</span> {block}')
                        else:
                            # No list marker, use plain text
                            col_items.append(block)
            column_rows.append(col_items)
        
        if not column_rows:
            return ""
        
        # Find maximum number of rows across all columns
        max_rows = max(len(items) for items in column_rows) if column_rows else 0
        
        # Build table structure
        align_class = "table-columns-top" if alignment == 'top' else "table-columns-center"
        table_parts = []
        table_parts.append(f'<table class="table-columns {align_class}">')
        table_parts.append('<tbody>')
        
        # Iterate through rows
        for row_idx in range(max_rows):
            table_parts.append('<tr>')
            
            # Iterate through columns
            for col_items in column_rows:
                if row_idx < len(col_items):
                    table_parts.append(f'<td>{col_items[row_idx]}</td>')
                else:
                    # Empty cell if this column doesn't have enough rows
                    table_parts.append('<td></td>')
            
            table_parts.append('</tr>')
        
        table_parts.append('</tbody>')
        table_parts.append('</table>')
        
        # Add any br tags after the table
        br_html = ""
        if max_br_count > 0:
            br_html = "\n\n" + ("<br/>\n" * max_br_count)
        
        return '\n'.join(table_parts) + br_html

    def _split_cells_into_column_blocks(self, cells: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Split slide cells into alternating normal-cell and columns-block segments.

        This enables multiple rows of columns on the same slide.

        Rules:
        - 'col'/'column' and 'top-col'/'top-column' start a column block (or a new column within it)
        - 'end-column' terminates the current columns block (row terminator)
        - 'no-column' terminates the current columns block too (kept for backwards compatibility)
        - 'table-row' marks cells that should align as rows across columns

        Returns:
            List of segments. Each segment is either:
            - {'type': 'cells', 'cells': [...]}
            - {'type': 'columns', 'columns': [[...], ...], 'alignment': 'top'|'center', 'use_table': bool}
        """
        segments: List[Dict[str, Any]] = []

        buffer_cells: List[Dict[str, Any]] = []
        columns: List[List[Dict[str, Any]]] = []
        current_column: List[Dict[str, Any]] = []
        in_columns = False
        alignment = 'center'

        def _flush_cells() -> None:
            nonlocal buffer_cells, segments
            if buffer_cells:
                segments.append({'type': 'cells', 'cells': buffer_cells})
                buffer_cells = []

        def _flush_columns() -> None:
            nonlocal columns, current_column, in_columns, alignment, segments
            if current_column:
                columns.append(current_column)
                current_column = []
            if columns:
                # Check if any cell in the columns has table-row tag
                use_table = False
                for col_cells in columns:
                    if self._has_table_row_tags(col_cells):
                        use_table = True
                        break
                segments.append({
                    'type': 'columns',
                    'columns': columns,
                    'alignment': alignment,
                    'use_table': use_table
                })
            columns = []
            current_column = []
            in_columns = False
            alignment = 'center'

        for cell in cells:
            tags = self._get_cell_tags(cell)

            if 'end-column' in tags or 'no-column' in tags:
                if in_columns:
                    _flush_columns()

                # Keep the marker cell itself if it has content
                cell_content = self._get_cell_content(cell).strip()
                if cell_content:
                    buffer_cells.append(cell)
                continue

            if 'top-col' in tags or 'top-column' in tags or 'col' in tags or 'column' in tags:
                # Starting a new column (and possibly a new columns block)
                if not in_columns:
                    _flush_cells()
                    in_columns = True

                if 'top-col' in tags or 'top-column' in tags:
                    alignment = 'top'

                if current_column:
                    columns.append(current_column)

                cell_content = self._get_cell_content(cell).strip()
                current_column = [cell] if cell_content else []
                continue

            if in_columns:
                current_column.append(cell)
            else:
                buffer_cells.append(cell)

        if in_columns:
            _flush_columns()
        _flush_cells()

        return segments
    
    def _get_fragment_index(self, cell: Dict[str, Any]) -> Optional[int]:
        """
        Extract fragment index from cell tags (e.g., 'fragment-index-2' -> 2).
        
        Args:
            cell: Notebook cell dictionary
            
        Returns:
            Fragment index as integer, or None if not found
        """
        tags = self._get_cell_tags(cell)
        for tag in tags:
            if tag.startswith('fragment-index-'):
                try:
                    index_str = tag.replace('fragment-index-', '')
                    return int(index_str)
                except ValueError:
                    pass
        return None
    
    def _group_cells_into_fragments_with_state(self, cells: List[Dict[str, Any]], in_fragment_mode: bool = False, current_fragment_step: Optional[int] = None, next_auto_fragment_step: int = 0) -> Tuple[List[Dict[str, Any]], bool, Optional[int], int]:
        """
        Group cells into fragments based on 'fragment' tag or slideshow metadata.
        
        Args:
            cells: List of cells to group
            
        Returns:
            Tuple of:
            - list of fragment dictionaries with 'cells', 'index', 'has_index', and 'force_fragment'
            - updated in_fragment_mode flag
            - current_fragment_step (fragment index to use for the current fragment region, if any)
            - next_auto_fragment_step (next available auto-assigned fragment index)
        """
        fragments = []
        
        for cell in cells:
            tags = self._get_cell_tags(cell)
            is_no_fragment = 'no-fragment' in tags
            is_fragment_mode_marker = 'fragment' in tags or self._is_slideshow_fragment(cell)
            fragment_index = self._get_fragment_index(cell)
            has_fragment_index = fragment_index is not None
            
            if is_no_fragment:
                # End fragment mode; this cell is treated as normal content (not a fragment)
                in_fragment_mode = False
                current_fragment_step = None
                cell_content = self._get_cell_content(cell).strip()
                if cell_content:
                    fragments.append({
                        'cells': [cell],
                        'index': None,
                        'has_index': False,
                        'force_fragment': False,
                    })
                continue
            
            # A cell with 'fragment' or 'fragment-index-N' starts a NEW fragment step.
            if is_fragment_mode_marker or has_fragment_index:
                in_fragment_mode = True
                if has_fragment_index:
                    current_fragment_step = fragment_index
                    if fragment_index is not None:
                        next_auto_fragment_step = max(next_auto_fragment_step, fragment_index + 1)
                else:
                    current_fragment_step = next_auto_fragment_step
                    next_auto_fragment_step += 1

            # While in fragment mode, every cell belongs to the CURRENT fragment step.
            force_fragment = in_fragment_mode
            
            cell_content = self._get_cell_content(cell).strip()
            if not cell_content:
                # Skip empty cells within the slide (they are already skipped globally,
                # but keep this safe for locally constructed cell lists).
                continue
            
            fragments.append({
                'cells': [cell],
                'index': current_fragment_step if force_fragment else None,
                'has_index': (current_fragment_step is not None) if force_fragment else False,
                'force_fragment': force_fragment,
            })
        
        return fragments, in_fragment_mode, current_fragment_step, next_auto_fragment_step

    def _group_cells_into_fragments(self, cells: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Backwards-compatible wrapper: group cells into fragments starting with fragment mode off."""
        fragments, _, _, _ = self._group_cells_into_fragments_with_state(
            cells,
            in_fragment_mode=False,
            current_fragment_step=None,
            next_auto_fragment_step=0,
        )
        return fragments
    
    def _extract_footnote_markers(self, cells: List[Dict[str, Any]]) -> List[str]:
        """
        Extract footnote markers from cells by looking for <sup>X</sup> patterns.
        
        Args:
            cells: List of cells to search
            
        Returns:
            List of unique markers found
        """
        markers = []
        marker_pattern = re.compile(r'<sup>([^<]+)</sup>')
        
        for cell in cells:
            content = self._get_cell_content(cell)
            matches = marker_pattern.findall(content)
            for match in matches:
                if match not in markers:
                    markers.append(match)
        
        return markers
    
    def _generate_footnote_marker(self, index: int) -> str:
        """
        Generate a default footnote marker based on index.
        
        Args:
            index: 0-based index of the footnote
            
        Returns:
            Marker string (e.g., "*", "**", "***")
        """
        return "*" * (index + 1)

    def _render_inline_markdown_for_raw_html(self, text: str) -> str:
        parts: List[str] = []
        code_spans: List[str] = []
        math_spans: List[str] = []

        i = 0
        while i < len(text):
            # Protect inline code spans
            if text[i] == '`':
                j = text.find('`', i + 1)
                if j != -1:
                    code_spans.append(text[i + 1 : j])
                    parts.append(f"\x00CODE{len(code_spans) - 1}\x00")
                    i = j + 1
                    continue
            
            # Protect inline math $...$
            if text[i] == '$' and (i + 1 < len(text) and text[i + 1] != '$'):
                j = i + 1
                while j < len(text):
                    if text[j] == '$' and (j + 1 >= len(text) or text[j + 1] != '$'):
                        # Found closing $
                        math_spans.append(text[i : j + 1])
                        parts.append(f"\x00MATH{len(math_spans) - 1}\x00")
                        i = j + 1
                        break
                    j += 1
                else:
                    # No closing $ found, treat as regular character
                    parts.append(text[i])
                    i += 1
                continue
            
            parts.append(text[i])
            i += 1

        rendered = ''.join(parts)
        
        # Convert markdown links [text](url) to HTML <a> tags
        rendered = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', rendered)
        
        rendered = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", rendered, flags=re.DOTALL)
        rendered = re.sub(r"__(.+?)__", r"<b>\1</b>", rendered, flags=re.DOTALL)
        rendered = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<i>\1</i>", rendered, flags=re.DOTALL)
        rendered = re.sub(r"(?<!_)_(?!_)(.+?)(?<!_)_(?!_)", r"<i>\1</i>", rendered, flags=re.DOTALL)

        for idx, code in enumerate(code_spans):
            rendered = rendered.replace(f"\x00CODE{idx}\x00", f"<code>{code}</code>")
        
        for idx, math in enumerate(math_spans):
            rendered = rendered.replace(f"\x00MATH{idx}\x00", math)

        return rendered

    def _replace_inline_code_in_alerts(self, html: str) -> str:
        """Convert inline backtick code inside alert divs to <code> spans.

        This is a safety net to ensure that, even when alert HTML is produced
        by different code paths, any `` `code` `` inside
        <div class="alert ..."> blocks becomes <code>code</code>,
        avoiding the issue that markdown is not processed inside raw HTML.
        """
        alert_div_pattern = re.compile(
            r'(<div\s+class="alert[^>]*>)(.*?)(</div>)',
            re.DOTALL
        )

        inline_code_pattern = re.compile(r"`([^`]+)`")

        def _sub_alert(match: re.Match) -> str:
            start, body, end = match.group(1), match.group(2), match.group(3)
            body = inline_code_pattern.sub(r"<code>\1</code>", body)
            # Convert markdown links [text](url) to HTML <a> tags
            body = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', body)
            body = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", body, flags=re.DOTALL)
            body = re.sub(r"__(.+?)__", r"<b>\1</b>", body, flags=re.DOTALL)
            body = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<i>\1</i>", body, flags=re.DOTALL)
            body = re.sub(r"(?<!_)_(?!_)(.+?)(?<!_)_(?!_)", r"<i>\1</i>", body, flags=re.DOTALL)
            return f"{start}{body}{end}"

        return alert_div_pattern.sub(_sub_alert, html)

    def _get_br_count(self, tags: List[str]) -> int:
        """Return the number of <br/> to append based on tags.

        Supported tags:
        - br (equivalent to br-1)
        - br-N where N is a positive integer

        If multiple br/br-N tags are present, the maximum N wins.
        """
        br_count = 0
        for tag in tags:
            if tag == 'br':
                br_count = max(br_count, 1)
                continue
            if tag.startswith('br-'):
                try:
                    n = int(tag.split('-', 1)[1])
                except ValueError:
                    continue
                if n > 0:
                    br_count = max(br_count, n)
        return br_count

    def _get_space_html(self, tags: List[str]) -> str:
        """Return an HTML snippet that adds vertical spacing based on tags.

        Supported tags:
        - space (equivalent to space-16px)
        - space-N (interpreted as pixels)
        - space-<value><unit> where unit is px, em, or rem (e.g., space-2em)
        
        If multiple space tags are present, the maximum pixel-equivalent wins when
        comparable. If units differ, the last parsed valid tag wins.
        """
        space_value: Optional[str] = None
        
        for tag in tags:
            if tag == 'space':
                space_value = '16px'
                continue
            if not tag.startswith('space-'):
                continue
            raw = tag.split('-', 1)[1].strip()
            if not raw:
                continue
            if raw.isdigit():
                space_value = f"{raw}px"
                continue
            if re.fullmatch(r"\d+(?:\.\d+)?(px|em|rem)", raw):
                space_value = raw
        
        if not space_value:
            return ''
        
        return f'\n<div style="height: {space_value};"></div>'

    def _get_padding_style(self, tags: List[str]) -> Optional[str]:
        """Return an inline style string for padding tags.

        Supported tags:
        - padding (adds 10px on all sides)
        - padding-top (adds 10px on top)
        - padding-bottom (adds 10px on bottom)
        """
        if 'padding' in tags:
            return 'padding: 10px;'

        styles: List[str] = []
        if 'padding-top' in tags:
            styles.append('padding-top: 10px;')
        if 'padding-bottom' in tags:
            styles.append('padding-bottom: 10px;')

        if not styles:
            return None

        return ' '.join(styles)

    def _separate_display_math(self, content: str) -> str:
        """Ensure display math blocks ($$ ... $$) are separated from surrounding text.

        Some markdown renderers can treat text immediately adjacent to display-math
        blocks as part of the same paragraph/block, which may cause the text to
        inherit centering/styling meant for display math.
        """
        lines = content.split('\n')
        out: List[str] = []
        in_display_math = False
        skip_following_blank_lines = False

        for idx, line in enumerate(lines):
            stripped = line.strip()

            if skip_following_blank_lines and stripped == '':
                continue
            if stripped != '':
                skip_following_blank_lines = False

            is_delimiter = stripped == '$$'

            if is_delimiter:
                if not in_display_math:
                    # Opening $$: ensure exactly one blank line before it if preceded by text.
                    if out and out[-1].strip() != '':
                        out.append('')
                    out.append('$$')
                    in_display_math = True
                    continue

                # Closing $$: never allow blank lines right before it (inside the block)
                while out and out[-1].strip() == '':
                    out.pop()
                out.append('$$')
                in_display_math = False

                # If there's more non-empty content after the block (and it's not another $$),
                # add exactly one blank line after the closing delimiter.
                j = idx + 1
                while j < len(lines) and lines[j].strip() == '':
                    j += 1
                if j < len(lines) and lines[j].strip() != '$$':
                    out.append('')
                    # Skip any notebook-provided blank lines that follow; we've normalized to one.
                    skip_following_blank_lines = True
                continue

            if in_display_math:
                # Inside $$...$$: drop all blank/whitespace-only lines.
                if stripped == '':
                    continue
                out.append(line)
                continue

            out.append(line)

        return '\n'.join(out)

    def _escape_math_for_reveal_markdown(self, content: str) -> str:
        parts = re.split(r'(```[\s\S]*?```)', content)
        out_parts: List[str] = []

        for part in parts:
            if part.startswith('```'):
                out_parts.append(part)
                continue

            placeholder_spans: List[str] = []

            def _stash_inline_code(m: re.Match) -> str:
                placeholder_spans.append(m.group(0))
                return f"@@NB2MD_INLINE_CODE_{len(placeholder_spans) - 1}@@"

            working = re.sub(r'`[^`]*`', _stash_inline_code, part)

            lines = working.split('\n')
            escaped_lines: List[str] = []
            in_display_math = False
            for line in lines:
                stripped = line.strip()
                if stripped == '$$':
                    in_display_math = not in_display_math
                    escaped_lines.append(line)
                    continue

                if in_display_math:
                    # Reveal.js markdown processing requires all backslashes to be doubled
                    line = line.replace('\\', '\\\\')
                    # After doubling, line breaks \\ become \\\\, add {} to prevent issues
                    if line.rstrip().endswith('\\\\'):
                        line = re.sub(r'\\\\\s*$', r'\\\\{}', line)
                    # Escape unescaped underscores/asterisks so marked doesn't treat
                    # them as emphasis delimiters before KaTeX processes subscripts.
                    line = re.sub(r'(?<!\\)_', r'\\_', line)
                    line = re.sub(r'(?<!\\)\*', r'\\*', line)
                escaped_lines.append(line)

            working = '\n'.join(escaped_lines)

            def _escape_inline_math(m: re.Match) -> str:
                inner = m.group(1)
                # Reveal.js markdown processing requires backslashes to be doubled
                inner = inner.replace('\\', '\\\\')
                # Escape unescaped underscores/asterisks so marked doesn't treat
                # them as emphasis delimiters before KaTeX processes subscripts.
                inner = re.sub(r'(?<!\\)_', r'\\_', inner)
                inner = re.sub(r'(?<!\\)\*', r'\\*', inner)
                return f"${inner}$"

            working = re.sub(r'(?<!\$)(?<!\\)\$([^\n$]+?)\$(?!\$)', _escape_inline_math, working)

            for i, original in enumerate(placeholder_spans):
                working = working.replace(f"@@NB2MD_INLINE_CODE_{i}@@", original)

            out_parts.append(working)

        return ''.join(out_parts)
    
    def _format_cell_content(self, cell: Dict[str, Any]) -> str:
        """
        Format a single cell's content without wrapping divs.
        
        Args:
            cell: Notebook cell dictionary
            
        Returns:
            Formatted content string
        """
        cell_type = cell.get('cell_type', '')
        cell_content = self._get_cell_content(cell)
        tags = self._get_cell_tags(cell)

        # Map title/subtitle/date style tags to template-specific ids
        title_id_map = {
            'title': 'title',
            'title-2': 'title-2',
            'subtitle': 'subtitle',
            'subtitle-2': 'subtitle-2',
            'date': 'date',
        }
        title_id = None
        for tag in tags:
            if tag in title_id_map:
                title_id = title_id_map[tag]
                break
        
        # Check for alert box tags
        alert_types = {
            'warning': ('alert-warning', 'WARNING'),
            'note': ('alert-note', 'NOTE'),
            'hint': ('alert-hint', 'HINT'),
            'recall': ('alert-recall', 'RECALL'),
            'error': ('alert-error', 'ERROR')
        }
        
        alert_type = None
        alert_class = None
        alert_title = None
        for tag, (css_class, title) in alert_types.items():
            if tag in tags:
                alert_type = tag
                alert_class = css_class
                alert_title = title
                break
        
        # Check if content should be centered
        should_center = 'center' in tags

        padding_style = self._get_padding_style(tags)
        br_count = self._get_br_count(tags)
        space_html = self._get_space_html(tags)
        
        if cell_type == 'markdown':
            content = self._separate_display_math(cell_content.strip())
            
            # Skip math escaping for alert boxes since they render as raw HTML
            if not alert_type:
                content = self._escape_math_for_reveal_markdown(content)

            # Title/subtitle/date style content: render to template-specific ids
            if title_id:
                # Strip any h1–h6 markdown or HTML markup from the content
                content_no_headings = self._strip_heading_markup(content).strip()
                content = f'<div id="{title_id}">{content_no_headings}</div>'
                if padding_style:
                    content = f'<div style="{padding_style}">\n\n{content}\n\n</div>'
                if br_count:
                    content += "\n\n" + ("<br/>\n" * br_count)
                if space_html:
                    content += space_html
                return content

            # Wrap in alert box if needed
            if alert_type:
                content = self._render_inline_markdown_for_raw_html(content)
                content = f'<div class="alert {alert_class}">{content}</div>'
            elif should_center and padding_style:
                content = f'<div class="cell-center" style="{padding_style}">\n\n{content}\n\n</div>'
                padding_style = None
            elif should_center:
                content = f'<div class="cell-center">\n\n{content}\n\n</div>'

            if padding_style:
                content = f'<div style="{padding_style}">\n\n{content}\n\n</div>'
            if br_count:
                content += "\n\n" + ("<br/>\n" * br_count)
            if space_html:
                content += space_html
            
            return content
        elif cell_type == 'code':
            # Format code cell without the outer content-center div
            code = cell_content
            outputs = cell.get('outputs', [])
            
            code_block = f"```python\n{code.strip()}\n```"
            
            if outputs:
                output_text = self._extract_output_text(outputs)
                if output_text:
                    code_block += f"\n\n<pre class=\"code-output\"><code>{output_text}</code></pre>"
            
            # Wrap in alert box if needed
            if alert_type:
                code_block = f'<div class="alert {alert_class}">\n\n{code_block}\n\n</div>'
            elif should_center and padding_style:
                code_block = f'<div class="cell-center" style="{padding_style}">\n\n{code_block}\n\n</div>'
                padding_style = None
            elif should_center:
                code_block = f'<div class="cell-center">\n\n{code_block}\n\n</div>'

            if padding_style:
                code_block = f'<div style="{padding_style}">\n\n{code_block}\n\n</div>'
            if br_count:
                code_block += "\n\n" + ("<br/>\n" * br_count)
            if space_html:
                code_block += space_html
            
            return code_block
        
        return ""
    
    def _process_slide(self, slide_cells: List[Dict[str, Any]]) -> str:
        """
        Process a slide (group of cells).
        
        Args:
            slide_cells: List of cells in this slide
            
        Returns:
            Formatted markdown for the slide
        """
        if not slide_cells:
            return ""
        
        # Separate footnote cells from regular cells
        footnote_cells = []
        regular_cells = []
        for cell in slide_cells:
            tags = self._get_cell_tags(cell)
            if 'footnote' in tags:
                footnote_cells.append(cell)
            else:
                regular_cells.append(cell)
        
        if not regular_cells:
            return ""
        
        # Check if any cell in the slide has auto-animate or special tags
        first_cell = regular_cells[0]
        first_cell_tags = self._get_cell_tags(first_cell)
        
        # Collect all tags from all cells to check for auto-animate
        all_slide_tags = set()
        for cell in regular_cells:
            all_slide_tags.update(self._get_cell_tags(cell))
        
        # Determine slide state from first cell (for special slides) or from any cell (for auto-animate)
        slide_state = self._get_slide_state_comment(first_cell_tags)
        
        # If no slide state from first cell, check if any cell has auto-animate
        if not slide_state and 'auto-animate' in all_slide_tags:
            slide_state = '<!-- .slide: data-auto-animate -->\n\n'
        
        # Check if this is a special slide (front, break, toc)
        special_tags = {'front', 'break-green', 'break-blue', 'toc-blue'}
        has_special_tag = bool(set(first_cell_tags) & special_tags)
        
        if has_special_tag:
            # Special slides: just process cells normally without grouping
            parts = []
            for cell in slide_cells:
                cell_type = cell.get('cell_type', '')
                if cell_type == 'markdown':
                    parts.append(self._process_markdown_cell(cell))
                elif cell_type == 'code':
                    parts.append(self._process_code_cell(cell))
            return '\n\n'.join(parts)
        
        # Regular slide: extract title and process content
        title = None
        cells_to_process = regular_cells
        
        # Try to extract title from first cell
        if regular_cells and regular_cells[0].get('cell_type') == 'markdown':
            first_content = self._get_cell_content(regular_cells[0])
            extracted_title = self._extract_title(first_content)
            if extracted_title:
                title = extracted_title
                # Remove the title line from first cell content
                lines = first_content.strip().split('\n')
                remaining_content = '\n'.join(lines[1:]).strip()
                
                # If there's remaining content, create a modified first cell
                if remaining_content:
                    modified_first_cell = regular_cells[0].copy()
                    modified_first_cell['source'] = remaining_content
                    cells_to_process = [modified_first_cell] + regular_cells[1:]
                else:
                    # Skip the first cell entirely
                    cells_to_process = regular_cells[1:]
        
        # Check if any cell has column tags
        has_columns = any(
            'col' in self._get_cell_tags(cell)
            or 'column' in self._get_cell_tags(cell)
            or 'top-col' in self._get_cell_tags(cell)
            or 'top-column' in self._get_cell_tags(cell)
            or 'no-column' in self._get_cell_tags(cell)
            or 'end-column' in self._get_cell_tags(cell)
            for cell in cells_to_process
        )
        
        # Build the slide
        result = slide_state
        
        if title:
            # Check if auto-animate is enabled to prevent title blinking
            has_auto_animate = 'auto-animate' in all_slide_tags
            if has_auto_animate:
                # Use HTML heading with data-id to prevent blinking during auto-animate
                result += f'<h2 data-id="title">{title}</h2>\n\n'
            else:
                result += f"## {title}\n\n"
        
        if cells_to_process:
            result += "<div class=\"content-center\">\n\n"

            open_fragment_index: Optional[int] = None

            def _close_open_fragment() -> None:
                nonlocal result, open_fragment_index
                if open_fragment_index is not None:
                    result += "</div>\n\n"
                    open_fragment_index = None

            def _emit_cell_content(content: str, fragment_index: Optional[int]) -> None:
                nonlocal result, open_fragment_index
                if fragment_index is None:
                    _close_open_fragment()
                    result += content + "\n\n"
                    return

                if open_fragment_index != fragment_index:
                    _close_open_fragment()
                    open_fragment_index = fragment_index
                    result += f"<div class=\"fragment\" data-fragment-index=\"{fragment_index}\">\n\n"

                result += content + "\n\n"
            
            if has_columns:
                in_fragment_mode = False
                current_fragment_step: Optional[int] = None
                next_auto_fragment_step = 0

                def _render_columns_block(columns: List[List[Dict[str, Any]]], alignment: str, use_table: bool = False) -> None:
                    nonlocal in_fragment_mode, current_fragment_step, next_auto_fragment_step
                    if not columns:
                        return

                    # If use_table is True, render as HTML table for row alignment
                    if use_table:
                        table_html = self._render_table_columns(columns, alignment)
                        columns_fragment_index: Optional[int] = current_fragment_step if in_fragment_mode else None
                        _emit_cell_content(table_html, columns_fragment_index)
                        return

                    align_class = "columns-top" if alignment == 'top' else "columns-center"

                    def _column_has_fragment_marker(col_cells: List[Dict[str, Any]]) -> bool:
                        for c in col_cells:
                            tags = self._get_cell_tags(c)
                            if 'fragment' in tags or self._is_slideshow_fragment(c) or self._get_fragment_index(c) is not None:
                                return True
                        return False

                    first_col_has_marker = _column_has_fragment_marker(columns[0]) if columns else False
                    other_cols_have_marker = any(_column_has_fragment_marker(col_cells) for col_cells in columns[1:])
                    any_col_has_marker = first_col_has_marker or other_cols_have_marker

                    # Rule:
                    # 1) If ONLY the first column has a fragment marker, the whole columns block
                    #    (and following content via fragment mode) must appear together.
                    # 2) If a fragment marker appears in any other column OR in all columns,
                    #    columns should appear at different times.
                    group_whole_columns = first_col_has_marker and not other_cols_have_marker

                    if not any_col_has_marker:
                        columns_parts: List[str] = []
                        columns_parts.append(f"<div class=\"columns-container {align_class}\">\n\n")
                        for col_cells in columns:
                            columns_parts.append("<div class=\"col\">\n\n")
                            for cell in col_cells:
                                content = self._format_cell_content(cell)
                                if content:
                                    columns_parts.append(content + "\n\n")
                            columns_parts.append("</div>\n\n")
                        columns_parts.append("</div>")
                        columns_html = ''.join(columns_parts).rstrip()

                        columns_fragment_index: Optional[int] = current_fragment_step if in_fragment_mode else None
                        _emit_cell_content(columns_html, columns_fragment_index)
                    elif group_whole_columns:
                        flattened_column_cells: List[Dict[str, Any]] = []
                        for col_cells in columns:
                            flattened_column_cells.extend(col_cells)

                        columns_fragment_groups, in_fragment_mode, current_fragment_step, next_auto_fragment_step = self._group_cells_into_fragments_with_state(
                            flattened_column_cells,
                            in_fragment_mode=in_fragment_mode,
                            current_fragment_step=current_fragment_step,
                            next_auto_fragment_step=next_auto_fragment_step,
                        )

                        columns_fragment_index: Optional[int] = None
                        for info in columns_fragment_groups:
                            if info.get('index') is not None:
                                columns_fragment_index = info.get('index')
                                break

                        columns_parts: List[str] = []
                        columns_parts.append(f"<div class=\"columns-container {align_class}\">\n\n")
                        for col_cells in columns:
                            columns_parts.append("<div class=\"col\">\n\n")
                            for cell in col_cells:
                                content = self._format_cell_content(cell)
                                if content:
                                    columns_parts.append(content + "\n\n")
                            columns_parts.append("</div>\n\n")
                        columns_parts.append("</div>")
                        columns_html = ''.join(columns_parts).rstrip()

                        _emit_cell_content(columns_html, columns_fragment_index)
                    else:
                        columns_parts: List[str] = []
                        columns_parts.append(f"<div class=\"columns-container {align_class}\">\n\n")

                        for col_idx, col_cells in enumerate(columns):
                            has_marker = _column_has_fragment_marker(col_cells)

                            columns_parts.append("<div class=\"col\">\n\n")

                            # Group cells within this column by their fragment-index
                            cell_groups: List[Tuple[Optional[int], List[Dict[str, Any]]]] = []
                            current_group_index: Optional[int] = None
                            current_group_cells: List[Dict[str, Any]] = []

                            for cell in col_cells:
                                cell_fragment_index = self._get_fragment_index(cell)
                                cell_tags = self._get_cell_tags(cell)
                                is_fragment_marker = 'fragment' in cell_tags or self._is_slideshow_fragment(cell)
                                
                                # Determine the fragment index for this cell
                                if cell_fragment_index is not None:
                                    # Cell has explicit fragment-index-N
                                    if current_group_index != cell_fragment_index:
                                        # Start a new group
                                        if current_group_cells:
                                            cell_groups.append((current_group_index, current_group_cells))
                                        current_group_index = cell_fragment_index
                                        current_group_cells = [cell]
                                        next_auto_fragment_step = max(next_auto_fragment_step, cell_fragment_index + 1)
                                    else:
                                        # Continue current group
                                        current_group_cells.append(cell)
                                elif is_fragment_marker:
                                    # Cell has 'fragment' tag but no explicit index
                                    new_index = next_auto_fragment_step
                                    if current_group_index != new_index:
                                        if current_group_cells:
                                            cell_groups.append((current_group_index, current_group_cells))
                                        current_group_index = new_index
                                        current_group_cells = [cell]
                                        next_auto_fragment_step += 1
                                    else:
                                        current_group_cells.append(cell)
                                else:
                                    # Cell has no fragment marker
                                    if current_group_index is not None:
                                        # End current fragment group
                                        if current_group_cells:
                                            cell_groups.append((current_group_index, current_group_cells))
                                        current_group_index = None
                                        current_group_cells = [cell]
                                    else:
                                        # Continue non-fragment group
                                        current_group_cells.append(cell)

                            # Add the last group
                            if current_group_cells:
                                cell_groups.append((current_group_index, current_group_cells))

                            # Render each group
                            for group_fragment_index, group_cells in cell_groups:
                                if group_fragment_index is not None:
                                    # Wrap in fragment div
                                    columns_parts.append(f"<div class=\"fragment\" data-fragment-index=\"{group_fragment_index}\">\n\n")
                                
                                for cell in group_cells:
                                    content = self._format_cell_content(cell)
                                    if content:
                                        columns_parts.append(content + "\n\n")
                                
                                if group_fragment_index is not None:
                                    columns_parts.append("</div>\n\n")

                            columns_parts.append("</div>\n\n")

                        columns_parts.append("</div>")
                        columns_html = ''.join(columns_parts).rstrip()

                        _emit_cell_content(columns_html, None)

                segments = self._split_cells_into_column_blocks(cells_to_process)

                for seg in segments:
                    if seg.get('type') == 'cells':
                        seg_cells = seg.get('cells', [])
                        if not seg_cells:
                            continue

                        fragment_groups, in_fragment_mode, current_fragment_step, next_auto_fragment_step = self._group_cells_into_fragments_with_state(
                            seg_cells,
                            in_fragment_mode=in_fragment_mode,
                            current_fragment_step=current_fragment_step,
                            next_auto_fragment_step=next_auto_fragment_step,
                        )

                        for fragment_info in fragment_groups:
                            fragment_cells = fragment_info['cells']
                            fragment_index = fragment_info['index']
                            for cell in fragment_cells:
                                content = self._format_cell_content(cell)
                                if content:
                                    _emit_cell_content(content, fragment_index)
                    elif seg.get('type') == 'columns':
                        _render_columns_block(seg.get('columns', []), seg.get('alignment', 'center'), seg.get('use_table', False))
            else:
                # No columns, group cells into fragments
                fragment_groups = self._group_cells_into_fragments(cells_to_process)
                
                for fragment_info in fragment_groups:
                    fragment_cells = fragment_info['cells']
                    fragment_index = fragment_info['index']
                    for cell in fragment_cells:
                        content = self._format_cell_content(cell)
                        if content:
                            _emit_cell_content(content, fragment_index)

            _close_open_fragment()
            
            result += "\n\n</div>"
        
        # Process footnotes if any
        if footnote_cells:
            # Extract markers from all regular cells
            markers = self._extract_footnote_markers(cells_to_process)
            
            result += "\n\n<div class=\"footnotes\">\n\n"
            
            for i, footnote_cell in enumerate(footnote_cells):
                # Determine marker for this footnote
                if i < len(markers):
                    marker = markers[i]
                else:
                    marker = self._generate_footnote_marker(i)
                
                # Format footnote content
                footnote_content = self._format_cell_content(footnote_cell)
                if footnote_content:
                    result += f"<sup>{marker}</sup> {footnote_content}\n\n"
            
            result += "</div>"

        # Ensure inline backticks inside alert divs are converted to <code>
        result = self._replace_inline_code_in_alerts(result)

        return result
    
    def convert(self) -> str:
        """
        Convert the notebook to markdown format.
        
        Returns:
            Markdown string
        """
        # Add front matter
        title = self.notebook_path.stem.replace('-', ' ')
        front_matter = f"---\ntitle: \"{title}\"\n---"
        
        # Group cells into slides
        slides = self._group_cells_into_slides()
        
        # Process each slide
        slide_parts = []
        for slide_cells in slides:
            slide_content = self._process_slide(slide_cells)
            if slide_content:
                slide_parts.append(slide_content)
        
        # Join front matter and slides - no separator after front matter
        if slide_parts:
            return front_matter + '\n\n' + '\n\n---\n\n'.join(slide_parts)
        else:
            return front_matter
    
    def save(self, output_path: str = None) -> Path:
        """
        Convert and save the markdown to a file.
        
        Args:
            output_path: Optional output path. If not provided, uses notebook name with .md extension
            
        Returns:
            Path to the saved file
        """
        if output_path is None:
            output_path = self.notebook_path.with_suffix('.md')
        else:
            output_path = Path(output_path)
        
        markdown = self.convert()
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(markdown)
        
        return output_path


def main():
    """Main entry point for the command-line tool."""
    parser = argparse.ArgumentParser(
        description='Convert Jupyter notebooks to mkslides-compatible markdown'
    )
    parser.add_argument(
        'notebook',
        help='Path to the Jupyter notebook file (.ipynb)'
    )
    parser.add_argument(
        '-o', '--output',
        help='Output markdown file path (default: same name as notebook with .md extension)',
        default=None
    )
    
    args = parser.parse_args()
    
    try:
        converter = NotebookConverter(args.notebook)
        output_path = converter.save(args.output)
        print(f"Successfully converted notebook to: {output_path}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
