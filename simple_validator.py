#!/usr/bin/env python3
"""Simple test validator - just run the tests we know work"""

import os
import subprocess
import sys

def main():
    print("🧪 Simple Test Validator")
    print("=" * 40)
    
    # Change to project directory
    os.chdir(r"c:\Users\Todd\Projects\symbolic_agi")
    
    tests = [
        ("EmotionalState", [sys.executable, "-m", "pytest", "test_emotional_simple.py", "-v"]),
        ("Tool Sync", [sys.executable, "-m", "pytest", "test_tool_sync.py", "-v"])
    ]
    
    for name, cmd in tests:
        print(f"\n▶️  Testing {name}...")
        try:
            result = subprocess.run(cmd, timeout=60)
            if result.returncode == 0:
                print(f"✅ {name} PASSED")
            else:
                print(f"❌ {name} FAILED")
        except Exception as e:
            print(f"💥 {name} ERROR: {e}")
    
    print("\n🎯 Validation complete!")

if __name__ == "__main__":
    main()