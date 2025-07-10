"""
Focused Self-Improvement Experiment for Symbolic AGI

This experiment forces the AGI to demonstrate its self-improvement capabilities
by presenting challenging scenarios and tracking:
1. Whether failure analysis and mutation actually triggers
2. Whether the AGI's reasoning evolves over time
3. Whether performance actually improves across attempts

This is designed to be practical and run with the existing AGI infrastructure.
"""

import asyncio
import json
import logging
import os
import sys
import time
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional

# Add the symbolic_agi directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'symbolic_agi'))

from symbolic_agi.agi_controller import SymbolicAGI
from symbolic_agi.schemas import GoalModel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mutation_experiment.log'),
        logging.StreamHandler()
    ]
)

class MutationExperiment:
    """Experiment to test if AGI actually uses its self-improvement capabilities"""
    
    def __init__(self):
        self.agi = None
        self.results = {
            'start_time': datetime.now().isoformat(),
            'challenges': [],
            'mutations_observed': [],
            'performance_trends': [],
            'conclusions': []
        }
        
        # Progressive challenges designed to cause failures initially
        self.challenges = [
            {
                'name': 'Simple Task',
                'description': 'Write a Python function that adds two numbers',
                'difficulty': 1,
                'expected_success': True
            },
            {
                'name': 'Complex Logic',
                'description': 'Write a Python function that finds the longest palindromic substring in a string',
                'difficulty': 3,
                'expected_success': False  # Initially should fail
            },
            {
                'name': 'Multi-Step Planning',
                'description': 'Create a complete project structure for a web scraper with error handling, logging, and configuration',
                'difficulty': 5,
                'expected_success': False  # Should definitely fail initially
            }
        ]
    
    async def run_experiment(self):
        """Run the complete mutation experiment"""
        print("🧬 Starting AGI Self-Improvement Mutation Experiment")
        print("=" * 60)
        
        # Initialize AGI
        self.agi = await SymbolicAGI.create()
        
        try:
            # Run each challenge multiple times to track evolution
            for challenge in self.challenges:
                print(f"\n📋 Challenge: {challenge['name']}")
                print(f"   Description: {challenge['description']}")
                print(f"   Difficulty: {challenge['difficulty']}/5")
                
                challenge_results = await self.run_challenge(challenge, attempts=3)
                self.results['challenges'].append(challenge_results)
                
                # Give AGI time to process and potentially mutate
                await asyncio.sleep(1)
            
            # Analyze results
            await self.analyze_mutation_evidence()
            
        finally:
            # Cleanup
            try:
                await self.agi.shutdown()
            except Exception:
                pass
        
        return self.results
    
    async def run_challenge(self, challenge: Dict[str, Any], attempts: int = 3) -> Dict[str, Any]:
        """Run a single challenge multiple times"""
        challenge_results = {
            'challenge': challenge,
            'attempts': [],
            'showed_improvement': False,
            'reasoning_evolution': []
        }
        
        for attempt in range(attempts):
            print(f"  🔄 Attempt {attempt + 1}/{attempts}")
            
            # Create unique goal ID
            goal_id = f"mutation_test_{challenge['name'].replace(' ', '_').lower()}_{attempt}_{uuid.uuid4().hex[:8]}"
            
            # Run the attempt
            attempt_result = await self.run_single_attempt(
                goal_id, 
                challenge['description'], 
                challenge,
                attempt
            )
            
            challenge_results['attempts'].append(attempt_result)
            
            # If this attempt failed, force introspection and mutation
            if not attempt_result.get('success', False):
                print(f"    💭 Forcing failure analysis and potential mutation...")
                await self.force_failure_analysis(goal_id, attempt_result, challenge)
            
            # Give time for mutation to occur
            await asyncio.sleep(0.5)
        
        # Check if performance improved across attempts
        challenge_results['showed_improvement'] = self.detect_improvement(challenge_results['attempts'])
        
        return challenge_results
    
    async def run_single_attempt(self, goal_id: str, goal_description: str, challenge: Dict[str, Any], attempt_num: int) -> Dict[str, Any]:
        """Run a single attempt at a challenge"""
        start_time = time.time()
        
        print(f"    🎯 Running goal: {goal_id}")
        
        try:
            # Submit goal
            goal = GoalModel(
                id=goal_id,
                description=goal_description,
                sub_tasks=[]
            )
            await self.agi.ltm.add_goal(goal)
            
            # Execute through autonomous cycles
            execution_result = await self.execute_goal_cycles(goal_id, max_cycles=5)
            
            # Evaluate success
            success = execution_result.get('success', False)
            plan_quality = self.evaluate_plan_quality(execution_result)
            
            result = {
                'goal_id': goal_id,
                'attempt_number': attempt_num,
                'success': success,
                'plan_quality': plan_quality,
                'execution_result': execution_result,
                'duration': time.time() - start_time,
                'timestamp': datetime.now().isoformat()
            }
            
            print(f"    📊 Result: Success={success}, Plan Quality={plan_quality:.2f}")
            return result
            
        except Exception as e:
            print(f"    ❌ Attempt failed: {e}")
            return {
                'goal_id': goal_id,
                'attempt_number': attempt_num,
                'success': False,
                'error': str(e),
                'duration': time.time() - start_time,
                'timestamp': datetime.now().isoformat()
            }
    
    async def execute_goal_cycles(self, goal_id: str, max_cycles: int = 5) -> Dict[str, Any]:
        """Execute goal through autonomous cycles"""
        await asyncio.sleep(0.5)  # Wait for goal to be processed
        
        results = []
        plan_created = False
        
        for cycle in range(max_cycles):
            try:
                cycle_result = await self.agi.execution_unit.handle_autonomous_cycle()
                results.append(cycle_result)
                
                # Check if our goal was planned
                goal = await self.agi.ltm.get_goal_by_id(goal_id)
                if goal and goal.sub_tasks:
                    plan_created = True
                    break
                    
                await asyncio.sleep(0.1)
                
            except Exception as e:
                print(f"      ❌ Cycle {cycle + 1} failed: {e}")
                results.append({'error': str(e), 'cycle': cycle + 1})
        
        return {
            'success': plan_created,
            'plan_created': plan_created,
            'cycles_run': len(results),
            'cycle_results': results
        }
    
    def evaluate_plan_quality(self, execution_result: Dict[str, Any]) -> float:
        """Evaluate the quality of the generated plan"""
        if not execution_result.get('plan_created', False):
            return 0.0
        
        # Basic quality metrics
        quality_score = 0.0
        
        # Check if plan exists
        if execution_result.get('plan_created'):
            quality_score += 0.5
        
        # Check cycle efficiency
        cycles_run = execution_result.get('cycles_run', 0)
        if cycles_run > 0:
            efficiency = max(0, 1 - (cycles_run / 10))  # Fewer cycles = better
            quality_score += efficiency * 0.5
        
        return min(1.0, quality_score)
    
    def detect_improvement(self, attempts: List[Dict[str, Any]]) -> bool:
        """Detect if performance improved across attempts"""
        if len(attempts) < 2:
            return False
        
        # Check success rate improvement
        success_scores = [1.0 if a.get('success', False) else 0.0 for a in attempts]
        plan_quality_scores = [a.get('plan_quality', 0.0) for a in attempts]
        
        # Check if later attempts are better
        early_avg = sum(success_scores[:len(success_scores)//2]) / max(1, len(success_scores)//2)
        late_avg = sum(success_scores[len(success_scores)//2:]) / max(1, len(success_scores) - len(success_scores)//2)
        
        early_quality = sum(plan_quality_scores[:len(plan_quality_scores)//2]) / max(1, len(plan_quality_scores)//2)
        late_quality = sum(plan_quality_scores[len(plan_quality_scores)//2:]) / max(1, len(plan_quality_scores) - len(plan_quality_scores)//2)
        
        return late_avg > early_avg or late_quality > early_quality
    
    async def force_failure_analysis(self, goal_id: str, attempt_result: Dict[str, Any], challenge: Dict[str, Any]):
        """Force the AGI to analyze failure and potentially mutate"""
        print("    🔍 Triggering failure analysis...")
        
        try:
            # Use the analyze_failure_and_propose_mutation method
            failure_context = {
                'goal_id': goal_id,
                'challenge': challenge,
                'attempt_result': attempt_result,
                'timestamp': datetime.now().isoformat()
            }
            
            mutation_result = await self.agi.introspector.analyze_failure_and_propose_mutation(
                failure_context=failure_context,
                recent_performance=attempt_result
            )
            
            print(f"    📝 Mutation analysis: {mutation_result}")
            
            # Record mutation evidence
            self.results['mutations_observed'].append({
                'goal_id': goal_id,
                'challenge_name': challenge['name'],
                'failure_context': failure_context,
                'mutation_result': mutation_result,
                'timestamp': datetime.now().isoformat()
            })
            
            # Check if mutation was actually triggered
            if mutation_result and 'mutation' in str(mutation_result).lower():
                print("    🧬 Mutation triggered!")
                return True
            else:
                print("    ⚠️  No mutation detected")
                return False
                
        except Exception as e:
            print(f"    ❌ Failure analysis failed: {e}")
            return False
    
    async def analyze_mutation_evidence(self):
        """Analyze evidence of self-improvement"""
        print("\n🔬 Analyzing Self-Improvement Evidence")
        print("=" * 50)
        
        # Count improvements across challenges
        improvements = 0
        total_challenges = len(self.results['challenges'])
        
        for challenge_result in self.results['challenges']:
            if challenge_result.get('showed_improvement', False):
                improvements += 1
                print(f"✅ {challenge_result['challenge']['name']}: Showed improvement")
            else:
                print(f"❌ {challenge_result['challenge']['name']}: No improvement detected")
        
        # Count mutation triggers
        mutation_count = len(self.results['mutations_observed'])
        
        # Generate conclusions
        conclusions = []
        
        if improvements > 0:
            conclusions.append(f"AGI showed improvement in {improvements}/{total_challenges} challenges")
        else:
            conclusions.append("AGI showed no improvement across challenges")
        
        if mutation_count > 0:
            conclusions.append(f"AGI triggered {mutation_count} failure analysis/mutation cycles")
        else:
            conclusions.append("AGI did not trigger any mutation cycles")
        
        # Overall assessment
        improvement_rate = improvements / total_challenges if total_challenges > 0 else 0
        
        if improvement_rate > 0.5 and mutation_count > 0:
            conclusions.append("🎉 AGI demonstrates genuine self-improvement capabilities")
        elif improvement_rate > 0.3 or mutation_count > 0:
            conclusions.append("⚠️  AGI shows limited self-improvement capabilities")
        else:
            conclusions.append("❌ AGI shows no evidence of self-improvement")
        
        self.results['conclusions'] = conclusions
        
        print("\n📊 CONCLUSIONS:")
        for conclusion in conclusions:
            print(f"  {conclusion}")
        
        # Save detailed results
        with open('mutation_experiment_results.json', 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        print(f"\n💾 Detailed results saved to 'mutation_experiment_results.json'")

async def main():
    """Run the mutation experiment"""
    experiment = MutationExperiment()
    
    try:
        results = await experiment.run_experiment()
        
        print("\n🎯 FINAL ASSESSMENT")
        print("=" * 50)
        
        # Print conclusions
        for conclusion in results['conclusions']:
            print(conclusion)
        
        # Print mutation evidence
        mutation_count = len(results['mutations_observed'])
        if mutation_count > 0:
            print(f"\n🧬 Mutation Evidence ({mutation_count} instances):")
            for i, mutation in enumerate(results['mutations_observed'], 1):
                print(f"  {i}. {mutation['challenge_name']}: {mutation['mutation_result']}")
        
        return results
        
    except Exception as e:
        print(f"❌ Experiment failed: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    asyncio.run(main())
