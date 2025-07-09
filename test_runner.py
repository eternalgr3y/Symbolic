#!/usr/bin/env python3
"""
Quick test runner for the enhanced DynamicAgentPool
"""

import os
import subprocess
import sys


def run_tests():
    """Run the agent pool tests."""
    print("🧪 Running DynamicAgentPool tests...")
    print("=" * 50)

    # Change to project directory
    os.chdir(r"C:\Users\Todd\Projects\symbolic_agi")

    try:
        # Run pytest on the agent pool tests
        result = subprocess.run([
            sys.executable, "-m", "pytest",
            "symbolic_agi/tests/test_agent_pool.py",
            "-v", "--tb=short"
        ], capture_output=True, text=True)

        print("STDOUT:")
        print(result.stdout)

        if result.stderr:
            print("\nSTDERR:")
            print(result.stderr)

        print(f"\nReturn code: {result.returncode}")

        if result.returncode == 0:
            print("\n✅ All tests passed!")
        else:
            print("\n❌ Some tests failed.")

    except Exception as e:
        print(f"❌ Error running tests: {e}")

def run_demo():
    """Run the demo script."""
    print("\n🚀 Running DynamicAgentPool demo...")
    print("=" * 50)

    try:
        result = subprocess.run([
            sys.executable, "demo_agent_pool.py"
        ], capture_output=True, text=True)

        print("DEMO OUTPUT:")
        print(result.stdout)

        if result.stderr:
            print("\nERRORS:")
            print(result.stderr)

    except Exception as e:
        print(f"❌ Error running demo: {e}")

if __name__ == "__main__":
    run_tests()
    run_demo()
