#!/usr/bin/env python3
"""Install missing dependencies"""

import subprocess
import sys

def install_missing_deps():
    """Install the missing dependencies"""
    missing_deps = [
        'watchfiles',
        'aiosqlite', 
        'pytest-timeout'
    ]
    
    for dep in missing_deps:
        print(f"Installing {dep}...")
        try:
            result = subprocess.run([
                sys.executable, "-m", "pip", "install", dep
            ], check=True)
            print(f"✅ {dep} installed successfully")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install {dep}: {e}")
            return False
    
    print("\n🎉 All dependencies installed!")
    return True

if __name__ == "__main__":
    install_missing_deps()