#!/usr/bin/env python3
"""Fix tests with proper timeout and resource management"""

import subprocess
import sys
import os

def run_fixed_tests():
    """Run tests with proper configuration to prevent hangs and crashes"""
    
    print("🔧 Running tests with proper configuration...")
    
    # Test commands with proper resource management
    test_commands = [
        # Single worker, no parallel execution, with timeout
        [
            sys.executable, "-m", "pytest", 
            "symbolic_agi/tests/test_tool_plugin.py",
            "-v", 
            "--timeout=15",           # 15 second timeout per test
            "--disable-warnings",     # Reduce noise
            "--tb=short",            # Short traceback
            "-x",                    # Stop on first failure
        ],
        
        # Just the basic working tests
        [
            sys.executable, "-m", "pytest", 
            "test_emotional_simple.py",
            "-v", "--timeout=10"
        ],
        
        # Basic consciousness test (non-database)
        [
            sys.executable, "-m", "pytest", 
            "symbolic_agi/tests/test_consciousness_emotional.py::TestEmotionalState",
            "-v", "--timeout=10"
        ]
    ]
    
    for i, cmd in enumerate(test_commands, 1):
        print(f"\n🧪 Test Run {i}: {' '.join(cmd[-2:])}")
        print("-" * 50)
        
        try:
            result = subprocess.run(cmd, timeout=300)  # 5 minute overall timeout
            
            if result.returncode == 0:
                print(f"✅ Test run {i} PASSED")
            else:
                print(f"❌ Test run {i} FAILED (exit code: {result.returncode})")
                
        except subprocess.TimeoutExpired:
            print(f"⏰ Test run {i} TIMED OUT")
        except KeyboardInterrupt:
            print(f"🛑 Test run {i} INTERRUPTED")
            break
        except Exception as e:
            print(f"💥 Test run {i} ERROR: {e}")

if __name__ == "__main__":
    os.chdir("c:\\Users\\Todd\\Projects\\symbolic_agi")
    run_fixed_tests()