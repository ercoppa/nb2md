#!/usr/bin/env python3
"""
Example usage of the nb2md converter
"""

from nb2md import NotebookConverter
from pathlib import Path

def convert_notebook(notebook_path, output_path=None):
    """
    Convert a single notebook to markdown.
    
    Args:
        notebook_path: Path to the notebook file
        output_path: Optional output path (defaults to same name with .md)
    """
    print(f"Converting: {notebook_path}")
    
    converter = NotebookConverter(notebook_path)
    result_path = converter.save(output_path)
    
    print(f"✓ Created: {result_path}")
    return result_path


def convert_all_notebooks_in_directory(directory):
    """
    Convert all notebooks in a directory.
    
    Args:
        directory: Path to directory containing notebooks
    """
    directory = Path(directory)
    notebooks = list(directory.glob("*.ipynb"))
    
    if not notebooks:
        print(f"No notebooks found in {directory}")
        return
    
    print(f"Found {len(notebooks)} notebook(s)")
    
    for notebook in notebooks:
        try:
            convert_notebook(notebook)
        except Exception as e:
            print(f"✗ Error converting {notebook}: {e}")


if __name__ == '__main__':
    # Example 1: Convert a single notebook
    convert_notebook('../src/P05-Python-Iteration.ipynb')
    
    # Example 2: Convert with custom output path
    # convert_notebook(
    #     '../src/P05-Python-Iteration.ipynb',
    #     '../output/my-slides.md'
    # )
    
    # Example 3: Convert all notebooks in a directory
    # convert_all_notebooks_in_directory('../src')
