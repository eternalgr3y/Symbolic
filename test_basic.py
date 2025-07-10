#!/usr/bin/env python3
"""Minimal test runner for basic functionality"""

import subprocess
import sys
import os

def run_basic_tests():
    """Run only the basic tests that should work"""
    os.chdir("c:\\Users\\Todd\\Projects\\symbolic_agi")
    
    print("Running basic emotional state tests...")
    
    # Test just the EmotionalState class (no database)
    cmd = [
        sys.executable, "-m", "pytest", 
        "symbolic_agi/tests/test_consciousness_emotional.py::TestEmotionalState",
        "-v", "--tb=short", "--no-header"
    ]
    
    try:
        result = subprocess.run(cmd, timeout=60)
        if result.returncode == 0:
            print("✅ Basic EmotionalState tests PASSED")
        else:
            print("❌ Basic EmotionalState tests FAILED")
            
    except subprocess.TimeoutExpired:
        print("⏰ Tests timed out")
    except Exception as e:
        print(f"💥 Error running tests: {e}")

if __name__ == "__main__":
    run_basic_tests()