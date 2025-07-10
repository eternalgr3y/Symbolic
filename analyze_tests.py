#!/usr/bin/env python3
"""Analyze the test folder structure and identify issues"""

import os
import glob
from pathlib import Path

def analyze_test_folder():
    """Analyze the symbolic_agi/tests folder"""
    
    test_dir = Path("symbolic_agi/tests")
    print(f"📁 Analyzing test directory: {test_dir}")
    print("="*60)
    
    if not test_dir.exists():
        print("❌ Test directory doesn't exist!")
        return
    
    # Get all Python test files
    test_files = list(test_dir.glob("test_*.py"))
    print(f"📄 Found {len(test_files)} test files:")
    
    for test_file in sorted(test_files):
        print(f"   • {test_file.name}")
    
    print("\n" + "="*60)
    
    # Analyze each test file
    for test_file in sorted(test_files):
        analyze_test_file(test_file)
    
    # Check for conftest.py
    conftest = test_dir / "conftest.py"
    if conftest.exists():
        print("\n📋 conftest.py found - analyzing...")
        analyze_conftest(conftest)
    else:
        print("\n⚠️  No conftest.py found")

def analyze_test_file(file_path):
    """Analyze individual test file"""
    print(f"\n📄 {file_path.name}")
    print("-" * 40)
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Count lines
        lines = content.split('\n')
        print(f"   Lines: {len(lines)}")
        
        # Check for async tests
        async_tests = content.count('@pytest.mark.asyncio')
        if async_tests > 0:
            print(f"   🔄 Async tests: {async_tests}")
        
        # Check for fixtures
        fixtures = content.count('@pytest.fixture') + content.count('@pytest_asyncio.fixture')
        if fixtures > 0:
            print(f"   🔧 Fixtures: {fixtures}")
        
        # Check for test classes
        test_classes = content.count('class Test')
        if test_classes > 0:
            print(f"   📦 Test classes: {test_classes}")
        
        # Check for test functions
        test_functions = content.count('def test_')
        if test_functions > 0:
            print(f"   🧪 Test functions: {test_functions}")
        
        # Check for potential issues
        issues = []
        
        # Check for database operations
        if 'Consciousness.create' in content or 'create(' in content:
            issues.append("Database operations detected")
        
        # Check for imports that might cause issues
        problematic_imports = ['tortoise', 'redis', 'awatch', 'aiosqlite']
        for imp in problematic_imports:
            if imp in content:
                issues.append(f"Potentially problematic import: {imp}")
        
        # Check for async generators
        if 'yield' in content and 'async def' in content:
            issues.append("Async generator fixtures detected")
        
        if issues:
            print(f"   ⚠️  Potential issues:")
            for issue in issues:
                print(f"      - {issue}")
        else:
            print(f"   ✅ No obvious issues detected")
            
    except Exception as e:
        print(f"   ❌ Error reading file: {e}")

def analyze_conftest(conftest_path):
    """Analyze conftest.py file"""
    try:
        with open(conftest_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print(f"   Lines: {len(content.split())}")
        
        # Check for fixtures
        fixtures = content.count('@pytest.fixture') + content.count('@pytest_asyncio.fixture')
        print(f"   🔧 Global fixtures: {fixtures}")
        
        # Check for async fixtures
        if '@pytest_asyncio.fixture' in content:
            print(f"   🔄 Async fixtures detected")
        
        # Check for imports
        if 'from symbolic_agi' in content:
            print(f"   📦 Imports symbolic_agi modules")
            
    except Exception as e:
        print(f"   ❌ Error reading conftest.py: {e}")

def check_pytest_config():
    """Check pytest configuration files"""
    print("\n" + "="*60)
    print("📋 Checking pytest configuration...")
    
    config_files = [
        "pytest.ini",
        "pyproject.toml", 
        "setup.cfg",
        "tox.ini"
    ]
    
    for config_file in config_files:
        if os.path.exists(config_file):
            print(f"   ✅ Found: {config_file}")
            
            # Quick check of pytest.ini
            if config_file == "pytest.ini":
                try:
                    with open(config_file, 'r') as f:
                        content = f.read()
                    if 'asyncio' in content:
                        print(f"      🔄 AsyncIO configuration detected")
                    if 'timeout' in content:
                        print(f"      ⏰ Timeout configuration detected")
                except:
                    pass
        else:
            print(f"   ❌ Missing: {config_file}")

if __name__ == "__main__":
    os.chdir("c:\\Users\\Todd\\Projects\\symbolic_agi")
    analyze_test_folder()
    check_pytest_config()
    
    print("\n" + "="*60)
    print("🎯 SUMMARY & RECOMMENDATIONS:")
    print("="*60)
    print("1. Run individual test files to isolate issues")
    print("2. Check for async fixture problems in consciousness tests")  
    print("3. Consider database initialization delays")
    print("4. Review pytest configuration for async handling")
    print("5. Test with smaller subsets to identify hanging tests")