#!/usr/bin/env python3
"""
🚀 Enhanced Interactive AGI Launcher
Advanced goal management, monitoring, and control
"""

import os
import sys
import asyncio
import logging
import threading
import subprocess
from queue import Queue
from typing import Dict, Any, List, Optional

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from symbolic_agi.agi_controller import SymbolicAGI
from symbolic_agi.goal_management import GoalManager, GoalPriority, GoalStatus
from symbolic_agi.input_processor import EnhancedInputProcessor
from symbolic_agi.execution_engine import ExecutionEngine

class EnhancedAGILauncher:
    """Main launcher class with enhanced capabilities"""
    
    def __init__(self):
        self.agi = None
        self.goal_manager = GoalManager(max_concurrent_goals=2)
        self.input_processor = EnhancedInputProcessor(self.goal_manager)
        self.execution_engine = None
        self.status_display_interval = 30  # seconds
        
    async def initialize(self):
        """Initialize all components"""
        print("🚀 Starting Enhanced Interactive Symbolic AGI...")
        print("=" * 60)
        
        # Check and install required dependencies
        await self._ensure_dependencies()
        
        # Initialize AGI
        self.agi = await SymbolicAGI.create()
        
        # Ensure tool plugin is loaded for web browsing
        await self.agi.ensure_tool_plugin_loaded()
        
        self.execution_engine = ExecutionEngine(self.agi, self.goal_manager)
        
        print("✅ AGI initialized successfully!")
        print("🧠 Enhanced goal management ready")
        print("🌐 Web browsing capabilities loaded")
        print("=" * 60)
        print("Commands available:")
        print("  /status  - Show current status")
        print("  /list    - List all goals")  
        print("  /help    - Show all commands")
        print("  !goal    - High priority goal")
        print("  !!goal   - Critical priority goal")
        print("=" * 60)
        
    async def _ensure_dependencies(self):
        """Ensure required dependencies are installed"""
        try:
            import aiohttp
            import bs4
            print("✅ Web browsing dependencies available")
        except ImportError:
            print("📦 Installing web browsing dependencies...")
            
            try:
                subprocess.check_call([
                    sys.executable, '-m', 'pip', 'install', 
                    'aiohttp', 'beautifulsoup4', 'lxml'
                ])
                print("✅ Dependencies installed successfully")
            except subprocess.CalledProcessError as e:
                print(f"❌ Failed to install dependencies: {e}")
        
    async def handle_command(self, command_data: Dict[str, Any]):
        """Handle parsed commands"""
        cmd_type = command_data.get('type')
        
        if cmd_type == 'status':
            await self.show_status()
        elif cmd_type == 'list_goals':
            await self.list_goals()
        elif cmd_type == 'help':
            self.show_help()
        elif cmd_type == 'show_history':
            self.show_history()
        else:
            print(f"❓ Unknown command: {cmd_type}")
    
    async def show_status(self):
        """Show current system status"""
        status = self.goal_manager.get_status_summary()
        metrics = self.execution_engine.metrics
        
        print("\n📊 System Status:")
        print(f"  🎯 Goals Queued: {status['queued']}")
        print(f"  ⚡ Goals Active: {status['active']}")
        print(f"  ✅ Goals Completed: {status['completed']}")
        print(f"  ❌ Goals Failed: {status['failed']}")
        print(f"  📈 Success Rate: {metrics.get('success_rate', 0):.1%}")
        print(f"  ⏱️  Avg Execution: {metrics.get('average_execution_time', 0):.1f}s")
        
        if self.goal_manager.active_goals:
            print("\n🔄 Active Goals:")
            for goal_id, goal in self.goal_manager.active_goals.items():
                print(f"  [{goal_id}] {goal.description[:50]}...")
    
    async def list_goals(self):
        """List all goals with their status"""
        print("\n📋 Goal History:")
        for goal in self.goal_manager.goal_history[-10:]:  # Last 10 goals
            status_emoji = {
                GoalStatus.COMPLETED: "✅",
                GoalStatus.FAILED: "❌", 
                GoalStatus.PROCESSING: "⚡",
                GoalStatus.QUEUED: "⏳"
            }.get(goal.status, "❓")
            
            print(f"  {status_emoji} [{goal.id}] {goal.description[:60]}...")
    
    def show_help(self):
        """Show help information"""
        print("\n🆘 Available Commands:")
        print("  /status   - Show system status and metrics")
        print("  /list     - List recent goals and their status")
        print("  /history  - Show goal execution history")
        print("  /help     - Show this help message")
        print("\n💡 Goal Priority:")
        print("  goal      - Normal priority")
        print("  !goal     - High priority") 
        print("  !!goal    - Critical priority")
        print("\n🌐 Example Goals:")
        print("  Search for latest AI news")
        print("  !Browse https://python.org urgently")
        print("  !!Critical: Monitor system health")
    
    def show_history(self):
        """Show execution history"""
        print("\n📚 Execution History:")
        for goal in self.goal_manager.goal_history[-5:]:
            duration = ""
            if goal.started_at and goal.completed_at:
                delta = goal.completed_at - goal.started_at
                duration = f" ({delta.total_seconds():.1f}s)"
            
            print(f"  [{goal.id}] {goal.description[:50]}... {goal.status.value}{duration}")
    
    async def main_loop(self):
        """Enhanced main execution loop"""
        # Start input thread
        input_thread = threading.Thread(
            target=self.input_processor.input_thread, 
            daemon=True
        )
        input_thread.start()
        
        # Start execution engine
        execution_task = asyncio.create_task(
            self.execution_engine.execution_loop()
        )
        
        # Start status display task
        status_task = asyncio.create_task(self.periodic_status_display())
        
        try:
            while not self.input_processor.shutdown_event.is_set():
                # Process input commands
                if not self.input_processor.input_queue.empty():
                    command_data = self.input_processor.input_queue.get()
                    
                    if command_data['type'] == 'goal':
                        # Add goal to queue
                        goal_id = self.goal_manager.add_goal(
                            description=command_data['description'],
                            priority=command_data['priority'],
                            context=command_data['context']
                        )
                        print(f"📝 Added goal [{goal_id}] with {command_data['priority'].name} priority")
                        
                    else:
                        # Handle command
                        await self.handle_command(command_data)
                
                await asyncio.sleep(0.1)
                
        except KeyboardInterrupt:
            print("\n⏹️ Shutdown requested by user")
        finally:
            # Cleanup
            self.goal_manager.shutdown_event.set()
            self.input_processor.shutdown_event.set()
            execution_task.cancel()
            status_task.cancel()
            
            try:
                await self.agi.shutdown()
                print("🛑 AGI shutdown complete")
            except:
                pass
    
    async def periodic_status_display(self):
        """Periodically display status updates"""
        while not self.goal_manager.shutdown_event.is_set():
            await asyncio.sleep(self.status_display_interval)
            
            if self.goal_manager.active_goals:
                await self.show_status()

async def main():
    """Main entry point"""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Check environment
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ ERROR: OPENAI_API_KEY environment variable not set!")
        print("Please set your OpenAI API key:")
        print("  Windows: $env:OPENAI_API_KEY='your-key-here'")
        print("  Linux/Mac: export OPENAI_API_KEY='your-key-here'")
        sys.exit(1)
    
    # Launch enhanced AGI
    launcher = EnhancedAGILauncher()
    await launcher.initialize()
    await launcher.main_loop()

if __name__ == "__main__":
    print("🧠 Enhanced Interactive Symbolic AGI")
    print("Press Ctrl+C to shutdown")
    print()
    
    asyncio.run(main())