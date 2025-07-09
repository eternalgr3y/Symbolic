# Chocolatey + Redis Installation Guide
"""
🍫 CHOCOLATEY + REDIS SETUP
===========================

STEP 1: Install Chocolatey
--------------------------
1. Open PowerShell as Administrator (Right-click PowerShell -> Run as Administrator)
2. Run this command:

Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

3. Close and reopen PowerShell as Administrator

STEP 2: Install Redis with Chocolatey
-------------------------------------
choco install redis-64

STEP 3: Start Redis
-------------------
redis-server

STEP 4: Test Redis (in another terminal)
----------------------------------------
redis-cli ping
# Should return: PONG

STEP 5: Run Your AGI
-------------------
python launch_agi.py

🎯 FULL COMMAND SEQUENCE:
========================
# In PowerShell as Administrator:
Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# Close and reopen PowerShell as Admin, then:
choco install redis-64

# Start Redis:
redis-server

# In another terminal (regular, not admin):
cd C:\Users\Todd\Projects\symbolic_agi
python bootstrap_agi.py
python launch_agi.py
"""

print("Follow the steps above to get Chocolatey and Redis running!")
print("Remember: PowerShell must be run as Administrator for Chocolatey install!")