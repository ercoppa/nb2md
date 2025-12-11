#!/usr/bin/env python3
"""
File preprocessor for mkslides to convert Jupyter notebooks to markdown.
This script is called by mkslides for each file in the source directory.
"""

import sys
from pathlib import Path
from typing import Optional

# Add the parent directory to path to import nb2md
sys.path.insert(0, str(Path(__file__).parent.parent))

from nb2md.nb2md import NotebookConverter


def preprocess_file(file_path: Path) -> Optional[Path]:
    """
    Preprocess a file. If it's a Jupyter notebook, convert it to markdown.
    Only converts if the notebook is newer than the markdown file.
    
    Args:
        file_path: Path to the file to preprocess
        
    Returns:
        Path to the generated markdown file if conversion happened, None otherwise
    """
    # Only process .ipynb files
    if file_path.suffix != '.ipynb':
        return None
    
    # Convert notebook to markdown
    output_path = file_path.with_suffix('.md')
    
    # Check if markdown exists and is newer than notebook
    if output_path.exists():
        notebook_mtime = file_path.stat().st_mtime
        markdown_mtime = output_path.stat().st_mtime
        
        # If markdown is newer or same age, skip conversion
        if markdown_mtime >= notebook_mtime:
            return None
    
    try:
        converter = NotebookConverter(str(file_path))
        markdown = converter.convert()
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(markdown)
        
        print(f"Converted {file_path} to {output_path}")
        return output_path
    except Exception as e:
        print(f"Error converting {file_path}: {e}", file=sys.stderr)
        return None
