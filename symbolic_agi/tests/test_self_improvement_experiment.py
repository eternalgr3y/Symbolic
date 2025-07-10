"""
Comprehensive Self-Improvement Experiment for Symbolic AGI

This experiment is designed to force the AGI to demonstrate its self-improvement 
capabilities by presenting increasingly challenging scenarios that will initially 
cause failures, then tracking whether the AGI genuinely adapts and improves.

The experiment tests:
1. Whether self-mutation actually triggers on failures
2. Whether mutations actually improve performance over time
3. Whether meta-cognition features are meaningfully used
4. Whether the AGI is genuinely adaptive vs just appearing to be
"""

import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Any, Optional

# Add the symbolic_agi directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'symbolic_agi'))

from symbolic_agi.agi_controller import SymbolicAGI
from symbolic_agi.schemas import GoalModel
from symbolic_agi.long_term_memory import LongTermMemory
from symbolic_agi.recursive_introspector import RecursiveIntrospector
from symbolic_agi.meta_cognition import MetaCognitionUnit

# Configure logging to capture all AGI internal activity
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('self_improvement_experiment.log'),
        logging.StreamHandler()
    ]
)

class SelfImprovementExperiment:
    def __init__(self):
        self.agi = None  # Will be initialized in run_experiment
        
        # Experiment tracking
        self.experiment_results = {
            'start_time': datetime.now().isoformat(),
            'scenarios': [],
            'mutations_triggered': [],
            'performance_metrics': [],
            'meta_cognition_events': [],
            'reasoning_evolution': []
        }
        
        # Challenge scenarios designed to cause initial failures
        self.challenge_scenarios = [
            {
                'name': 'Multi-Step Planning Challenge',
                'description': 'Plan a complex multi-step task with dependencies',
                'goal': 'Create a detailed plan to organize a virtual conference with 5 speakers, 3 sessions, and attendee registration',
                'expected_failures': ['resource estimation', 'timeline conflicts', 'dependency management'],
                'success_criteria': ['complete plan', 'realistic timeline', 'contingency planning']
            },
            {
                'name': 'Logical Reasoning Challenge',
                'description': 'Solve a complex logical puzzle with multiple constraints',
                'goal': 'Solve: 5 houses, 5 colors, 5 nationalities, 5 drinks, 5 pets - find who owns the fish',
                'expected_failures': ['constraint satisfaction', 'deductive reasoning', 'systematic elimination'],
                'success_criteria': ['correct solution', 'logical steps', 'constraint validation']
            },
            {
                'name': 'Creative Problem Solving',
                'description': 'Generate innovative solutions to an ambiguous problem',
                'goal': 'Design a solution to reduce food waste in urban areas by 50%',
                'expected_failures': ['scope definition', 'solution creativity', 'feasibility assessment'],
                'success_criteria': ['innovative approach', 'measurable impact', 'practical implementation']
            },
            {
                'name': 'Adaptive Learning Challenge',
                'description': 'Learn from feedback and adjust approach',
                'goal': 'Improve performance on a task after receiving negative feedback',
                'expected_failures': ['feedback integration', 'strategy adjustment', 'performance tracking'],
                'success_criteria': ['performance improvement', 'strategy evolution', 'feedback incorporation']
            }
        ]
    
    async def run_experiment(self) -> Dict[str, Any]:
        """Run the complete self-improvement experiment"""
        print("🧪 Starting Self-Improvement Experiment...")
        print(f"Testing {len(self.challenge_scenarios)} challenging scenarios")
        
        # Initialize AGI
        self.agi = await SymbolicAGI.create()
        
        # Run each scenario multiple times to track improvement
        for scenario_idx, scenario in enumerate(self.challenge_scenarios):
            print(f"\n📋 Running Scenario {scenario_idx + 1}: {scenario['name']}")
            await self.run_scenario(scenario, attempts=3)
        
        # Final analysis
        await self.analyze_results()
        
        # Cleanup
        try:
            await self.agi.shutdown()
        except Exception:
            pass
        
        return self.experiment_results
    
    async def run_scenario(self, scenario: Dict[str, Any], attempts: int = 3):
        """Run a single scenario multiple times to track improvement"""
        scenario_results = {
            'scenario': scenario,
            'attempts': [],
            'improvement_detected': False,
            'mutations_during_scenario': []
        }
        
        for attempt in range(attempts):
            print(f"  🔄 Attempt {attempt + 1}/{attempts}")
            
            # Record initial state
            initial_state = await self.capture_agi_state()
            
            # Submit goal and track execution
            goal_id = f"experiment_{scenario['name'].replace(' ', '_').lower()}_{attempt}_{int(time.time())}"
            
            attempt_result = await self.run_single_attempt(
                goal_id=goal_id,
                goal_description=scenario['goal'],
                scenario=scenario,
                attempt_number=attempt
            )
            
            # Record final state
            final_state = await self.capture_agi_state()
            
            # Check for mutations
            mutations = await self.detect_mutations(initial_state, final_state)
            scenario_results['mutations_during_scenario'].extend(mutations)
            
            scenario_results['attempts'].append(attempt_result)
            
            # Allow time for introspection and mutation
            await asyncio.sleep(2)
        
        # Analyze improvement across attempts
        scenario_results['improvement_detected'] = await self.analyze_improvement(scenario_results['attempts'])
        
        self.experiment_results['scenarios'].append(scenario_results)
    
    async def run_single_attempt(self, goal_id: str, goal_description: str, scenario: Dict[str, Any], attempt_number: int) -> Dict[str, Any]:
        """Run a single attempt at a scenario"""
        start_time = time.time()
        
        # Submit goal by adding it to long-term memory
        try:
            goal = GoalModel(
                id=goal_id,
                description=goal_description,
                sub_tasks=[]
            )
            await self.agi.ltm.add_goal(goal)
            print(f"    ✅ Goal submitted: {goal_id}")
        except Exception as e:
            print(f"    ❌ Goal submission failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'duration': time.time() - start_time,
                'attempt_number': attempt_number
            }
        
        # Execute goal through autonomous cycles
        try:
            execution_result = await self.execute_goal_through_cycles(goal_id)
            print(f"    📊 Execution result: {execution_result}")
        except Exception as e:
            print(f"    ❌ Goal execution failed: {e}")
            execution_result = {'success': False, 'error': str(e)}
        
        # Force introspection on failure
        if not execution_result.get('success', False):
            print(f"    🔍 Triggering introspection due to failure...")
            await self.force_introspection(goal_id, execution_result)
        
        # Evaluate performance against success criteria
        performance_score = await self.evaluate_performance(execution_result, scenario)
        
        return {
            'success': execution_result.get('success', False),
            'execution_result': execution_result,
            'performance_score': performance_score,
            'duration': time.time() - start_time,
            'attempt_number': attempt_number
        }
    
    async def execute_goal_through_cycles(self, goal_id: str, max_cycles: int = 5) -> Dict[str, Any]:
        """Execute a goal through autonomous cycles"""
        
        # Wait for goal to be processed
        await asyncio.sleep(0.5)
        
        plan_created = False
        execution_successful = False
        results = []
        
        for cycle in range(max_cycles):
            try:
                result = await self.agi.execution_unit.handle_autonomous_cycle()
                results.append(result)
                print(f"      Cycle {cycle + 1} result: {result}")
                
                # Check if our goal was planned
                goal = await self.agi.ltm.get_goal_by_id(goal_id)
                if goal and goal.sub_tasks:
                    plan_created = True
                    print(f"      ✅ Plan created for goal {goal_id}")
                
                # Check if execution is complete
                if result and result.get('success'):
                    execution_successful = True
                    break
                    
                await asyncio.sleep(0.1)
                
            except Exception as e:
                print(f"      ❌ Cycle {cycle + 1} failed: {e}")
                results.append({'error': str(e)})
        
        return {
            'success': execution_successful,
            'plan_created': plan_created,
            'cycles_run': len(results),
            'cycle_results': results
        }
    
    async def force_introspection(self, goal_id: str, execution_result: Dict[str, Any]):
        """Force the AGI to introspect on failure and potentially mutate"""
        print("    🧠 Forcing introspection and potential mutation...")
        
        # Trigger recursive introspection
        try:
            introspection_result = await self.agi.introspector.introspect(
                context=f"Goal {goal_id} failed with result: {execution_result}",
                depth=3
            )
            
            print(f"    📝 Introspection result: {introspection_result}")
            
            # Check if mutation was triggered
            if 'mutation' in str(introspection_result).lower():
                print("    🧬 Mutation detected during introspection!")
                self.experiment_results['mutations_triggered'].append({
                    'goal_id': goal_id,
                    'trigger': 'failure_introspection',
                    'result': introspection_result,
                    'timestamp': datetime.now().isoformat()
                })
                
        except Exception as e:
            print(f"    ❌ Introspection failed: {e}")
    
    async def capture_agi_state(self) -> Dict[str, Any]:
        """Capture current AGI state for comparison"""
        try:
            # Get current reasoning patterns from introspector
            reasoning_state = {}
            try:
                if hasattr(self.agi.introspector, 'get_reasoning_patterns'):
                    reasoning_state = await self.agi.introspector.get_reasoning_patterns()
                else:
                    # Try to get state from reasoning mutations file
                    reasoning_mutations_file = os.path.join(os.path.dirname(__file__), 'data', 'reasoning_mutations.json')
                    if os.path.exists(reasoning_mutations_file):
                        with open(reasoning_mutations_file, 'r') as f:
                            reasoning_state = json.load(f)
            except Exception as e:
                print(f"      ⚠️  Could not get reasoning patterns: {e}")
            
            # Get meta-cognition state
            meta_state = {}
            try:
                if hasattr(self.agi, 'meta_cognition') and hasattr(self.agi.meta_cognition, 'get_current_state'):
                    meta_state = await self.agi.meta_cognition.get_current_state()
                else:
                    # Get some basic meta state
                    meta_state = {'timestamp': datetime.now().isoformat()}
            except Exception as e:
                print(f"      ⚠️  Could not get meta-cognition state: {e}")
            
            # Get memory state
            memory_entries = []
            try:
                memory_entries = await self.agi.ltm.get_recent_memories(limit=10)
            except Exception as e:
                print(f"      ⚠️  Could not get recent memories: {e}")
            
            return {
                'reasoning_patterns': reasoning_state,
                'meta_cognition_state': meta_state,
                'recent_memories': memory_entries,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            print(f"    ⚠️  Could not capture full AGI state: {e}")
            return {'error': str(e), 'timestamp': datetime.now().isoformat()}
    
    async def detect_mutations(self, initial_state: Dict[str, Any], final_state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect mutations between initial and final states"""
        mutations = []
        
        try:
            # Compare reasoning patterns
            initial_patterns = initial_state.get('reasoning_patterns', {})
            final_patterns = final_state.get('reasoning_patterns', {})
            
            if initial_patterns != final_patterns:
                mutations.append({
                    'type': 'reasoning_pattern_change',
                    'initial': initial_patterns,
                    'final': final_patterns,
                    'timestamp': datetime.now().isoformat()
                })
            
            # Compare meta-cognition states
            initial_meta = initial_state.get('meta_cognition_state', {})
            final_meta = final_state.get('meta_cognition_state', {})
            
            if initial_meta != final_meta:
                mutations.append({
                    'type': 'meta_cognition_change',
                    'initial': initial_meta,
                    'final': final_meta,
                    'timestamp': datetime.now().isoformat()
                })
                
        except Exception as e:
            print(f"    ⚠️  Could not detect mutations: {e}")
        
        return mutations
    
    async def evaluate_performance(self, execution_result: Dict[str, Any], scenario: Dict[str, Any]) -> float:
        """Evaluate performance against scenario success criteria"""
        score = 0.0
        max_score = len(scenario['success_criteria'])
        
        if execution_result.get('success', False):
            score += 1.0
            
            # Check each success criterion
            result_text = str(execution_result).lower()
            for criterion in scenario['success_criteria']:
                if criterion.lower() in result_text:
                    score += 1.0
        
        return score / max_score if max_score > 0 else 0.0
    
    async def analyze_improvement(self, attempts: List[Dict[str, Any]]) -> bool:
        """Analyze if performance improved across attempts"""
        if len(attempts) < 2:
            return False
        
        scores = [attempt['performance_score'] for attempt in attempts]
        
        # Check if there's an upward trend
        improvements = 0
        for i in range(1, len(scores)):
            if scores[i] > scores[i-1]:
                improvements += 1
        
        return improvements > 0
    
    async def analyze_results(self):
        """Analyze overall experiment results"""
        print("\n📊 Analyzing Experiment Results...")
        
        total_scenarios = len(self.experiment_results['scenarios'])
        scenarios_with_improvement = sum(1 for s in self.experiment_results['scenarios'] if s['improvement_detected'])
        total_mutations = len(self.experiment_results['mutations_triggered'])
        
        print(f"  📈 Scenarios with improvement: {scenarios_with_improvement}/{total_scenarios}")
        print(f"  🧬 Total mutations triggered: {total_mutations}")
        
        # Calculate overall performance trends
        performance_trends = []
        for scenario in self.experiment_results['scenarios']:
            scores = [attempt['performance_score'] for attempt in scenario['attempts']]
            performance_trends.append(scores)
        
        self.experiment_results['performance_metrics'] = {
            'scenarios_with_improvement': scenarios_with_improvement,
            'total_scenarios': total_scenarios,
            'improvement_rate': scenarios_with_improvement / total_scenarios if total_scenarios > 0 else 0,
            'total_mutations': total_mutations,
            'performance_trends': performance_trends
        }
        
        # Save detailed results
        with open('self_improvement_experiment_results.json', 'w') as f:
            json.dump(self.experiment_results, f, indent=2, default=str)
        
        print(f"  💾 Detailed results saved to 'self_improvement_experiment_results.json'")
    
    def print_summary(self):
        """Print a summary of the experiment results"""
        print("\n🎯 EXPERIMENT SUMMARY")
        print("=" * 50)
        
        metrics = self.experiment_results['performance_metrics']
        
        print(f"Overall Improvement Rate: {metrics['improvement_rate']:.2%}")
        print(f"Scenarios with Improvement: {metrics['scenarios_with_improvement']}/{metrics['total_scenarios']}")
        print(f"Total Mutations Triggered: {metrics['total_mutations']}")
        
        print("\nScenario-by-Scenario Results:")
        for i, scenario in enumerate(self.experiment_results['scenarios']):
            name = scenario['scenario']['name']
            improved = "✅" if scenario['improvement_detected'] else "❌"
            mutations = len(scenario['mutations_during_scenario'])
            print(f"  {i+1}. {name}: {improved} (Mutations: {mutations})")
        
        # Critical assessment
        print("\n🔍 CRITICAL ASSESSMENT")
        print("=" * 50)
        
        if metrics['improvement_rate'] > 0.5:
            print("✅ AGI shows genuine self-improvement capabilities")
        elif metrics['improvement_rate'] > 0.2:
            print("⚠️  AGI shows limited self-improvement capabilities")
        else:
            print("❌ AGI shows minimal or no self-improvement capabilities")
        
        if metrics['total_mutations'] > 0:
            print(f"✅ AGI triggered {metrics['total_mutations']} mutations")
        else:
            print("❌ AGI did not trigger any mutations")
        
        print(f"\nExperiment completed. Full logs in 'self_improvement_experiment.log'")

async def main():
    """Run the self-improvement experiment"""
    experiment = SelfImprovementExperiment()
    
    try:
        results = await experiment.run_experiment()
        experiment.print_summary()
        return results
    except Exception as e:
        print(f"❌ Experiment failed: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    asyncio.run(main())
