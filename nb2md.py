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
    
    def _group_cells_into_fragments(self, cells: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Group cells into fragments based on 'fragment' tag or slideshow metadata.
        
        Args:
            cells: List of cells to group
            
        Returns:
            List of fragment dictionaries with 'cells', 'index', and 'has_index' keys
        """
        fragments = []
        current_fragment = []
        current_fragment_index = None
        in_fragment = False
        
        for cell in cells:
            tags = self._get_cell_tags(cell)
            is_no_fragment = 'no-fragment' in tags
            is_fragment_marker = 'fragment' in tags or self._is_slideshow_fragment(cell)
            fragment_index = self._get_fragment_index(cell)
            has_fragment_index = fragment_index is not None
            
            if is_no_fragment:
                # Exit fragment mode
                if current_fragment:
                    fragments.append({
                        'cells': current_fragment,
                        'index': current_fragment_index,
                        'has_index': current_fragment_index is not None
                    })
                    current_fragment = []
                    current_fragment_index = None
                in_fragment = False
                # Add the no-fragment cell itself if it has content
                cell_content = self._get_cell_content(cell).strip()
                if cell_content:
                    fragments.append({
                        'cells': [cell],
                        'index': None,
                        'has_index': False
                    })
            elif is_fragment_marker or has_fragment_index:
                # Start a new fragment
                if current_fragment:
                    # Save the previous fragment
                    fragments.append({
                        'cells': current_fragment,
                        'index': current_fragment_index,
                        'has_index': current_fragment_index is not None
                    })
                # Start new fragment and include this cell if it has content
                cell_content = self._get_cell_content(cell).strip()
                if cell_content:
                    current_fragment = [cell]
                else:
                    current_fragment = []
                current_fragment_index = fragment_index
                in_fragment = True
            else:
                if in_fragment:
                    # Add to current fragment
                    current_fragment.append(cell)
                else:
                    # Not in a fragment, treat as individual fragment without index
                    fragments.append({
                        'cells': [cell],
                        'index': None,
                        'has_index': False
                    })
        
        # Add the last fragment
        if current_fragment:
            fragments.append({
                'cells': current_fragment,
                'index': current_fragment_index,
                'has_index': current_fragment_index is not None
            })
        
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
            return f"{start}{body}{end}"

        return alert_div_pattern.sub(_sub_alert, html)
    
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
            'recall': ('alert-recall', 'RECALL')
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
        
        if cell_type == 'markdown':
            content = cell_content.strip()

            # Title/subtitle/date style content: render to template-specific ids
            if title_id:
                # Strip any h1–h6 markdown or HTML markup from the content
                content_no_headings = self._strip_heading_markup(content).strip()
                return f'<div id="{title_id}">{content_no_headings}</div>'

            # Wrap in alert box if needed
            if alert_type:
                # For alert boxes we must ensure inline backticks become <code>
                # because markdown is not processed inside raw HTML blocks.
                inline_code_pattern = re.compile(r"`([^`]+)`")
                content = inline_code_pattern.sub(r"<code>\1</code>", content)
                content = f'<div class="alert {alert_class}">{content}</div>'
            elif should_center:
                content = f'<div class="cell-center">\n\n{content}\n\n</div>'
            
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
            elif should_center:
                code_block = f'<div class="cell-center">\n\n{code_block}\n\n</div>'
            
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
        
        # Check if any cell has 'col', 'column', 'top-col', 'top-column', or 'no-column' tag
        has_columns = any('col' in self._get_cell_tags(cell) or 'column' in self._get_cell_tags(cell) or 'top-col' in self._get_cell_tags(cell) or 'top-column' in self._get_cell_tags(cell) or 'no-column' in self._get_cell_tags(cell) for cell in cells_to_process)
        
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
            
            if has_columns:
                # Group cells into pre-column cells, columns, and post-column cells
                pre_column_cells, columns, post_column_cells, alignment = self._group_cells_into_columns(cells_to_process)
                
                # Process pre-column cells first (not wrapped in col div)
                if pre_column_cells:
                    pre_column_parts = []
                    for cell in pre_column_cells:
                        content = self._format_cell_content(cell)
                        if content:
                            pre_column_parts.append(content)
                    
                    if pre_column_parts:
                        result += "\n\n".join(pre_column_parts) + "\n\n"
                
                # Wrap columns in a container div to prevent flex layout issues
                if columns:
                    align_class = "columns-top" if alignment == 'top' else "columns-center"
                    result += f"<div class=\"columns-container {align_class}\">\n\n"
                    
                    # Process columns
                    for column_cells in columns:
                        result += "<div class=\"col\">\n\n"
                        
                        # Group column cells into fragments
                        fragment_groups = self._group_cells_into_fragments(column_cells)
                        
                        for fragment_info in fragment_groups:
                            fragment_cells = fragment_info['cells']
                            fragment_index = fragment_info['index']
                            has_index = fragment_info['has_index']
                            
                            # Check if this is a multi-cell fragment or has explicit fragment marking
                            is_multi_cell_fragment = len(fragment_cells) > 1 or (
                                len(fragment_cells) == 1 and 
                                ('fragment' in self._get_cell_tags(fragment_cells[0]) or 
                                 self._is_slideshow_fragment(fragment_cells[0]) or
                                 has_index)
                            )
                            
                            # Process cells in this fragment
                            fragment_parts = []
                            for cell in fragment_cells:
                                content = self._format_cell_content(cell)
                                if content:
                                    fragment_parts.append(content)
                            
                            if fragment_parts:
                                fragment_content = "\n\n".join(fragment_parts)
                                # Wrap in fragment div if this is a multi-cell fragment
                                if is_multi_cell_fragment:
                                    if has_index:
                                        result += f"<div class=\"fragment\" data-fragment-index=\"{fragment_index}\">\n\n{fragment_content}\n\n</div>\n\n"
                                    else:
                                        result += f"<div class=\"fragment\">\n\n{fragment_content}\n\n</div>\n\n"
                                else:
                                    result += fragment_content + "\n\n"
                        
                        result += "</div>\n\n"
                    
                    result += "</div>\n\n"
                
                # Process post-column cells (after no-column tag)
                if post_column_cells:
                    post_column_parts = []
                    for cell in post_column_cells:
                        content = self._format_cell_content(cell)
                        if content:
                            post_column_parts.append(content)
                    
                    if post_column_parts:
                        result += "\n\n".join(post_column_parts)
            else:
                # No columns, group cells into fragments
                fragment_groups = self._group_cells_into_fragments(cells_to_process)
                
                for fragment_info in fragment_groups:
                    fragment_cells = fragment_info['cells']
                    fragment_index = fragment_info['index']
                    has_index = fragment_info['has_index']
                    
                    # Check if this is a multi-cell fragment or has explicit fragment marking
                    is_multi_cell_fragment = len(fragment_cells) > 1 or (
                        len(fragment_cells) == 1 and 
                        ('fragment' in self._get_cell_tags(fragment_cells[0]) or 
                         self._is_slideshow_fragment(fragment_cells[0]) or
                         has_index)
                    )
                    
                    # Process cells in this fragment
                    fragment_parts = []
                    for cell in fragment_cells:
                        content = self._format_cell_content(cell)
                        if content:
                            fragment_parts.append(content)
                    
                    if fragment_parts:
                        fragment_content = "\n\n".join(fragment_parts)
                        # Wrap in fragment div if this is a multi-cell fragment
                        if is_multi_cell_fragment:
                            if has_index:
                                result += f"<div class=\"fragment\" data-fragment-index=\"{fragment_index}\">\n\n{fragment_content}\n\n</div>\n\n"
                            else:
                                result += f"<div class=\"fragment\">\n\n{fragment_content}\n\n</div>\n\n"
                        else:
                            result += fragment_content + "\n\n"
            
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
