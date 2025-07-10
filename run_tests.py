#!/usr/bin/env python3
"""
Comprehensive test runner for Symbolic AGI
"""
import sys
import subprocess
import argparse
from pathlib import Path
import os

def check_dependencies():
    """Check if required test dependencies are installed"""
    required = ['pytest', 'pytest-cov', 'pytest-asyncio']
    missing = []
    
    for package in required:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing.append(package)
    
    if missing:
        print(f"Missing required packages: {', '.join(missing)}")
        print("Install with: pip install pytest pytest-cov pytest-asyncio pytest-xdist")
        return False
    return True

def run_tests(args):
    """Run tests with specified options"""
    if args.coverage and not check_dependencies():
        return 1
    
    cmd = ["python", "-m", "pytest"]
    
    if args.fast:
        # Skip slow tests for quick feedback
        cmd.extend(["-m", "not slow"])
    
    if args.unit:
        cmd.extend(["-m", "unit"])
    elif args.integration:
        cmd.extend(["-m", "integration"])
    elif args.performance:
        cmd.extend(["-m", "performance"])
    
    if args.coverage:
        cmd.extend([
            "--cov=symbolic_agi",
            "--cov-report=html",
            "--cov-report=term-missing"
        ])
    
    if args.verbose:
        cmd.append("-vv")
    else:
        cmd.append("-v")
    
    if args.parallel:
        cmd.extend(["-n", str(args.parallel)])
    
    if args.failed_first:
        cmd.append("--failed-first")
    
    if args.pattern:
        cmd.extend(["-k", args.pattern])
    
    # Add specific test files if provided
    if args.files:
        cmd.extend(args.files)
    else:
        cmd.append("symbolic_agi/tests")
    
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    
    if args.coverage and result.returncode == 0:
        print("\nCoverage report generated in htmlcov/index.html")
        print("Open with: start htmlcov/index.html")
    
    return result.returncode

def simple_test_runner():
    """Run a simple set of tests to check status"""
    os.chdir("c:\\Users\\Todd\\Projects\\symbolic_agi")
    
    # Test categories to run
    test_categories = [
        ("Basic EmotionalState tests", "symbolic_agi/tests/test_consciousness_emotional.py::TestEmotionalState"),
        ("Consciousness emotional tests", "symbolic_agi/tests/test_consciousness_emotional.py::TestConsciousnessEmotional"),
        ("Basic tool plugin tests", "symbolic_agi/tests/test_tool_plugin.py::TestToolPlugin::test_tool_initialization"),
        ("Tool plugin file ops", "symbolic_agi/tests/test_tool_plugin.py::TestToolPlugin::test_write_file_basic"),
    ]
    
    for name, test_path in test_categories:
        print(f"\n{'='*60}")
        print(f"Running: {name}")
        print(f"{'='*60}")
        
        try:
            result = subprocess.run([
                sys.executable, "-m", "pytest", 
                test_path, "-v", "--tb=short"
            ], capture_output=True, text=True, timeout=30)
            
            print(f"Exit code: {result.returncode}")
            if result.stdout:
                print("STDOUT:", result.stdout)
            if result.stderr:
                print("STDERR:", result.stderr)
                
        except subprocess.TimeoutExpired:
            print("Test timed out after 30 seconds")
        except Exception as e:
            print(f"Error running test: {e}")

def main():
    parser = argparse.ArgumentParser(description="Run Symbolic AGI tests")
    
    parser.add_argument("--fast", action="store_true",
                       help="Skip slow tests")
    parser.add_argument("--unit", action="store_true",
                       help="Run only unit tests")
    parser.add_argument("--integration", action="store_true",
                       help="Run only integration tests")
    parser.add_argument("--performance", action="store_true",
                       help="Run only performance tests")
    parser.add_argument("--coverage", action="store_true",
                       help="Generate coverage report")
    parser.add_argument("-v", "--verbose", action="store_true",
                       help="Verbose output")
    parser.add_argument("-n", "--parallel", type=int,
                       help="Number of parallel workers")
    parser.add_argument("--failed-first", action="store_true",
                       help="Run failed tests first")
    parser.add_argument("-k", "--pattern", type=str,
                       help="Run tests matching pattern")
    parser.add_argument("files", nargs="*",
                       help="Specific test files to run")
    
    args = parser.parse_args()
    
    # For now, always run the simple test runner
    simple_test_runner()
    
    sys.exit(run_tests(args))

if __name__ == "__main__":
    main()