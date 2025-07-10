#!/usr/bin/env python
"""Simple coverage checker"""
import subprocess
import sys

def main():
    """Run tests with coverage"""
    cmd = [
        sys.executable, "-m", "pytest",
        "--cov=symbolic_agi",
        "--cov-report=html",
        "--cov-report=term-missing",
        "--cov-fail-under=20",  # Start with current coverage
        "symbolic_agi/tests"
    ]
    
    print("Running tests with coverage...")
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        print("\nCoverage report: htmlcov/index.html")
        if sys.platform == "win32":
            subprocess.run(["start", "htmlcov/index.html"], shell=True)
    
    return result.returncode

if __name__ == "__main__":
    sys.exit(main())