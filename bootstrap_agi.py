#!/usr/bin/env python3
"""
🧠 AGI Kickstarter - Give your AGI some initial motivation!
Run this to bootstrap your AGI with initial drives and goals
"""

import asyncio
import sys
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from symbolic_agi.agi_controller import SymbolicAGI
from symbolic_agi.schemas import GoalModel, ActionStep

async def bootstrap_agi():
    """Give the AGI some initial goals to get it started."""
    
    logger.info("🚀 Bootstrapping AGI with initial motivation...")
    
    try:
        # Create the AGI
        agi = await SymbolicAGI.create()
        
        # Create some initial goals to kickstart the AGI
        initial_goals = [
            {
                "description": "Learn about my environment and capabilities",
                "sub_tasks": [
                    ActionStep(action="list_files", parameters={}, assigned_persona="orchestrator"),
                    ActionStep(action="read_own_source_code", parameters={"file_name": "config.py"}, assigned_persona="orchestrator"),
                    ActionStep(action="get_current_datetime", parameters={}, assigned_persona="orchestrator"),
                ]
            },
            {
                "description": "Explore my workspace and create a simple file",
                "sub_tasks": [
                    ActionStep(action="write_file", parameters={"file_path": "hello_world.txt", "content": "Hello! I am a Symbolic AGI and I'm alive!"}, assigned_persona="orchestrator"),
                    ActionStep(action="read_file", parameters={"file_path": "hello_world.txt"}, assigned_persona="orchestrator"),
                ]
            },
            {
                "description": "Test my web search capabilities", 
                "sub_tasks": [
                    ActionStep(action="web_search", parameters={"query": "artificial intelligence latest news", "num_results": 3}, assigned_persona="orchestrator"),
                ]
            }
        ]
        
        # Add goals to the AGI
        for goal_data in initial_goals:
            plan = goal_data["sub_tasks"]
            goal = GoalModel(
                description=goal_data["description"], 
                sub_tasks=plan, 
                original_plan=plan
            )
            await agi.ltm.add_goal(goal)
            logger.info("✅ Added goal: %s", goal.description)
        
        # Boost the consciousness drives to motivate action
        if agi.consciousness:
            # Give it some initial drives (consciousness might use different structure)
            try:
                if hasattr(agi.consciousness, 'drives'):
                    if hasattr(agi.consciousness.drives, 'curiosity'):
                        agi.consciousness.drives.curiosity = 0.8
                        agi.consciousness.drives.autonomy = 0.7 
                        agi.consciousness.drives.growth = 0.6
                    else:
                        # Alternative drive structure
                        agi.consciousness.drives['curiosity'] = 0.8
                        agi.consciousness.drives['autonomy'] = 0.7
                        agi.consciousness.drives['growth'] = 0.6
                    logger.info("🧠 Boosted consciousness drives")
                else:
                    logger.warning("🧠 Consciousness exists but no drives found")
            except Exception as e:
                logger.warning("🧠 Consciousness drives not accessible: %s", e)
            
            # Add some life events to give context
            try:
                agi.consciousness.add_life_event(
                    "I have been awakened and given initial goals to explore my capabilities",
                    importance=0.9
                )
            except Exception as e:
                logger.warning("🧠 Could not add life event: %s", e)
        
        logger.info("🎯 AGI bootstrapped successfully!")
        logger.info("💡 Your AGI now has motivation and goals to pursue!")
        
        await agi.shutdown()
        
    except Exception as e:
        logger.error("❌ Error bootstrapping AGI: %s", e)
        return 1
    
    return 0

if __name__ == "__main__":
    logger.info("🧠 AGI Motivation Bootstrapper")
    logger.info("This will give your AGI some initial goals and drives")
    logger.info("")
    
    exit_code = asyncio.run(bootstrap_agi())
    
    if exit_code == 0:
        logger.info("\n🚀 Now run your AGI again with: python launch_agi.py")
        logger.info("Your AGI should now have motivation to act!")
    
    sys.exit(exit_code)