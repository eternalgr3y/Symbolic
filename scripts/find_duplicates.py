# scripts/find_duplicates.py
"""
This script detects duplicate Python modules within a specified directory.
It is intended to be run as part of a CI/CD pipeline to prevent code rot.
"""
import os
import sys
from collections import defaultdict
from typing import Dict, List


def find_duplicate_modules(directory: str) -> Dict[str, List[str]]:
    """
    Scans a directory for .py files and identifies any that have the same
    base name (module name), which would cause import conflicts.

    Args:
        directory: The root directory to scan.

    Returns:
        A dictionary where keys are duplicate module names and values are lists
        of the full paths to the conflicting files.
    """
    modules: Dict[str, List[str]] = defaultdict(list)
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".py"):
                module_name = os.path.splitext(file)[0]
                modules[module_name].append(os.path.join(root, file))

    duplicates = {name: paths for name, paths in modules.items() if len(paths) > 1}
    return duplicates


if __name__ == "__main__":
    search_dir = "symbolic_agi"
    if not os.path.isdir(search_dir):
        print(f"Error: Directory '{search_dir}' not found.", file=sys.stderr)
        sys.exit(1)

    duplicates = find_duplicate_modules(search_dir)

    if duplicates:
        print("ERROR: Duplicate Python modules found!", file=sys.stderr)
        for name, paths in duplicates.items():
            print(
                f"  - Module '{name}.py' found in multiple locations:", file=sys.stderr
            )
            for path in paths:
                print(f"    - {path}", file=sys.stderr)
        sys.exit(1)
    else:
        print("No duplicate modules found. Excellent!")
        sys.exit(0)