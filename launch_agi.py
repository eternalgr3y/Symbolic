#!/usr/bin/env python3
"""
🚀 Simple AGI Launcher
Run this script to start your Symbolic AGI
"""

import os
import sys
import asyncio
import logging

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from symbolic_agi.agi_controller import SymbolicAGI

async def main():
    """Launch the AGI with proper initialization."""
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("🚀 Starting Symbolic AGI...")
    print("=" * 50)
    
    try:
        # Create and initialize the AGI
        agi = await SymbolicAGI.create()
        
        # Start background tasks
        await agi.start_background_tasks()
        
        print("✅ AGI initialized successfully!")
        print("🧠 Meta-cognition active")
        print("🎯 Autonomous goal generation enabled")
        print("🔄 Background tasks running")
        print("=" * 50)
        
        # Main execution loop with better signal handling
        print("🏃 Starting autonomous execution cycle...")
        
        while True:
            try:
                result = await agi.execution_unit.handle_autonomous_cycle()
                if result and result.get("description"):
                    print(f"🤖 AGI: {result['description']}")
                
                # Brief pause between cycles
                await asyncio.sleep(2)
                
            except KeyboardInterrupt:
                print("\n⏹️ Shutdown requested by user")
                break
            except asyncio.CancelledError:
                print("\n⏹️ Execution cancelled")
                break
            except Exception as e:
                print(f"⚠️ Error in execution cycle: {e}")
                await asyncio.sleep(5)  # Wait before retrying
    
    except Exception as e:
        print(f"❌ Failed to start AGI: {e}")
        return 1
    
    finally:
        try:
            await agi.shutdown()
            print("🛑 AGI shutdown complete")
        except:
            pass
    
    return 0

if __name__ == "__main__":
    print("🧠 Symbolic AGI - Autonomous Intelligence System")
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