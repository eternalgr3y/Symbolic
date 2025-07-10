# symbolic_agi/micro_world.py

import asyncio
import inspect
import json
import logging
import os
import random
from typing import Any, Callable, Dict, List, Optional, cast

from . import config
from .api_client import monitored_chat_completion


class MicroWorld:
    """A rich, multi-agent, multi-room simulated world with persistent state."""

    room_map: Dict[str, Dict[str, Any]]
    state: Dict[str, List[Any]]
    state_file_path: str

    def __init__(self: "MicroWorld"):
        self.room_map = {
            "hallway": {
                "desc": "A main hallway with doors to room1 and room2.",
                "exits": ["room1", "room2"],
            },
            "room1": {
                "desc": "A small room with a locked chest and sticks.",
                "exits": ["hallway"],
            },
            "room2": {
                "desc": "A stone room with a heavy rock and a notice board.",
                "exits": ["hallway"],
            },
        }
        self.state_file_path = os.path.join(
            config.WORKSPACE_DIR, "microworld_state.json"
        )
        self.state = self._load_state()

    def _get_default_state(self) -> Dict[str, List[Any]]:
        """Returns the default state for a new world."""
        return {
            "agents": [
                {"name": "SymbolicAGI", "location": "hallway", "inventory": []},
                {"name": "Alice", "location": "room1", "inventory": ["Stick"]},
                {"name": "Bob", "location": "room2", "inventory": ["Rock"]},
                {"name": "User", "location": "hallway", "inventory": []},
            ],
            "objects": [
                {
                    "name": "Chest",
                    "location": "room1",
                    "state": "locked",
                    "type": "chest",  # Add this line
                    "description": "A heavy wooden chest with a lock.",
                },
                {"name": "Rock", "location": "room2", "description": "A rough gray rock."},
                {
                    "name": "Stick",
                    "location": "room1",
                    "description": "A sturdy wooden stick.",
                },
                {"name": "Key", "location": "room2", "description": "A small iron key."},
                {
                    "name": "NoticeBoard",
                    "location": "room2",
                    "description": "A faded notice board covered with old papers.",
                },
            ],
            "doors": [
                {"from": "hallway", "to": "room1", "locked": False},
                {"from": "hallway", "to": "room2", "locked": False},
            ],
            "rooms": list(self.room_map.keys()),
            "events": [],
        }

    def _load_state(self) -> Dict[str, List[Any]]:
        """Loads the world state from a JSON file, or creates a default state."""
        if os.path.exists(self.state_file_path):
            try:
                with open(self.state_file_path, "r", encoding="utf-8") as f:
                    logging.info(
                        "Loading persistent MicroWorld state from %s",
                        self.state_file_path,
                    )
                    return cast(Dict[str, List[Any]], json.load(f))
            except (json.JSONDecodeError, TypeError):
                logging.error("Could not load MicroWorld state, creating a new one.")

        logging.info("No persistent MicroWorld state found, creating default state.")
        default_state = self._get_default_state()
        self._save_state(default_state)
        return default_state

    def _save_state(self, state_data: Dict[str, Any]) -> None:
        """Saves the current world state to a JSON file."""
        try:
            os.makedirs(os.path.dirname(self.state_file_path), exist_ok=True)
            with open(self.state_file_path, "w", encoding="utf-8") as f:
                json.dump(state_data, f, indent=4)
        except Exception as e:
            logging.error("Failed to save MicroWorld state: %s", e, exc_info=True)

    def save_state(self) -> None:
        """Public method to save the current world state."""
        self._save_state(self.state)

    def add_agent(
        self: "MicroWorld",
        name: str,
        location: str = "hallway",
        inventory: Optional[List[str]] = None,
    ) -> None:
        """Adds a new agent to the world."""
        if inventory is None:
            inventory = []
        self.state["agents"].append(
            {"name": name, "location": location, "inventory": inventory}
        )
        self._save_state(self.state)

    def get_agent(self: "MicroWorld", name: str) -> Optional[Dict[str, Any]]:
        """Retrieves an agent by name."""
        return next(
            (agent for agent in self.state["agents"] if agent["name"] == name), None
        )

    def get_object(self: "MicroWorld", object_name: str) -> Optional[Dict[str, Any]]:
        """Retrieves an object by name."""
        return next(
            (obj for obj in self.state["objects"] if obj["name"] == object_name), None
        )

    def room_agents(self: "MicroWorld", room: str) -> List[Dict[str, Any]]:
        """Returns agents in a specific room."""
        return [a for a in self.state["agents"] if a["location"] == room]

    def room_objects(self: "MicroWorld", room: str) -> List[Dict[str, Any]]:
        """Returns objects in a specific room."""
        return [o for o in self.state["objects"] if o["location"] == room]

    async def tick(self: "MicroWorld") -> None:
        """Simulate time passing in the world (random agent wandering)."""
        state_changed = False
        try:
            if random.random() < 0.1:
                agent = random.choice(self.state["agents"])
                current_location_data = self.room_map.get(agent["location"])
                if current_location_data:
                    available_exits = current_location_data.get("exits")
                    if available_exits:
                        new_location = random.choice(available_exits)
                        is_locked = any(
                            d
                            for d in self.state["doors"]
                            if d["from"] == agent["location"]
                            and d["to"] == new_location
                            and d["locked"]
                        )
                        if not is_locked:
                            agent["location"] = new_location
                            self.state["events"].append(
                                {
                                    "event_type": "wander",
                                    "agent": agent["name"],
                                    "to": new_location,
                                }
                            )
                            state_changed = True
                        else:
                            logging.debug(
                                "Agent %s tried to wander to %s but the door was locked.",
                                agent["name"],
                                new_location,
                            )

        except Exception as e:
            logging.error("World tick error: %s", e)
        finally:
            if state_changed:
                self._save_state(self.state)

    async def perform_action(
        self: "MicroWorld", action: str, **kwargs: Any
    ) -> Dict[str, Any]:
        """
        Executes a world action, validates parameters, and saves the state on success.
        """
        try:
            method_to_call: Optional[Callable[..., Any]] = getattr(
                self, f"_action_{action}", None
            )

            if not method_to_call:
                return {
                    "status": "failure",
                    "description": f"World action '{action}' not found.",
                }

            sig = inspect.signature(method_to_call)
            required_params = {
                p.name
                for p in sig.parameters.values()
                if p.default is inspect.Parameter.empty
                and p.name not in ["self", "kwargs"]
            }
            provided_params = set(kwargs.keys())

            if not required_params.issubset(provided_params):
                missing = required_params - provided_params
                error_msg = (
                    f"World action '{action}' missing required parameters: "
                    f"{', '.join(missing)}."
                )
                logging.error(error_msg)
                return {"status": "failure", "description": error_msg}

            result: Any
            if asyncio.iscoroutinefunction(method_to_call):
                result = await method_to_call(**kwargs)
            else:
                result = method_to_call(**kwargs)

            self.state["events"].append(
                {"action": action, "params": kwargs, "result": result}
            )
            logging.info("WORLD ACTION: %s with %s -> %s", action, kwargs, result)

            if result.get("status") == "success":
                self._save_state(self.state)

            return cast(Dict[str, Any], result)
        except Exception as e:
            err_msg = f"Error performing action '{action}': {type(e).__name__}: {e}"
            logging.error(err_msg, exc_info=True)
            return {"status": "failure", "description": err_msg}

    # ========== Actions ==========

    def _action_move(
        self: "MicroWorld", agent_name: str, new_location: str
    ) -> Dict[str, Any]:
        """Moves an agent to a new location if possible."""
        agent = self.get_agent(agent_name)
        if not agent:
            return {"status": "failure", "description": f"Agent '{agent_name}' not found."}

        current_room_exits = self.room_map.get(agent["location"], {}).get("exits", [])
        if new_location not in current_room_exits:
            return {
                "status": "failure",
                "description": (
                    f"Cannot move from {agent['location']} to {new_location}. "
                    "No direct exit."
                ),
            }

        for door in self.state["doors"]:
            if (
                door["from"] == agent["location"]
                and door["to"] == new_location
                and door["locked"]
            ):
                return {
                    "status": "failure",
                    "description": f"The door to {new_location} is locked.",
                }

        agent["location"] = new_location
        return {
            "status": "success",
            "description": f"{agent_name} moves to {new_location}.",
        }

    def _action_read(
        self: "MicroWorld", object_name: str, agent_name: str = "SymbolicAGI"
    ) -> Dict[str, Any]:
        """Allows an agent to read an object's description."""
        agent = self.get_agent(agent_name)
        obj = self.get_object(object_name)
        if not agent:
            return {"status": "failure", "description": f"Agent '{agent_name}' not found."}
        if not obj:
            return {"status": "failure", "description": f"Object '{object_name}' not found."}
        if agent["location"] != obj.get("location"):
            return {
                "status": "failure",
                "description": f"{agent_name} is not in the same location as {object_name}.",
            }
        desc = obj.get("description", f"You see a {object_name}.")
        details = f"State: {obj.get('state', 'normal')}" if "state" in obj else ""
        return {
            "status": "success",
            "description": f"{agent_name} reads {object_name}: {desc} {details}".strip(),
        }

    def _action_pickup(
        self: "MicroWorld", agent_name: str, object_name: str
    ) -> Dict[str, Any]:
        """Allows an agent to pick up an object."""
        agent = self.get_agent(agent_name)
        obj = self.get_object(object_name)
        if not agent or not obj:
            return {"status": "failure", "description": "Agent or object not found."}
        if agent["location"] != obj.get("location"):
            return {
                "status": "failure",
                "description": f"{object_name} is not in the same room as {agent_name}.",
            }

        if obj.get("state") == "fixed":
            return {
                "status": "failure",
                "description": f"{object_name} cannot be picked up.",
            }

        agent["inventory"].append(object_name)
        obj["location"] = "inventory"
        return {
            "status": "success",
            "description": f"{agent_name} picked up {object_name}.",
        }

    def _action_drop(
        self: "MicroWorld", agent_name: str, object_name: str
    ) -> Dict[str, Any]:
        """Allows an agent to drop an item from inventory."""
        agent = self.get_agent(agent_name)
        obj = self.get_object(object_name)
        if not agent or not obj:
            return {"status": "failure", "description": "Agent or object not found."}
        if object_name not in agent["inventory"]:
            return {
                "status": "failure",
                "description": f"{agent_name} does not have {object_name} in inventory.",
            }
        agent["inventory"].remove(object_name)
        obj["location"] = agent["location"]
        return {
            "status": "success",
            "description": f"{agent_name} dropped {object_name} in {agent['location']}.",
        }

    def _action_open(
        self: "MicroWorld", agent_name: str, object_name: str
    ) -> Dict[str, Any]:
        """Allows an agent to open an object (e.g., a chest)."""
        agent = self.get_agent(agent_name)
        obj = self.get_object(object_name)
        if not agent or not obj:
            return {"status": "failure", "description": "Agent or object not found."}
        
        # Debug logging
        logging.info(f"DEBUG: Agent {agent_name} location: {agent.get('location')}")
        logging.info(f"DEBUG: Object {object_name} location: {obj.get('location')}")
        
        if agent["location"] != obj.get("location"):
            return {
                "status": "failure",
                "description": f"{agent_name} is not in the same location as {object_name}. Agent in {agent['location']}, object in {obj.get('location')}.",
            }
    
        # Handle the Chest specifically
        if object_name == "Chest":
            if obj.get("state") == "locked":
                if "Key" in agent["inventory"]:
                    obj["state"] = "unlocked"
                    return {
                        "status": "success",
                        "description": "Unlocked the Chest with the Key!",
                    }
                else:
                    return {
                        "status": "failure",
                        "description": "The Chest is locked. You need a Key.",
                    }
            elif obj.get("state") == "unlocked":
                obj["state"] = "open"
                return {
                    "status": "success",
                    "description": "Opened the Chest.",
                }
            elif obj.get("state") == "open":
                return {"status": "success", "description": "The Chest is already open."}
            else:
                return {
                    "status": "failure",
                    "description": f"The Chest state is {obj.get('state')} and cannot be opened.",
                }

        return {
            "status": "failure",
            "description": f"{object_name} cannot be opened or is already open.",
        }

    async def _action_ask(
        self: "MicroWorld", asking_agent: str, target_agent: str, question: str
    ) -> Dict[str, Any]:
        """Allows an agent to ask another agent (or user) a question."""
        agent = self.get_agent(asking_agent)
        target = self.get_agent(target_agent)
        if not agent or not target:
            return {
                "status": "failure",
                "description": "Asking agent or target agent not found.",
            }
        if agent["location"] != target["location"]:
            return {
                "status": "failure",
                "description": f"{target_agent} is not in the same location as {asking_agent}.",
            }

        if target_agent.lower() == "user":
            return {
                "status": "success",
                "response_text": f"{asking_agent} asked you: {question}",
            }

        try:
            prompt = (
                f"{target_agent} is being asked a question by {asking_agent}.\n"
                f"World state: {json.dumps(self.state)}\n"
                f"Question: {question}\n"
                f"Answer in character as {target_agent} and keep it concise:"
            )
            resp = await monitored_chat_completion(
                role="tool_action", messages=[{"role": "system", "content": prompt}]
            )
            answer = (
                resp.choices[0].message.content.strip()
                if resp.choices and resp.choices[0].message.content
                else "..."
            )
        except Exception as e:
            logging.error("LLM for _action_ask error: %s", e)
            answer = (
                f"{target_agent} says: I don't know yet, but I'll try to help next time!"
            )
        return {
            "status": "success",
            "response_text": f"{asking_agent} asked {target_agent}: {question}\n{answer}",
        }

    def _action_look(self: "MicroWorld", agent_name: str) -> Dict[str, Any]:
        """Allows an agent to observe its current surroundings."""
        agent = self.get_agent(agent_name)
        if not agent:
            return {"status": "failure", "description": f"Agent '{agent_name}' not found."}

        location = agent["location"]
        room = self.room_map.get(location)
        if not room:
            return {"status": "failure", "description": f"Room '{location}' not found in map."}

        objects_here = [obj["name"] for obj in self.room_objects(location)]
        agents_here = [
            a["name"] for a in self.room_agents(location) if a["name"] != agent_name
        ]

        return {
            "status": "success",
            "description": (
                f"You are in {location}. {room['desc']} You see: "
                f"{', '.join(objects_here) or 'nothing'}. "
                f"Others here: {', '.join(agents_here) or 'no one'}."
            ),
        }

    def _action_give(
        self: "MicroWorld", giving_agent: str, item_name: str, receiving_agent: str
    ) -> Dict[str, Any]:
        """Allows an agent to give an item to another agent."""
        agent = self.get_agent(giving_agent)
        recipient = self.get_agent(receiving_agent)
        obj = self.get_object(item_name)

        if not agent or not recipient or not obj:
            return {
                "status": "failure",
                "description": "Giving agent, receiving agent, or item not found.",
            }

        if agent["location"] != recipient["location"]:
            return {"status": "failure", "description": "Recipient not in the same room."}

        if item_name not in agent["inventory"]:
            return {
                "status": "failure",
                "description": f"{giving_agent} does not have {item_name} in inventory.",
            }

        agent["inventory"].remove(item_name)
        recipient["inventory"].append(item_name)
        obj["location"] = "inventory"

        return {
            "status": "success",
            "description": f"{giving_agent} gave {item_name} to {receiving_agent}.",
        }

    def _action_combine(
        self: "MicroWorld", agent_name: str, item1_name: str, item2_name: str
    ) -> Dict[str, Any]:
        """Allows an agent to combine two items."""
        agent = self.get_agent(agent_name)
        if not agent:
            return {"status": "failure", "description": "Agent not found."}

        if item1_name not in agent["inventory"] or item2_name not in agent["inventory"]:
            return {
                "status": "failure",
                "description": "Agent does not have both items to combine.",
            }

        if {item1_name, item2_name} == {"Stick", "Rock"}:
            agent["inventory"].remove("Stick")
            agent["inventory"].remove("Rock")
            agent["inventory"].append("Hammer")
            for obj_name in ["Stick", "Rock"]:
                obj = self.get_object(obj_name)
                if obj:
                    self.state["objects"].remove(obj)
            self.state["objects"].append(
                {
                    "name": "Hammer",
                    "location": "inventory",
                    "description": "A crude hammer made from a stick and a rock.",
                }
            )
            return {"status": "success", "description": f"{agent_name} crafted a Hammer."}

        return {"status": "failure", "description": "These items cannot be combined."}

    def _action_use(
        self: "MicroWorld", agent_name: str, item_name: str, target_name: str
    ) -> Dict[str, Any]:
        """Allows an agent to use an item on a target."""
        agent = self.get_agent(agent_name)
        if not agent:
            return {"status": "failure", "description": "Agent not found."}
        if item_name not in agent["inventory"]:
            return {
                "status": "failure",
                "description": f"Agent does not have a {item_name} in inventory.",
            }

        target = self.get_object(target_name)
        if not target:
            return {
                "status": "failure",
                "description": f"Target object {target_name} not found.",
            }

        if target.get("location") != agent["location"]:
            return {
                "status": "failure",
                "description": f"The {target_name} is not in the same location as {agent_name}.",
            }

        if (
            item_name == "Hammer"
            and target_name == "Chest"
            and target.get("state") == "locked"
        ):
            target["state"] = "unlocked"
            return {
                "status": "success",
                "description": f"{agent_name} used the Hammer to break the lock on the Chest.",
            }

        return {
            "status": "failure",
            "description": f"The {item_name} has no effect on the {target_name}.",
        }