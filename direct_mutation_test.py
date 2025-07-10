"""
Simple Direct Test of AGI Self-Mutation Capabilities

This test directly calls the AGI's mutation methods to verify they work,
without getting caught in the autonomous loop issues.
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime

# Add the symbolic_agi directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'symbolic_agi'))

from symbolic_agi.recursive_introspector import RecursiveIntrospector
from symbolic_agi.agi_controller import SymbolicAGI

# Configure logging
logging.basicConfig(level=logging.INFO)

async def test_mutation_directly():
    """Test the mutation capabilities directly without autonomous loops"""
    print("🧬 Direct Mutation Test")
    print("=" * 50)
    
    try:
        # Create AGI instance
        agi = await SymbolicAGI.create()
        introspector = agi.introspector
        
        print("✅ AGI initialized successfully")
        
        # Test 1: Check if reasoning mutations are loaded
        print(f"\n📋 Test 1: Check existing mutations")
        initial_mutations = len(introspector.reasoning_mutations)
        print(f"Initial mutation count: {initial_mutations}")
        
        if initial_mutations > 0:
            print("✅ AGI has existing mutations:")
            for i, mutation in enumerate(introspector.reasoning_mutations):
                print(f"  {i+1}. {mutation[:100]}...")
        else:
            print("⚠️  No existing mutations found")
        
        # Test 2: Force failure analysis and mutation
        print(f"\n📋 Test 2: Force failure analysis")
        failure_context = {
            'goal_id': 'test_mutation',
            'error': 'Plan failed due to insufficient reasoning',
            'attempts': 3,
            'timestamp': datetime.now().isoformat()
        }
        
        print("Triggering failure analysis...")
        await introspector.analyze_failure_and_propose_mutation(failure_context)
        
        # Check if mutation was added
        new_mutation_count = len(introspector.reasoning_mutations)
        print(f"Mutation count after analysis: {new_mutation_count}")
        
        if new_mutation_count > initial_mutations:
            print("✅ NEW MUTATION DETECTED!")
            print(f"New mutation: {introspector.reasoning_mutations[-1]}")
        else:
            print("❌ No new mutation was generated")
        
        # Test 3: Test meta-assessment
        print(f"\n📋 Test 3: Test meta-assessment")
        test_cycle_data = {
            'performance': 'poor',
            'reasoning_quality': 'low',
            'goal_achievement': False,
            'timestamp': datetime.now().isoformat()
        }
        
        print("Triggering meta-assessment...")
        await introspector.meta_assess(test_cycle_data)
        
        # Check if mutation was added
        final_mutation_count = len(introspector.reasoning_mutations)
        print(f"Mutation count after meta-assessment: {final_mutation_count}")
        
        if final_mutation_count > new_mutation_count:
            print("✅ META-ASSESSMENT TRIGGERED MUTATION!")
            print(f"New mutation: {introspector.reasoning_mutations[-1]}")
        else:
            print("❌ Meta-assessment did not generate mutation")
        
        # Test 4: Test LLM reflection capability
        print(f"\n📋 Test 4: Test LLM reflection")
        reflection_prompt = "What is the most important thing for an AGI to improve its reasoning?"
        
        print("Testing LLM reflection...")
        reflection_result = await introspector.llm_reflect(reflection_prompt)
        
        if reflection_result and len(reflection_result) > 10:
            print("✅ LLM reflection working")
            print(f"Reflection: {reflection_result[:200]}...")
        else:
            print("❌ LLM reflection failed or returned empty result")
        
        # Test 5: Test reason_with_context
        print(f"\n📋 Test 5: Test reason_with_context")
        test_prompt = "Plan a simple task: write a hello world function in Python"
        
        print("Testing reason_with_context...")
        reasoning_result = await introspector.reason_with_context(test_prompt)
        
        if reasoning_result:
            print("✅ reason_with_context working")
            try:
                parsed = json.loads(reasoning_result)
                print(f"Generated plan with {len(parsed.get('plan', []))} steps")
            except:
                print("⚠️  Response not valid JSON, but method returned something")
        else:
            print("❌ reason_with_context failed")
        
        # Final assessment
        print(f"\n🎯 FINAL ASSESSMENT")
        print("=" * 50)
        
        mutations_generated = final_mutation_count - initial_mutations
        
        if mutations_generated > 0:
            print(f"✅ AGI generated {mutations_generated} new mutations during testing")
            print("✅ Self-mutation capability is WORKING")
        else:
            print("❌ AGI did not generate any mutations")
            print("❌ Self-mutation capability appears BROKEN")
        
        if reflection_result and reasoning_result:
            print("✅ Core reasoning capabilities are working")
        else:
            print("❌ Core reasoning capabilities have issues")
        
        # Save results
        results = {
            'initial_mutations': initial_mutations,
            'final_mutations': final_mutation_count,
            'mutations_generated': mutations_generated,
            'reflection_working': bool(reflection_result),
            'reasoning_working': bool(reasoning_result),
            'test_timestamp': datetime.now().isoformat()
        }
        
        with open('direct_mutation_test_results.json', 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n💾 Results saved to 'direct_mutation_test_results.json'")
        
        # Cleanup
        await agi.shutdown()
        
        return results
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return None

async def main():
    """Run the direct mutation test"""
    return await test_mutation_directly()

if __name__ == "__main__":
    asyncio.run(main())
