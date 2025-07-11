import logging
from typing import Dict, Set
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

class ConfigManager:
    """Manages configuration and robots.txt compliance."""
    
    def __init__(self):
        self.robots_cache: Dict[str, RobotFileParser] = {}
        self.user_agent = "SymbolicAGI/1.0"

    def can_fetch(self, url: str) -> bool:
        """Check if URL can be fetched according to robots.txt."""
        try:
            parsed = urlparse(url)
            base_url = f"{parsed.scheme}://{parsed.netloc}"
            
            # Check cache
            if base_url not in self.robots_cache:
                # Create parser
                rp = RobotFileParser()
                rp.set_url(f"{base_url}/robots.txt")
                
                try:
                    rp.read()
                    self.robots_cache[base_url] = rp
                except Exception:
                    # If we can't read robots.txt, assume we can fetch
                    logging.debug(f"Could not read robots.txt for {base_url}")
                    return True
                    
            # Check if allowed
            return self.robots_cache[base_url].can_fetch(self.user_agent, url)
            
        except Exception as e:
            logging.error(f"Error checking robots.txt: {e}")
            # Be conservative - don't fetch if there's an error
            return False

    def clear_cache(self) -> None:
        """Clear the robots.txt cache."""
        self.robots_cache.clear()