#!/usr/bin/env python3
"""
🔧 AGI Agent Bootstrapper
Create essential agents for your AGI to function properly
"""

import asyncio
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from symbolic_agi.agi_controller import SymbolicAGI

async def create_essential_agents():
    """Create the essential agents your AGI needs."""
    
    print("🤖 Creating essential agents for your AGI...")
    
    try:
        # Create the AGI
        agi = await SymbolicAGI.create()
        
        # Create essential agents
        essential_agents = [
            {"name": "QA_Agent_Alpha", "persona": "qa"},
            {"name": "Research_Agent_Beta", "persona": "researcher"},  
            {"name": "Code_Agent_Gamma", "persona": "developer"},
            {"name": "Analysis_Agent_Delta", "persona": "analyst"},
        ]
        
        for agent_data in essential_agents:
            agi.agent_pool.add_agent(
                name=agent_data["name"],
                persona=agent_data["persona"], 
                memory=agi.memory
            )
            print(f"✅ Created {agent_data['name']} with persona '{agent_data['persona']}'")
        
        print(f"\n🎯 Created {len(essential_agents)} essential agents!")
        print("Your AGI now has the specialists it needs to function properly!")
        
        await agi.shutdown()
        
    except Exception as e:
        print(f"❌ Error creating agents: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    print("🤖 AGI Agent Bootstrapper")
    print("Creating essential specialist agents...")
    print()
    
    exit_code = asyncio.run(create_essential_agents())
    
    if exit_code == 0:
        print("\n🚀 Now restart your AGI with: python launch_agi.py")
        print("Your AGI should now execute plans successfully!")
    
    sys.exit(exit_code)