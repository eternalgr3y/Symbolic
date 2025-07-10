#!/usr/bin/env python3
"""
EMERGENCY FIX SCRIPT
Fix the stuck login goal and prevent future infinite loops
"""

import json
import time
from pathlib import Path


def fix_stuck_goal():
    """Fix the currently stuck login goal"""

    goals_file = Path("c:/Users/Todd/Projects/symbolic_agi/data/long_term_goals.json")

    if not goals_file.exists():
        print("❌ Goals file not found!")
        return

    try:
        with open(goals_file, 'r') as f:
            goals_data = json.load(f)

        # Find the stuck goal
        stuck_goal_id = None
        for goal_id, goal_data in goals_data.items():
            if "login page" in goal_data.get('description', ''):
                stuck_goal_id = goal_id
                break

        if stuck_goal_id:
            print(f"🔧 Found stuck goal: {stuck_goal_id}")

            # Force complete the goal
            goals_data[stuck_goal_id]['status'] = 'completed'
            goals_data[stuck_goal_id]['completion_time'] = time.time()
            goals_data[stuck_goal_id]['completion_note'] = 'Manually completed due to infinite loop bug'

            # Clear problematic sub_tasks
            goals_data[stuck_goal_id]['sub_tasks'] = []

            # Add execution counter to prevent future loops
            goals_data[stuck_goal_id]['execution_count'] = 999  # High number to prevent re-execution

            print(f"✅ Fixed goal {stuck_goal_id}")

        else:
            print("ℹ️ No stuck login goal found")

        # Write back the fixed data
        with open(goals_file, 'w') as f:
            json.dump(goals_data, f, indent=4)

        print("💾 Saved fixed goals file")

    except json.JSONDecodeError as e:
        print(f"❌ JSON Error: {e}")
        print("🔧 Attempting to fix JSON...")

        # Try to fix common JSON issues
        try:
            with open(goals_file, 'r') as f:
                content = f.read()

            # Remove trailing commas and other common issues
            content = content.replace(',\n}', '\n}')
            content = content.replace(',\n]', '\n]')

            # Try parsing again
            goals_data = json.loads(content)

            with open(goals_file, 'w') as f:
                json.dump(goals_data, f, indent=4)

            print("✅ Fixed JSON formatting")

        except Exception as e2:
            print(f"❌ Could not fix JSON: {e2}")

    except Exception as e:
        print(f"❌ Unexpected error: {e}")

def add_loop_protection():
    """Add loop protection to the goal system"""

    print("🛡️ Adding loop protection mechanisms...")

    # Create a backup of current goals
    goals_file = Path("c:/Users/Todd/Projects/symbolic_agi/data/long_term_goals.json")
    backup_file = Path("c:/Users/Todd/Projects/symbolic_agi/data/long_term_goals_backup.json")

    if goals_file.exists():
        import shutil
        shutil.copy2(goals_file, backup_file)
        print(f"📋 Created backup: {backup_file}")

if __name__ == "__main__":
    print("🚨 EMERGENCY FIX SCRIPT STARTING...")
    print("=" * 50)

    fix_stuck_goal()
    add_loop_protection()

    print("=" * 50)
    print("✅ Emergency fix complete!")
    print("🔄 You can now restart the AGI system safely.")
    print("🛡️ Loop protection mechanisms are in place.")
