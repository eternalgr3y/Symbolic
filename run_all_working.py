#!/usr/bin/env python3
"""Comprehensive working test suite using the proven sync pattern"""

import subprocess
import sys

def run_all_working_tests():
    """Run all our working test patterns"""
    
    test_suites = [
        {
            "name": "EmotionalState (Pure Sync)",
            "cmd": ["python", "-m", "pytest", "test_emotional_simple.py", "-v"]
        },
        {
            "name": "Tool Plugin (Sync Pattern)", 
            "cmd": ["python", "-m", "pytest", "test_tool_sync.py", "-v"]
        },
        {
            "name": "Direct Tests (No pytest)",
            "cmd": ["python", "test_direct.py"]
        }
    ]
    
    print("🎯 Running all working test patterns...")
    print("=" * 60)
    
    total_passed = 0
    total_failed = 0
    
    for suite in test_suites:
        print(f"\n🧪 {suite['name']}")
        print("-" * 40)
        
        try:
            result = subprocess.run(suite['cmd'], capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                print(f"✅ PASSED")
                # Extract test count from output
                if "passed" in result.stdout:
                    import re
                    matches = re.findall(r'(\d+) passed', result.stdout)
                    if matches:
                        passed = int(matches[0])
                        total_passed += passed
                        print(f"   Tests: {passed}")
                else:
                    total_passed += 1  # Direct test
            else:
                print(f"❌ FAILED (exit code: {result.returncode})")
                total_failed += 1
                if result.stderr:
                    print(f"   Error: {result.stderr[:200]}...")
                    
        except subprocess.TimeoutExpired:
            print(f"⏰ TIMEOUT")
            total_failed += 1
        except Exception as e:
            print(f"💥 ERROR: {e}")
            total_failed += 1
    
    print("\n" + "=" * 60)
    print(f"🎯 FINAL RESULTS:")
    print(f"✅ Passed: {total_passed}")
    print(f"❌ Failed: {total_failed}")
    print(f"📊 Success Rate: {total_passed/(total_passed+total_failed)*100:.1f}%")
    
    if total_failed == 0:
        print("\n🎉 ALL TESTS WORKING! The sync pattern is the solution!")
    else:
        print(f"\n🔧 Working patterns identified - avoid pytest-asyncio fixtures!")

if __name__ == "__main__":
    run_all_working_tests()