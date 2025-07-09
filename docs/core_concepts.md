### FILE: `New folder/symbolic_agi/core_concepts.md`
```markdown
# Core Concepts

This document explains the philosophy and design principles behind some of SymbolicAGI's most important features.

## 1. The Meta-Cognitive Loop

**Concept:** Meta-cognition is "thinking about thinking." In SymbolicAGI, this is implemented via the `MetaCognitionUnit`, which runs a continuous background loop of self-improvement tasks.

**Why it matters:** A system that only executes user-defined goals is merely a sophisticated task-runner. A system that can generate its own goals, reflect on its own performance, and actively seek to improve its own cognitive processes is exhibiting a foundational property of intelligence. This loop is what allows for emergent, autonomous behavior and prevents the AGI from being purely passive.

**Implementation:** The `run_background_tasks` method in `meta_cognition.py` randomly selects from a weighted list of methods (e.g., `daydream`, `prune_mutations`, `generate_goal_from_drives`) and executes them periodically.

## 2. Self-Mutation

**Concept:** The AGI can permanently alter its own core reasoning process by adding new rules to its "mutation stack."

**Why it matters:** This is a powerful and direct form of learning. When a plan fails due to a logical error (e.g., using a tool with the wrong parameters), the `RecursiveIntrospector` performs a root-cause analysis and generates a new, generalized rule. This rule is saved to `data/reasoning_mutations.json` and injected into the system prompt of all future planning requests. The AGI doesn't just recover from an error; it learns a permanent lesson that prevents it from making the same *class* of error again.

**Safety:** This capability is intentionally separated from direct code modification. The mutations only affect the LLM's reasoning prompt, not the underlying Python logic. This provides a safe sandbox for experimenting with self-improvement.

## 3. Interactive Web Navigation

**Concept:** The AGI uses the Playwright library to control a real browser instance. A specialized `browser` agent analyzes the state of a webpage and decides on the next action (click, fill, etc.), which the `orchestrator` then executes.

**Why it matters:** This moves the AGI from being a passive scraper of static HTML to an active agent in the dynamic web. It can log into services, interact with complex JavaScript applications, and perform tasks that require a sequence of interactions, dramatically expanding its capabilities in the digital world.

## 4. Trust-Based Agent Economy

**Concept:** Every specialist agent has a `trust_score` that is adjusted based on its performance. The orchestrator uses this score to select the most reliable agent for a given task.

**Why it matters:** This moves the system from simple delegation to a dynamic, self-organizing team. It creates an internal "economy" where reliability is rewarded with more responsibility. This is a foundational step towards more advanced agent management, such as automatically retiring underperforming agents or provisioning new ones when trust in a certain persona pool is low.

## 5. Skill Acquisition and Versioning

**Concept:** The AGI can abstract a successful sequence of actions into a new, reusable "skill." These skills are versioned, and the AGI can autonomously review and improve them over time.

**Why it matters:** This is a powerful form of long-term memory and learning. Instead of re-planning common tasks from scratch, the AGI can build a library of reliable, high-level competencies. Versioning prevents a flawed "improvement" from overwriting a working skill, ensuring stability.

## 6. The Ethical Governor

**Concept:** The `SymbolicEvaluator` is a non-negotiable gatekeeper for all plans and self-modification attempts.

**Why it matters:** As the AGI's capabilities grow, ensuring its actions remain aligned with a core set of values is the most important design constraint. Before any plan is executed, the evaluator simulates its likely outcomes and scores it against the AGI's value system (e.g., `harm_avoidance`, `truthfulness`). If any value scores below a configured threshold, the plan is rejected. This provides a powerful, automated safety layer that is fundamental to the project's design.