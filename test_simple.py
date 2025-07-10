#!/usr/bin/env python3
"""Super simple test runner that won't hang"""

import subprocess
import sys
import os

def run_simple_test():
    """Run just one basic test"""
    os.chdir("c:\\Users\\Todd\\Projects\\symbolic_agi")
    
    print("Testing basic EmotionalState initialization...")
    
    cmd = [
        sys.executable, "-m", "pytest", 
        "symbolic_agi/tests/test_consciousness_emotional.py::TestEmotionalState::test_initialization",
        "-v", "--tb=short", "--timeout=10"
    ]
    
    try:
        result = subprocess.run(cmd, timeout=20, capture_output=True, text=True)
        print(f"Exit code: {result.returncode}")
        print("STDOUT:")
        print(result.stdout)
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
            
        if result.returncode == 0:
            print("✅ BASIC TEST PASSED!")
        else:
            print("❌ Test failed")
            
    except subprocess.TimeoutExpired:
        print("⏰ Test timed out")
    except Exception as e:
        print(f"💥 Error: {e}")

if __name__ == "__main__":
    run_simple_test()