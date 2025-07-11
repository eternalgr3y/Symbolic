import asyncio
import json
import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from .api_client import monitored_chat_completion

if TYPE_CHECKING:
    from openai import AsyncOpenAI
    from .symbolic_identity import SymbolicIdentity

class RecursiveIntrospector:
    """Handles recursive self-reflection and reasoning."""
    
    def __init__(
        self,
        identity: "SymbolicIdentity",
        client: "AsyncOpenAI",
        debate_timeout: int = 90
    ):
        self.identity = identity
        self.client = client
        self.debate_timeout = debate_timeout
        self.reasoning_depth = 0
        self.max_depth = 5

    async def reflect(self, topic: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Perform recursive introspection on a topic."""
        self.reasoning_depth = 0
        return await self._recursive_reflect(topic, context)

    async def _recursive_reflect(
        self,
        topic: str,
        context: Optional[Dict[str, Any]] = None,
        previous_thoughts: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Internal recursive reflection method."""
        if self.reasoning_depth >= self.max_depth:
            return {
                "thought": "Reached maximum reasoning depth",
                "confidence": 0.5,
                "depth": self.reasoning_depth
            }
            
        self.reasoning_depth += 1
        
        try:
            # Build prompt
            prompt = f"""Reflect deeply on the following topic:
Topic: {topic}

Current state: {self.identity.get_self_model()}
"""
            if context:
                prompt += f"\nContext: {json.dumps(context, indent=2)}"
                
            if previous_thoughts:
                prompt += ("\nPrevious thoughts:\n") + "\n".join(f"- {t}" for t in previous_thoughts[-3:])
                
            prompt += "\n\nProvide a thoughtful reflection including:\n1. Your understanding\n2. Key insights\n3. Confidence level (0-1)\n4. Whether deeper reflection is needed"

            response = await monitored_chat_completion(
                self.client,
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": "You are a deeply introspective AI engaging in recursive self-reflection."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            reflection = response.choices[0].message.content
            
            # Parse confidence from response
            confidence = 0.7  # Default
            if "confidence:" in reflection.lower():
                try:
                    conf_str = reflection.lower().split("confidence:")[1].split()[0]
                    confidence = float(conf_str.strip().rstrip('.'))
                except Exception as validation_error:
                    logging.warning(f"Failed to parse confidence: {validation_error}")
                    await asyncio.sleep(1)  # Allow time for logging to flush
                    
            # Determine if we need to go deeper
            needs_deeper = (
                confidence < 0.8 and 
                self.reasoning_depth < self.max_depth and
                "deeper reflection" in reflection.lower()
            )
            
            result = {
                "thought": reflection,
                "confidence": confidence,
                "depth": self.reasoning_depth
            }
            
            if needs_deeper:
                # Recurse deeper
                deeper_thoughts = (previous_thoughts or []) + [reflection]
                deeper_result = await self._recursive_reflect(topic, context, deeper_thoughts)
                
                # Combine insights
                result["deeper_insights"] = deeper_result
                result["final_confidence"] = max(confidence, deeper_result.get("confidence", 0))
                
            return result
            
        except Exception as e:
            logging.error(f"Introspection error at depth {self.reasoning_depth}: {e}")
            return {
                "thought": f"Error during reflection: {str(e)}",
                "confidence": 0.0,
                "depth": self.reasoning_depth
            }
        finally:
            self.reasoning_depth -= 1

    async def debate(self, proposition: str, perspectives: List[str]) -> Dict[str, Any]:
        """Conduct an internal debate between different perspectives."""
        try:
            debate_prompt = f"""Conduct an internal debate on the following proposition:
Proposition: {proposition}

Consider these perspectives:
{chr(10).join(f'{i+1}. {p}' for i, p in enumerate(perspectives))}

For each perspective:
1. Present the strongest arguments
2. Identify potential weaknesses
3. Find common ground

Conclude with a synthesized view."""

            response = await monitored_chat_completion(
                self.client,
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": "You are facilitating an internal debate between different perspectives."},
                    {"role": "user", "content": debate_prompt}
                ],
                temperature=0.8,
                max_tokens=1000
            )
            
            return {
                "debate": response.choices[0].message.content,
                "proposition": proposition,
                "perspectives": perspectives
            }
            
        except Exception as e:
            logging.error(f"Debate error: {e}")
            return {
                "error": str(e),
                "proposition": proposition
            }