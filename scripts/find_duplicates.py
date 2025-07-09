#!/usr/bin/env python3
# scripts/find_duplicates.py

import hashlib
import os
import sys
from collections import defaultdict
from pathlib import Path


def find_duplicate_files(root_dir: Path) -> dict[str, list[str]]:
    """
    Finds files with duplicate content within a directory.

    Args:
        root_dir: The root directory to search.

    Returns:
        A dictionary mapping content hashes to lists of file paths.
    """
    hashes = defaultdict(list)
    for dirpath, _, filenames in os.walk(root_dir):
        # Ignore virtual environments and cache directories
        if ".venv" in dirpath or "__pycache__" in dirpath or ".git" in dirpath:
            continue

        for filename in filenames:
            if filename.endswith(".py"):
                file_path = Path(dirpath) / filename
                with open(file_path, "rb") as f:
                    file_hash = hashlib.sha256(f.read()).hexdigest()
                hashes[file_hash].append(str(file_path.relative_to(root_dir)))

    return {key: value for key, value in hashes.items() if len(value) > 1}


if __name__ == "__main__":
    project_root = Path(__file__).parent.parent.resolve()
    print(f"Scanning for duplicate Python files in: {project_root}")

    duplicates = find_duplicate_files(project_root)

    if duplicates:
        print("\nERROR: Found duplicate files!", file=sys.stderr)
        for file_hash, files in duplicates.items():
            print(
                f"  - Hash: {file_hash[:10]}... Files: {', '.join(files)}",
                file=sys.stderr,
            )
        sys.exit(1)
    else:
        print("\nSuccess: No duplicate Python files found.")
        sys.exit(0)
