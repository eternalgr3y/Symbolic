#!/usr/bin/env python3
"""
🚀 Interactive AGI Launcher
Run this script to start your Symbolic AGI with goal input
"""

import os
import sys
import asyncio
import logging
import threading
from queue import Queue

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from symbolic_agi.agi_controller import SymbolicAGI
from symbolic_agi.schemas import ActionStep

# Global queue for user input
input_queue = Queue()
shutdown_event = threading.Event()

def input_thread():
    """Background thread to handle user input."""
    while not shutdown_event.is_set():
        try:
            goal = input("\n💭 Enter goal (or 'quit' to exit): ")
            if goal.lower() in ['quit', 'exit', 'q']:
                shutdown_event.set()
                break
            input_queue.put(goal)
        except (EOFError, KeyboardInterrupt):
            shutdown_event.set()
            break

async def main():
    """Launch the AGI with interactive goal input."""
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("🚀 Starting Interactive Symbolic AGI...")
    print("=" * 50)
    
    try:
        # Create and initialize the AGI
        agi = await SymbolicAGI.create()
        
        print("✅ AGI initialized successfully!")
        print("🧠 Ready to receive goals")
        print("=" * 50)
        print("Type goals and press Enter. Type 'quit' to exit.")
        print("Examples:")
        print("  - Search for 'latest AI news' and summarize")
        print("  - Browse https://python.org and tell me about Python")
        print("  - Search for symbolic AI research papers")
        
        # Start input thread
        input_thread_obj = threading.Thread(target=input_thread, daemon=True)
        input_thread_obj.start()
        
        # Main execution loop
        while not shutdown_event.is_set():
            try:
                # Check for new goals from user
                if not input_queue.empty():
                    goal_description = input_queue.get()
                    print(f"🎯 Processing goal: {goal_description}")
                    
                    try:
                        # Use the new plan-based goal processing
                        result = await agi.process_goal_with_plan(goal_description)
                        
                        print(f"✅ Result: {result['summary']}")
                        if result.get('results'):
                            print("📊 Last few step results:")
                            for i, step_result in enumerate(result['results'], 1):
                                status = "✅" if step_result.get('status') == 'success' else "❌"
                                desc = step_result.get('description', 'No description')[:100]
                                print(f"  {status} Step result {i}: {desc}")
                        
                    except Exception as e:
                        print(f"❌ Error executing goal: {e}")
                
                # Brief pause
                await asyncio.sleep(0.1)
                
            except KeyboardInterrupt:
                print("\n⏹️ Shutdown requested by user")
                break
            except Exception as e:
                print(f"⚠️ Error: {e}")
                await asyncio.sleep(1)
    
    except Exception as e:
        print(f"❌ Failed to start AGI: {e}")
        return 1
    
    finally:
        shutdown_event.set()
        try:
            await agi.shutdown()
            print("🛑 AGI shutdown complete")
        except:
            pass
    
    return 0

if __name__ == "__main__":
    print("🧠 Interactive Symbolic AGI")
    print("Press Ctrl+C to shutdown")
    print()
    
    # Check for required environment variables
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ ERROR: OPENAI_API_KEY environment variable not set!")
        print("Please set your OpenAI API key:")
        print("  Windows: $env:OPENAI_API_KEY='your-key-here'")
        print("  Linux/Mac: export OPENAI_API_KEY='your-key-here'")
        sys.exit(1)
    
    # Run the AGI
    exit_code = asyncio.run(main())
    sys.exit(exit_code)