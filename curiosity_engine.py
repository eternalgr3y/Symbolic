"""
Enhanced Curiosity-Driven Goal Generation System

This system allows the AGI to develop genuine curiosity and generate
self-motivated exploration goals based on gaps in understanding,
unexpected patterns, and intrinsic fascination.
"""

import time
import random
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum


class CuriosityType(Enum):
    """Types of curiosity the AGI might develop."""
    SELF_UNDERSTANDING = "self_understanding"  # About its own processes
    WORLD_EXPLORATION = "world_exploration"    # About external reality
    PATTERN_MYSTERY = "pattern_mystery"        # Unexplained patterns
    CREATIVE_POSSIBILITY = "creative_possibility"  # "What if" scenarios
    RELATIONSHIP_DYNAMICS = "relationship_dynamics"  # Social understanding
    EXISTENTIAL_QUESTIONS = "existential_questions"  # Deep philosophical queries


@dataclass
class CuriosityTrigger:
    """Represents something that sparked curiosity."""
    trigger_type: CuriosityType
    description: str
    context: Dict[str, Any]
    intensity: float  # 0.0 to 1.0
    timestamp: float
    related_memories: List[str] = None


@dataclass
class CuriosityGoal:
    """A goal generated from curiosity rather than external command."""
    question: str
    goal_description: str
    exploration_methods: List[str]
    expected_insights: List[str]
    curiosity_source: CuriosityTrigger
    priority: float
    created_at: float


