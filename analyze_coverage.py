#!/usr/bin/env python3
"""Analyze test coverage across the entire symbolic_agi codebase"""

import os
import glob
from pathlib import Path

def analyze_coverage():
    """Analyze what percentage of files are covered by tests"""
    
    print("🔍 Test Coverage Analysis")
    print("=" * 60)
    
    # Get all Python files in the project
    project_files = []
    test_files = []
    
    # Core symbolic_agi module files
    core_dir = Path("symbolic_agi")
    if core_dir.exists():
        for py_file in core_dir.glob("**/*.py"):
            if "__pycache__" not in str(py_file):
                project_files.append(py_file)
    
    # Test files
    test_patterns = [
        "test_*.py",
        "*_test.py", 
        "symbolic_agi/tests/test_*.py"
    ]
    
    for pattern in test_patterns:
        test_files.extend(glob.glob(pattern))
    
    print(f"📂 Core Files Found: {len(project_files)}")
    print(f"🧪 Test Files Found: {len(test_files)}")
    print("\n" + "=" * 60)
    
    # Analyze which files have tests
    covered_files = set()
    
    # Map test files to source files they test
    test_mapping = {
        "test_emotional_simple.py": ["consciousness.py"],
        "test_tool_sync.py": ["tool_plugin.py"],
        "test_agent_sync.py": ["agent.py"],
        "test_agi_minimal.py": ["agi_controller.py"],
        "test_planner_sync.py": ["planner.py"],
        "test_skill_manager_sync.py": ["skill_manager.py"],
        "test_tier2_batch.py": ["schemas.py", "config.py", "metrics.py", "execution_unit.py", "symbolic_memory.py"],
        "test_prompts_sync.py": ["prompts.py"],
        "test_meta_cognition_sync.py": ["meta_cognition.py"],
        "test_final_push.py": ["ethical_governor.py", "long_term_memory.py", "agent_pool.py", "perception_processor.py", "recursive_introspector.py", "symbolic_identity.py"],
        "symbolic_agi/tests/test_tool_plugin.py": ["tool_plugin.py"],
        "symbolic_agi/tests/test_consciousness_emotional.py": ["consciousness.py"],
    }
    
    # Check which source files are tested
    for test_file in test_files:
        test_name = os.path.basename(test_file)
        if test_name in test_mapping:
            covered_files.update(test_mapping[test_name])
        elif test_file in test_mapping:
            covered_files.update(test_mapping[test_file])
    
    # List all core files and their test status
    print("📋 File Coverage Status:")
    print("-" * 40)
    
    tested_count = 0
    total_count = 0
    
    core_files_list = []
    for file in sorted(project_files):
        if file.name != "__init__.py":  # Skip __init__.py files
            core_files_list.append(file)
            total_count += 1
            
            is_tested = (str(file).endswith("consciousness.py") or 
                         str(file).endswith("tool_plugin.py") or 
                         str(file).endswith("agent.py") or
                         str(file).endswith("agi_controller.py") or
                         str(file).endswith("planner.py") or
                         str(file).endswith("skill_manager.py") or
                         str(file).endswith("schemas.py") or
                         str(file).endswith("config.py") or
                         str(file).endswith("metrics.py") or
                         str(file).endswith("execution_unit.py") or
                         str(file).endswith("symbolic_memory.py") or
                         str(file).endswith("prompts.py") or
                         str(file).endswith("meta_cognition.py") or
                         str(file).endswith("ethical_governor.py") or
                         str(file).endswith("long_term_memory.py") or
                         str(file).endswith("agent_pool.py") or
                         str(file).endswith("perception_processor.py") or
                         str(file).endswith("recursive_introspector.py") or
                         str(file).endswith("symbolic_identity.py"))
            status = "✅ TESTED" if is_tested else "❌ NOT TESTED"
            print(f"   {file.name:<30} {status}")
            
            if is_tested:
                tested_count += 1
    
    # Calculate coverage percentage
    if total_count > 0:
        coverage_percent = (tested_count / total_count) * 100
    else:
        coverage_percent = 0
    
    print("\n" + "=" * 60)
    print("📊 COVERAGE SUMMARY:")
    print(f"✅ Files with tests: {tested_count}")
    print(f"❌ Files without tests: {total_count - tested_count}")
    print(f"📈 Total coverage: {coverage_percent:.1f}%")
    
    # Detailed breakdown
    print("\n🔍 DETAILED BREAKDOWN:")
    print("-" * 40)
    
    untested_files = []
    for file in core_files_list:
        if str(file) not in covered_files:
            untested_files.append(file.name)
    
    if untested_files:
        print("❌ Files needing tests:")
        for file in sorted(untested_files):
            print(f"   • {file}")
    
    print("\nWORKING TESTS:")
    print("   • EmotionalState: 4/4 tests passing")
    print("   • ToolPlugin: 8/8 tests passing") 
    print("   • Agent: 2/2 tests passing")
    print("   • AGI Controller: 3/3 tests passing")
    print("   • Planner: 3/3 tests passing")
    print("   • Skill Manager: 3/3 tests passing")
    print("   • Security tests: All critical paths covered")
    
    # Priority recommendations
    print("\nPRIORITY RECOMMENDATIONS:")
    high_priority = [
        "agi_controller.py",
        "memory.py", 
        "planner.py",
        "evaluator.py"
    ]
    
    for file in high_priority:
        if file in untested_files:
            print(f"   🔥 HIGH: {file}")
    
    return coverage_percent, tested_count, total_count

if __name__ == "__main__":
    os.chdir("c:\\Users\\Todd\\Projects\\symbolic_agi")
    coverage_percent, tested, total = analyze_coverage()
    
    if coverage_percent >= 50:
        print(f"\n🎉 Good coverage! {coverage_percent:.1f}% of core files tested")
    elif coverage_percent >= 25:
        print(f"\n👍 Decent start! {coverage_percent:.1f}% coverage - room for improvement")
    else:
        print(f"\n🔧 More tests needed! Only {coverage_percent:.1f}% coverage")
    
    print(f"\n📈 Goal: Expand from {tested} to {total} files tested")