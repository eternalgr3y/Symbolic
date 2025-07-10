#!/usr/bin/env python3
"""
🧹 Resource Cleanup Utility for Symbolic AGI
Cleans up hanging processes and unclosed resources
"""

import psutil
import os
import sys
import time
import subprocess

def cleanup_hanging_processes():
    """Clean up any hanging AGI-related processes"""
    print("🔍 Scanning for hanging AGI processes...")
    
    current_pid = os.getpid()
    killed_processes = []
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['pid'] == current_pid:
                continue
                
            cmdline = ' '.join(proc.info['cmdline'] or [])
            
            # Look for AGI-related processes
            if any(keyword in cmdline.lower() for keyword in [
                'symbolic_agi', 'launch_agi.py', 'redis-server', 
                'playwright', 'chromium'
            ]):
                print(f"🎯 Found hanging process: PID {proc.info['pid']} - {proc.info['name']}")
                print(f"   Command: {cmdline[:100]}...")
                
                try:
                    proc.terminate()
                    proc.wait(timeout=5)
                    killed_processes.append(proc.info['pid'])
                    print(f"   ✅ Terminated gracefully")
                except psutil.TimeoutExpired:
                    proc.kill()
                    killed_processes.append(proc.info['pid'])
                    print(f"   ⚡ Force killed")
                except psutil.AccessDenied:
                    print(f"   ❌ Access denied (may need admin privileges)")
                
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    
    if killed_processes:
        print(f"🎯 Cleaned up {len(killed_processes)} processes: {killed_processes}")
    else:
        print("✅ No hanging processes found")
    
    return killed_processes

def cleanup_redis_connections():
    """Clean up Redis connections"""
    print("🔍 Checking Redis connections...")
    
    try:
        # Check if Redis is running
        redis_processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if 'redis' in proc.info['name'].lower():
                    redis_processes.append(proc)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        if redis_processes:
            print(f"📊 Found {len(redis_processes)} Redis process(es)")
            for proc in redis_processes:
                print(f"   • PID {proc.info['pid']}: {proc.info['name']}")
        else:
            print("ℹ️  No Redis processes found")
        
    except Exception as e:
        print(f"❌ Error checking Redis: {e}")

def cleanup_playwright_browsers():
    """Clean up Playwright browser processes"""
    print("🔍 Checking for leftover browser processes...")
    
    browser_names = ['chromium', 'chrome', 'firefox', 'webkit']
    browser_processes = []
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = ' '.join(proc.info['cmdline'] or [])
            
            if any(browser in proc.info['name'].lower() for browser in browser_names):
                if 'headless' in cmdline.lower() or 'playwright' in cmdline.lower():
                    browser_processes.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    
    if browser_processes:
        print(f"🌐 Found {len(browser_processes)} browser process(es) to clean up")
        for proc in browser_processes:
            try:
                print(f"   🎯 Terminating browser PID {proc.info['pid']}")
                proc.terminate()
                proc.wait(timeout=3)
            except (psutil.TimeoutExpired, psutil.AccessDenied):
                try:
                    proc.kill()
                except:
                    pass
        print("✅ Browser cleanup completed")
    else:
        print("✅ No hanging browser processes found")

def check_system_resources():
    """Check system resource usage"""
    print("📊 System Resource Check:")
    
    # CPU usage
    cpu_percent = psutil.cpu_percent(interval=1)
    print(f"   🔥 CPU Usage: {cpu_percent:.1f}%")
    
    # Memory usage
    memory = psutil.virtual_memory()
    print(f"   🧠 Memory Usage: {memory.percent:.1f}% ({memory.used // (1024**3):.1f}GB / {memory.total // (1024**3):.1f}GB)")
    
    # Disk usage
    disk = psutil.disk_usage('C:' if os.name == 'nt' else '/')
    print(f"   💾 Disk Usage: {disk.percent:.1f}% ({disk.used // (1024**3):.1f}GB / {disk.total // (1024**3):.1f}GB)")
    
    # Network connections
    connections = len(psutil.net_connections())
    print(f"   🌐 Network Connections: {connections}")
    
    # Process count
    process_count = len(psutil.pids())
    print(f"   ⚙️  Running Processes: {process_count}")

def main():
    """Main cleanup routine"""
    print("🧹 SYMBOLIC AGI RESOURCE CLEANUP")
    print("=" * 40)
    
    try:
        # System resource check
        check_system_resources()
        print()
        
        # Clean up processes
        killed = cleanup_hanging_processes()
        print()
        
        # Check Redis
        cleanup_redis_connections()
        print()
        
        # Clean up browsers
        cleanup_playwright_browsers()
        print()
        
        print("🎯 CLEANUP SUMMARY:")
        print(f"   • Processes cleaned: {len(killed) if killed else 0}")
        print("   • Redis connections checked")
        print("   • Browser processes cleaned")
        print("   • System resources monitored")
        
        print("\n✅ Cleanup completed successfully!")
        print("💡 Safe to restart Symbolic AGI now")
        
    except Exception as e:
        print(f"❌ Cleanup failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n🛑 Cleanup interrupted by user")
        sys.exit(1)