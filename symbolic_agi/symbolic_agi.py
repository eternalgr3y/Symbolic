from .tools.knowledge import Knowledge

class SymbolicAGI:
    # ...existing code...
    async def process_goal_with_plan(self, goal: str, plan: list = None):
        # ...existing code...
        while self.current_step_index < len(self.plan):
            # ...existing code...
            result = await self.agent.execute_step(step, state)

            if "REPLAN" in str(result):
                print(f"⚠️ Replanning detected at step {self.current_step_index + 1}.")
                new_plan = await self.replan(self.current_step_index, results)
                
                # *** LEARNING FROM FAILURE ***
                # After a successful replan, reflect on what was learned.
                learning_summary = await self._reflect_on_replan(
                    original_step=step, 
                    new_steps=new_plan, 
                    context=results
                )
                if learning_summary:
                    result['learning'] = learning_summary # This will make your test pass!
                    # Add the new knowledge to the knowledge base
                    await self.tools.use_tool("knowledge.add_knowledge", {"content": learning_summary})

                self.plan = self.plan[:self.current_step_index] + new_plan + self.plan[self.current_step_index+1:]
                continue # Restart the loop with the new plan
            
            # ...existing code...
        
            # *** LEARNING FROM SUCCESS ***
            if overall_result['status'] == 'success':
                learning_summary = await self._reflect_on_success(goal, results)
                if learning_summary:
                    overall_result['learning'] = learning_summary
                    await self.tools.use_tool("knowledge.add_knowledge", {"content": learning_summary})

            return overall_result

    async def _reflect_on_replan(self, original_step: dict, new_steps: list, context: list) -> str:
        """Analyzes a failed step and the successful recovery to create a new rule."""
        prompt = f"""
        Analyze the following situation to create a new, reusable rule or skill.
        Context: The agent was trying to achieve a goal. The previous successful steps were: {context}
        Failed Step: {original_step}
        Recovery: The agent replaced the failed step with these new successful steps: {new_steps}
        
        Based on this, define a general rule or a parameterized skill. For example: 'When the task is X and you see Y, do Z instead.' or define a new skill in JSON format.
        Your output should be only the new rule or skill definition.
        """
        print("🤔 Reflecting on failure to learn...")
        learning = await self.llm.inference(prompt)
        return learning

    async def _reflect_on_success(self, goal: str, results: list) -> str:
        """Analyzes a successful execution trace to create a new, more abstract skill."""
        prompt = f"""
        The agent successfully completed the goal '{goal}' with the following steps: {results}.
        
        Can this sequence of steps be generalized into a new, reusable, parameterized skill?
        If yes, define the skill in a structured JSON format with a 'skill_name', 'description', 'steps', and 'parameters'.
        If no, simply respond with 'No generalization possible.'.
        """
        print("🤔 Reflecting on success to learn...")
        learning = await self.llm.inference(prompt)
        if "No generalization possible." in learning:
            return None
        return learning