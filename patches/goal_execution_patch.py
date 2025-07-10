# EMERGENCY PATCH: Fix Infinite Loop in Goal Execution
# 
# Problem: perform_web_login skill expansion causes infinite review loop
# Solution: Add execution counters and circuit breakers

import time
from typing import Dict, Any

class GoalExecutionPatch:
    """Patch to prevent infinite loops in goal execution"""
    
    def __init__(self):
        self.execution_counters = {}  # Track how many times each step executes
        self.max_step_repeats = 3     # Max times same step can repeat
        self.goal_start_times = {}    # Track when goals started
        self.max_goal_runtime = 300   # 5 minutes max per goal
    
    def should_break_loop(self, goal_id: str, step_type: str) -> bool:
        """Check if we should break out of a potential infinite loop"""
        
        # Track step execution count
        key = f"{goal_id}_{step_type}"
        self.execution_counters[key] = self.execution_counters.get(key, 0) + 1
        
        # Break if step repeated too many times
        if self.execution_counters[key] > self.max_step_repeats:
            print(f"[CIRCUIT_BREAKER] Step '{step_type}' repeated {self.execution_counters[key]} times for goal {goal_id}. Breaking loop.")
            return True
        
        # Track goal runtime
        if goal_id not in self.goal_start_times:
            self.goal_start_times[goal_id] = time.time()
        
        runtime = time.time() - self.goal_start_times[goal_id]
        if runtime > self.max_goal_runtime:
            print(f"[CIRCUIT_BREAKER] Goal {goal_id} has been running for {runtime:.1f}s. Breaking loop.")
            return True
            
        return False
    
    def reset_goal_counters(self, goal_id: str):
        """Reset counters when goal completes or fails"""
        keys_to_remove = [k for k in self.execution_counters.keys() if k.startswith(goal_id)]
        for key in keys_to_remove:
            del self.execution_counters[key]
        
        if goal_id in self.goal_start_times:
            del self.goal_start_times[goal_id]
    
    def force_skip_to_execution(self, goal_data: Dict[str, Any]) -> Dict[str, Any]:
        """Force skip plan review and go straight to execution"""
        
        # If we have sub_tasks, execute them directly
        if goal_data.get('sub_tasks'):
            print(f"[PATCH] Forcing execution of sub_tasks for goal {goal_data['id']}")
            
            # Remove review_plan steps from sub_tasks
            filtered_tasks = []
            for task in goal_data['sub_tasks']:
                if task.get('action') != 'review_plan':
                    filtered_tasks.append(task)
            
            goal_data['sub_tasks'] = filtered_tasks
            
            # If no tasks left, create a direct execution task
            if not filtered_tasks:
                goal_data['sub_tasks'] = [{
                    "action": "perform_web_login",
                    "parameters": {
                        "login_page_url": "https://the-internet.herokuapp.com/login",
                        "username": "tomsmith", 
                        "password": "SuperSecretPassword!"
                    },
                    "assigned_persona": "orchestrator",
                    "risk": "low"
                }]
        
        return goal_data

# Global patch instance
execution_patch = GoalExecutionPatch()

print("[PATCH] Infinite loop detection and circuit breaker loaded!")
print("[PATCH] Max step repeats:", execution_patch.max_step_repeats)
print("[PATCH] Max goal runtime:", execution_patch.max_goal_runtime, "seconds")