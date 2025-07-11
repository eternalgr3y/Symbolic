import json
import logging
import os
from typing import Any, Dict, List, Optional

class MicroWorld:
    """Simulates a simple environment for the AGI to interact with."""
    
    def __init__(self, workspace_dir: str):
        self.workspace_dir = workspace_dir
        self.entities: Dict[str, Dict[str, Any]] = {}
        self.locations: Dict[str, Dict[str, Any]] = {
            "hallway": {"description": "A long hallway with doors on both sides"},
            "office": {"description": "A small office with a desk and computer"},
            "library": {"description": "A quiet library filled with books"},
            "garden": {"description": "A peaceful garden with various plants"}
        }
        self.current_location = "hallway"
        self._initialize_world()

    def _initialize_world(self) -> None:
        """Initialize the micro world with default entities."""
        os.makedirs(self.workspace_dir, exist_ok=True)
        
        # Add some default entities
        self.entities["notebook"] = {
            "type": "object",
            "location": "office",
            "description": "A spiral notebook for taking notes",
            "properties": {"pages": 100, "used_pages": 0}
        }
        
        self.entities["computer"] = {
            "type": "object",
            "location": "office",
            "description": "A desktop computer",
            "properties": {"powered_on": False}
        }
        
        self.entities["book_python"] = {
            "type": "object",
            "location": "library",
            "description": "Python Programming: An Introduction",
            "properties": {"pages": 500, "topics": ["basics", "data structures", "algorithms"]}
        }

    def move_to(self, location: str) -> Dict[str, Any]:
        """Move to a different location."""
        if location not in self.locations:
            return {
                "success": False,
                "error": f"Unknown location: {location}"
            }
            
        self.current_location = location
        
        # Get entities at this location
        local_entities = [
            name for name, entity in self.entities.items()
            if entity.get("location") == location
        ]
        
        return {
            "success": True,
            "location": location,
            "description": self.locations[location]["description"],
            "entities": local_entities
        }

    def examine(self, entity_name: str) -> Dict[str, Any]:
        """Examine an entity."""
        if entity_name not in self.entities:
            return {
                "success": False,
                "error": f"Unknown entity: {entity_name}"
            }
            
        entity = self.entities[entity_name]
        
        if entity.get("location") != self.current_location:
            return {
                "success": False,
                "error": f"{entity_name} is not at your current location"
            }
            
        return {
            "success": True,
            "entity": entity_name,
            "description": entity.get("description", ""),
            "type": entity.get("type", "unknown"),
            "properties": entity.get("properties", {})
        }

    def interact(self, entity_name: str, action: str, **kwargs) -> Dict[str, Any]:
        """Interact with an entity."""
        if entity_name not in self.entities:
            return {
                "success": False,
                "error": f"Unknown entity: {entity_name}"
            }
            
        entity = self.entities[entity_name]
        
        if entity.get("location") != self.current_location:
            return {
                "success": False,
                "error": f"{entity_name} is not at your current location"
            }
            
        # Handle different interactions
        if entity_name == "notebook" and action == "write":
            content = kwargs.get("content", "")
            if entity["properties"]["used_pages"] < entity["properties"]["pages"]:
                entity["properties"]["used_pages"] += 1
                
                # Save to file
                notebook_path = os.path.join(self.workspace_dir, "notebook.txt")
                with open(notebook_path, "a") as f:
                    f.write(f"\nPage {entity['properties']['used_pages']}: {content}\n")
                    
                return {
                    "success": True,
                    "message": f"Wrote to notebook: {content}"
                }
            else:
                return {
                    "success": False,
                    "error": "Notebook is full"
                }
                
        elif entity_name == "computer" and action == "power":
            entity["properties"]["powered_on"] = not entity["properties"]["powered_on"]
            state = "on" if entity["properties"]["powered_on"] else "off"
            return {
                "success": True,
                "message": f"Computer is now {state}"
            }
            
        return {
            "success": False,
            "error": f"Cannot perform action '{action}' on {entity_name}"
        }

    def get_state(self) -> Dict[str, Any]:
        """Get current world state."""
        return {
            "current_location": self.current_location,
            "locations": list(self.locations.keys()),
            "all_entities": list(self.entities.keys()),
            "local_entities": [
                name for name, entity in self.entities.items()
                if entity.get("location") == self.current_location
            ]
        }