import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def debug_agi():
    from symbolic_agi.agi_controller import SymbolicAGI
    
    print("Creating AGI...")
    agi = await SymbolicAGI.create()
    
    print("Available methods:")
    methods = [method for method in dir(agi) if not method.startswith('_') and callable(getattr(agi, method))]
    for method in sorted(methods):
        print(f"  - {method}")
    
    # Try to find goal-related methods
    goal_methods = [m for m in methods if 'goal' in m.lower()]
    print(f"\nGoal-related methods: {goal_methods}")

if __name__ == "__main__":
    asyncio.run(debug_agi())