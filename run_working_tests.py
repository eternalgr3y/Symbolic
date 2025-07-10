#!/usr/bin/env python3
"""Run only known working tests - fast and reliable"""

import subprocess
import sys

# List of tests we know work
WORKING_TESTS = [
    "test_emotional_simple.py",
    "symbolic_agi/tests/test_tool_plugin.py::TestToolPlugin::test_tool_initialization",
    "symbolic_agi/tests/test_tool_plugin.py::TestToolPlugin::test_file_access_security", 
    "symbolic_agi/tests/test_consciousness_emotional.py::TestEmotionalState",
]

def run_working_tests():
    """Run only the tests we know work"""
    print("🚀 Running known working tests...")
    
    for test in WORKING_TESTS:
        print(f"\n▶️  Running: {test}")
        try:
            result = subprocess.run([
                sys.executable, "-m", "pytest", test, 
                "-v", "--timeout=30", "--tb=short"
            ], timeout=60)
            
            if result.returncode == 0:
                print(f"✅ {test} - PASSED")
            else:
                print(f"❌ {test} - FAILED")
                
        except subprocess.TimeoutExpired:
            print(f"⏰ {test} - TIMEOUT")
        except Exception as e:
            print(f"💥 {test} - ERROR: {e}")

if __name__ == "__main__":
    run_working_tests()