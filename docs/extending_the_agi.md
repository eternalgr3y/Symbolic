# Extending SymbolicAGI

This guide provides practical instructions for extending the AGI's capabilities. The system is designed to be modular, making it straightforward to add new tools, agents, and even cognitive functions.

## How to Add a New Tool

Tools are the AGI's primitive actions for interacting with the outside world (e.g., file system, web).

1.  **Implement the Method:**
    -   Open `symbolic_agi/tool_plugin.py`.
    -   Add a new `async` method to the `ToolPlugin` class.
    -   The method should accept its parameters with explicit type hints.
    -   It MUST return a dictionary with a `"status"` key (`"success"` or `"failure"`) and a `"description"` key explaining the outcome. It can also return other data to be added to the workspace.

    **Example:**
    ```python
    # In symbolic_agi/tool_plugin.py
    async def get_stock_price(self, ticker: str, **kwargs: Any) -> Dict[str, Any]:
        """Fetches the current stock price for a given ticker symbol."""
        try:
            # (Your logic to call a stock API)
            price = 123.45 
            return {"status": "success", "description": f"Price for {ticker} is {price}", "stock_price": price}
        except Exception as e:
            return {"status": "failure", "description": str(e)}
    ```

2.  **Register the Tool:**
    -   Open `symbolic_agi/skill_manager.py`.
    -   Find the `_get_innate_actions` method.
    -   Add a new entry to the dictionary it returns. The key is the action name, and the value is a string describing its parameters and assigning it to the `orchestrator`.

    **Example:**
    ```python
    # In symbolic_agi/skill_manager.py
    def _get_innate_actions(self) -> Dict[str, str]:
        return {
            # ... other actions
            "get_stock_price": 'parameters: {"ticker": "..."}, assigned_persona: "orchestrator"',
        }
    ```
The `Planner` will automatically pick up the new tool on the next cycle and can incorporate it into its plans.

## How to Add a New Agent Persona

Personas are for specialized, multi-step reasoning tasks that are too complex for a single tool (e.g., writing code, performing detailed analysis).

1.  **Define the Persona's Skill:**
    -   Open `symbolic_agi/agent.py`.
    -   Add a new `async def skill_...` method to the `Agent` class. This method will contain the logic for the new persona, including the LLM prompt that defines its behavior.

2.  **Register the Skill:**
    -   In `symbolic_agi/agent.py`, find the `_initialize_skills` method.
    -   Add an `elif self.persona == 'your_new_persona':` block that maps a message type to your new skill method.

    **Example:**
    ```python
    # In symbolic_agi/agent.py
    class Agent:
        # ...
        def _initialize_skills(self) -> Dict[str, Any]:
            if self.persona == 'coder':
                return {"write_code": self.skill_write_code}
            # ... other personas
            elif self.persona == 'db_expert':
                return {"optimize_sql_query": self.skill_optimize_sql}

        async def skill_optimize_sql(self, params: Dict[str, Any]) -> Dict[str, Any]:
            # Your logic and LLM prompt for optimizing SQL
            ...
    ```

3.  **Launch the Agent:**
    -   Open `scripts/run_agi.py`.
    -   In the `main` function, add your new persona to the `specialist_definitions` list.

    **Example:**
    ```python
    # In scripts/run_agi.py
    specialist_definitions = [
        {"name": f"{agi.name}_Coder_0", "persona": "coder"},
        {"name": f"{agi.name}_Research_0", "persona": "research"},
        {"name": f"{agi.name}_QA_0", "persona": "qa"},
        {"name": f"{agi.name}_DBExpert_0", "persona": "db_expert"}, # New agent
    ]
    ```
Your new specialist agent will now be available for the `Planner` to delegate tasks to.