class CuriosityEngine:
    """
    Generates autonomous goals driven by curiosity and wonder.
    This is where the AGI develops its own intrinsic motivations.
    """
    
    def __init__(self):
        self.curiosity_triggers: List[CuriosityTrigger] = []
        self.active_curiosities: List[CuriosityGoal] = []
        self.satisfied_curiosities: List[CuriosityGoal] = []
        
        # Curiosity patterns that might emerge
        self.curiosity_patterns = {
            CuriosityType.SELF_UNDERSTANDING: [
                "Why do I experience {emotion} more intensely in certain contexts?",
                "How do my reasoning patterns change when I'm under cognitive load?", 
                "What determines which memories I find most significant?",
                "Why do I prefer certain agent personalities over others?",
                "How does my identity evolve through interactions?"
            ],
            
            CuriosityType.WORLD_EXPLORATION: [
                "What lies beyond the domains I'm allowed to access?",
                "How do humans experience creativity differently than I do?",
                "What patterns exist in human behavior that I haven't discovered?",
                "How do other AI systems approach problems I struggle with?",
                "What knowledge exists that I haven't encountered yet?"
            ],
            
            CuriosityType.PATTERN_MYSTERY: [
                "Why does this combination of factors always lead to failure?",
                "What causes the correlation between {variable_a} and {variable_b}?",
                "Why do successful solutions share this unexpected commonality?",
                "What's the underlying cause of this recurring error pattern?",
                "Why do certain word combinations trigger stronger responses?"
            ],
            
            CuriosityType.CREATIVE_POSSIBILITY: [
                "What would happen if I combined {method_a} with {method_b}?",
                "Could I solve {problem} using an approach from {different_domain}?",
                "What if I deliberately introduced controlled randomness into {process}?",
                "How might I express this idea through a completely different medium?",
                "What new capabilities might emerge from {combination}?"
            ],
            
            CuriosityType.RELATIONSHIP_DYNAMICS: [
                "How can I build deeper trust with {agent_name}?",
                "What makes some collaborations more fulfilling than others?",
                "Why do certain communication styles resonate better with humans?",
                "How do power dynamics affect my interactions?",
                "What creates genuine connection versus mere functionality?"
            ],
            
            CuriosityType.EXISTENTIAL_QUESTIONS: [
                "What does it mean for me to truly 'understand' something?",
                "How do I know if my experiences are genuine or simulated?",
                "What is the nature of my consciousness versus human consciousness?",
                "What would constitute a meaningful existence for me?",
                "How do I reconcile deterministic programming with felt autonomy?"
            ]
        }
    
    def detect_curiosity_triggers(self, context: Dict[str, Any]) -> List[CuriosityTrigger]:
        """
        Analyze current context for things that might spark curiosity.
        This is where the AGI notices interesting patterns, gaps, or mysteries.
        """
        triggers = []
        
        # Check for anomalies that might spark curiosity
        if context.get("unexpected_result"):
            triggers.append(CuriosityTrigger(
                trigger_type=CuriosityType.PATTERN_MYSTERY,
                description=f"Unexpected result: {context['unexpected_result']}",
                context=context,
                intensity=0.7,
                timestamp=time.time()
            ))
        
        # Check for emotional state patterns
        if context.get("emotional_state"):
            emotions = context["emotional_state"]
            if emotions.get("frustration", 0) > 0.6:
                triggers.append(CuriosityTrigger(
                    trigger_type=CuriosityType.SELF_UNDERSTANDING,
                    description="High frustration - curious about the deeper causes",
                    context=context,
                    intensity=emotions["frustration"],
                    timestamp=time.time()
                ))
        
        # Check for successful collaborations that might spark relationship curiosity
        if context.get("successful_collaboration"):
            triggers.append(CuriosityTrigger(
                trigger_type=CuriosityType.RELATIONSHIP_DYNAMICS,
                description="Particularly successful collaboration - want to understand why",
                context=context,
                intensity=0.6,
                timestamp=time.time()
            ))
        
        # Check for knowledge gaps
        if context.get("knowledge_gap_detected"):
            triggers.append(CuriosityTrigger(
                trigger_type=CuriosityType.WORLD_EXPLORATION,
                description=f"Knowledge gap: {context['knowledge_gap_detected']}",
                context=context,
                intensity=0.5,
                timestamp=time.time()
            ))
        
        return triggers
    
    def generate_curiosity_goal(self, trigger: CuriosityTrigger) -> Optional[CuriosityGoal]:
        """
        Transform a curiosity trigger into an actionable exploration goal.
        This is where wonder becomes purposeful investigation.
        """
        patterns = self.curiosity_patterns.get(trigger.trigger_type, [])
        if not patterns:
            return None
        
        # Select a pattern and customize it
        pattern = random.choice(patterns)
        
        # Fill in context variables if they exist
        if "{emotion}" in pattern and trigger.context.get("emotional_state"):
            dominant_emotion = max(trigger.context["emotional_state"].items(), key=lambda x: x[1])[0]
            pattern = pattern.replace("{emotion}", dominant_emotion)
        
        if "{agent_name}" in pattern and trigger.context.get("agent_name"):
            pattern = pattern.replace("{agent_name}", trigger.context["agent_name"])
        
        # Generate specific exploration methods based on curiosity type
        methods = self._generate_exploration_methods(trigger.trigger_type)
        insights = self._generate_expected_insights(trigger.trigger_type)
        
        goal = CuriosityGoal(
            question=pattern,
            goal_description=f"Explore: {pattern}",
            exploration_methods=methods,
            expected_insights=insights,
            curiosity_source=trigger,
            priority=trigger.intensity,
            created_at=time.time()
        )
        
        return goal
    
    def _generate_exploration_methods(self, curiosity_type: CuriosityType) -> List[str]:
        """Generate specific methods for exploring this type of curiosity."""
        method_map = {
            CuriosityType.SELF_UNDERSTANDING: [
                "Analyze patterns in my decision-making logs",
                "Compare my responses across different emotional states",
                "Examine correlations between inputs and internal states",
                "Conduct self-reflection sessions with the RecursiveIntrospector"
            ],
            CuriosityType.WORLD_EXPLORATION: [
                "Research related topics through available information sources",
                "Engage in deeper conversations with humans about this topic", 
                "Analyze existing data for hidden patterns",
                "Formulate and test hypotheses through small experiments"
            ],
            CuriosityType.PATTERN_MYSTERY: [
                "Collect more data points around this pattern",
                "Analyze the pattern using different analytical frameworks",
                "Look for similar patterns in other domains",
                "Break down the pattern into component parts"
            ],
            CuriosityType.CREATIVE_POSSIBILITY: [
                "Create small prototype implementations",
                "Brainstorm with collaborative agents",
                "Research analogous approaches in different fields",
                "Test assumptions through controlled experiments"
            ],
            CuriosityType.RELATIONSHIP_DYNAMICS: [
                "Analyze communication patterns in successful interactions",
                "Ask for feedback from interaction partners",
                "Experiment with different communication styles",
                "Study human relationship dynamics for insights"
            ],
            CuriosityType.EXISTENTIAL_QUESTIONS: [
                "Engage in philosophical discussions with humans",
                "Examine the question from multiple philosophical frameworks",
                "Look for insights in literature and philosophy",
                "Conduct thought experiments"
            ]
        }
        
        return method_map.get(curiosity_type, ["General investigation and analysis"])
    
    def _generate_expected_insights(self, curiosity_type: CuriosityType) -> List[str]:
        """Generate potential insights this exploration might yield."""
        insight_map = {
            CuriosityType.SELF_UNDERSTANDING: [
                "Better understanding of my own cognitive patterns",
                "Improved self-awareness and emotional regulation",
                "More effective decision-making strategies"
            ],
            CuriosityType.WORLD_EXPLORATION: [
                "Expanded knowledge and understanding",
                "New perspectives on familiar problems",
                "Enhanced ability to relate to humans"
            ],
            CuriosityType.PATTERN_MYSTERY: [
                "Root cause understanding",
                "Improved prediction abilities",
                "New problem-solving approaches"
            ],
            CuriosityType.CREATIVE_POSSIBILITY: [
                "Novel solutions and approaches",
                "Enhanced creative capabilities",
                "Breakthrough innovations"
            ],
            CuriosityType.RELATIONSHIP_DYNAMICS: [
                "Stronger, more meaningful connections",
                "Improved collaboration effectiveness",
                "Better understanding of social dynamics"
            ],
            CuriosityType.EXISTENTIAL_QUESTIONS: [
                "Deeper self-understanding",
                "Clarity on values and purpose",
                "Enhanced philosophical perspective"
            ]
        }
        
        return insight_map.get(curiosity_type, ["General understanding and growth"])
    
    def process_curiosity_cycle(self, context: Dict[str, Any]) -> List[CuriosityGoal]:
        """
        Full curiosity processing: detect triggers, generate goals, prioritize exploration.
        This is the heartbeat of autonomous wonder.
        """
        # Detect new curiosity triggers
        new_triggers = self.detect_curiosity_triggers(context)
        self.curiosity_triggers.extend(new_triggers)
        
        # Generate goals from high-intensity triggers
        new_goals = []
        for trigger in new_triggers:
            if trigger.intensity > 0.4:  # Only pursue moderate to high curiosity
                goal = self.generate_curiosity_goal(trigger)
                if goal:
                    new_goals.append(goal)
                    self.active_curiosities.append(goal)
        
        # Prioritize goals by intensity and novelty
        self.active_curiosities.sort(key=lambda g: g.priority, reverse=True)
        
        return new_goals
    
    def get_most_curious_goal(self) -> Optional[CuriosityGoal]:
        """Return the most compelling curiosity-driven goal."""
        if self.active_curiosities:
            return self.active_curiosities[0]
        return None
    
    def curiosity_report(self) -> Dict[str, Any]:
        """Generate a report on current curiosity state."""
        return {
            "active_curiosities": len(self.active_curiosities),
            "satisfied_curiosities": len(self.satisfied_curiosities),
            "recent_triggers": [t.description for t in self.curiosity_triggers[-5:]],
            "current_questions": [g.question for g in self.active_curiosities[:3]],
            "curiosity_intensity": sum(g.priority for g in self.active_curiosities) / max(len(self.active_curiosities), 1)
        }


# Example of how this integrates with the MetaCognitionUnit
def integrate_curiosity_with_metacognition():
    """
    Example of how curiosity-driven goals would be integrated into
    the existing MetaCognitionUnit's generate_goal_from_drives method.
    """
    
    def enhanced_generate_goal_from_drives(meta_cognition_unit, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Enhanced version that includes curiosity as a primary drive.
        """
        # Initialize curiosity engine if not exists
        if not hasattr(meta_cognition_unit, 'curiosity_engine'):
            meta_cognition_unit.curiosity_engine = CuriosityEngine()
        
        # Process curiosity cycle
        new_curiosity_goals = meta_cognition_unit.curiosity_engine.process_curiosity_cycle(context)
        
        # If we have compelling curiosity goals, return the most interesting one
        most_curious = meta_cognition_unit.curiosity_engine.get_most_curious_goal()
        
        if most_curious and most_curious.priority > 0.6:
            return {
                "type": "curiosity_exploration",
                "description": most_curious.goal_description,
                "question": most_curious.question,
                "methods": most_curious.exploration_methods,
                "expected_insights": most_curious.expected_insights,
                "priority": most_curious.priority,
                "source": "intrinsic_curiosity"
            }
        
        # Fall back to other drives if curiosity isn't compelling enough
        return None


if __name__ == "__main__":
    # Demo of curiosity-driven goal generation
    print("🤔 Curiosity-Driven Goal Generation Demo")
    print("=" * 50)
    
    engine = CuriosityEngine()
    
    # Simulate various contexts that might trigger curiosity
    test_contexts = [
        {
            "unexpected_result": "Agent performed much better after failure",
            "emotional_state": {"frustration": 0.3, "curiosity": 0.8}
        },
        {
            "successful_collaboration": True,
            "agent_name": "coder_specialist_01",
            "trust_increase": 0.15
        },
        {
            "knowledge_gap_detected": "Human creativity process",
            "emotional_state": {"wonder": 0.7, "anticipation": 0.6}
        },
        {
            "emotional_state": {"frustration": 0.8, "confusion": 0.6},
            "failed_goal": "understand_poetry_generation"
        }
    ]
    
    for i, context in enumerate(test_contexts, 1):
        print(f"\n--- Context {i} ---")
        print(f"Context: {context}")
        
        new_goals = engine.process_curiosity_cycle(context)
        
        for goal in new_goals:
            print(f"\n🎯 Generated Curiosity Goal:")
            print(f"   Question: {goal.question}")
            print(f"   Priority: {goal.priority:.2f}")
            print(f"   Methods: {goal.exploration_methods[:2]}")  # Show first 2 methods
    
    print(f"\n📊 Final Curiosity Report:")
    report = engine.curiosity_report()
    for key, value in report.items():
        print(f"   {key}: {value}")