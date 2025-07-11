# symbolic_agi/config.py
import os
from datetime import timedelta
from typing import Set, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Constants
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
DB_PATH = os.path.join("data", "symbolic_agi.db")

# File Paths
MUTATION_FILE_PATH = "data/reasoning_mutations.json"
WORKSPACE_DIR = "data/workspace"
DATA_DIR = "data"

# Behavioral & Ethical Tuning
MAX_REASONING_DEPTH = 5
REASONING_TIMEOUT = 30
CONFIDENCE_THRESHOLD = 0.7

# Web Access Configuration
ALLOWED_DOMAINS = {
    # Educational & Reference
    "en.wikipedia.org", "www.wikipedia.org",
    "arxiv.org", "www.arxiv.org",
    "scholar.google.com",
    "plato.stanford.edu",
    "britannica.com", "www.britannica.com",
    
    # News & Current Events  
    "reuters.com", "www.reuters.com",
    "apnews.com", "www.apnews.com",
    "bbc.com", "www.bbc.com", "bbc.co.uk", "www.bbc.co.uk",
    "npr.org", "www.npr.org",
    "theguardian.com", "www.theguardian.com",
    
    # Technical Documentation
    "docs.python.org", "python.org", "www.python.org",
    "developer.mozilla.org", "mdn.io",
    "stackoverflow.com", "www.stackoverflow.com",
    "github.com", "www.github.com",
    "docs.microsoft.com", "learn.microsoft.com",
    
    # Scientific & Academic
    "nature.com", "www.nature.com",
    "sciencedirect.com", "www.sciencedirect.com", 
    "pubmed.ncbi.nlm.nih.gov", "ncbi.nlm.nih.gov",
    "jstor.org", "www.jstor.org",
    
    # Government & Statistics
    "data.gov", "www.data.gov",
    "census.gov", "www.census.gov",
    "who.int", "www.who.int",
    "cdc.gov", "www.cdc.gov",
    "nih.gov", "www.nih.gov",
    
    # Search Engines
    "duckduckgo.com", "www.duckduckgo.com",
    "searx.me", "www.searx.me",
    "startpage.com", "www.startpage.com",
    "www.bing.com", "bing.com",
    "yandex.com", "www.yandex.com",
    "www.wolframalpha.com", "wolframalpha.com",
    
    # Utilities & Archives
    "archive.org", "www.archive.org", "web.archive.org",
    "www.google.com", "google.com",
    "translate.google.com", "maps.googleapis.com",
    
    # Open Data & APIs
    "api.github.com", "raw.githubusercontent.com", "gist.githubusercontent.com",
    "jsonplaceholder.typicode.com", "httpbin.org", "www.httpbin.org",
    "restcountries.com", "www.restcountries.com",
    
    # International Organizations
    "www.wto.org", "wto.org", "www.ilo.org", "ilo.org",
    "www.unicef.org", "unicef.org", "www.unhcr.org", "unhcr.org",
    "www.redcross.org", "redcross.org", "www.msf.org", "msf.org",
}

class AGIConfig(BaseSettings):
    """
    Defines the application's configuration settings.
    Pydantic will automatically load these from a .env file and then environment variables.
    """
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    # General Settings
    name: str = Field(default="SymbolicAGI", description="Name of the AGI instance.")
    scalable_agent_pool_size: int = Field(default=3)
    meta_task_sleep_seconds: int = Field(default=10)
    meta_task_timeout: int = Field(default=60)
    memory_forgetting_threshold: float = Field(default=0.2)
    debate_timeout_seconds: int = Field(default=120)
    energy_regen_amount: int = Field(default=5)
    initial_trust_score: float = Field(default=0.5)
    max_trust_score: float = Field(default=1.0)
    trust_decay_rate: float = Field(default=0.1)
    trust_reward_rate: float = Field(default=0.05)
    
    # Database and Caching
    database_url: str = Field(default="sqlite+aiosqlite:///data/symbolic_agi.db")
    redis_url: str = Field(default="redis://localhost:6379")
    redis_host: str = Field(default="localhost")
    redis_port: int = Field(default=6379)

    # LLM and API Settings
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    default_model: str = Field(default="gpt-4-turbo-preview")

    # Operational Settings
    allowed_domains: Set[str] = Field(default_factory=lambda: ALLOWED_DOMAINS)
    max_concurrent_goals: int = Field(default=3)
    max_reasoning_depth: int = Field(default=5)
    reasoning_timeout: int = Field(default=30)
    confidence_threshold: float = Field(default=0.7)

    # File Paths
    mutation_file_path: str = Field(default="data/reasoning_mutations.json")
    workspace_dir: str = Field(default="data/workspace")
    data_dir: str = Field(default="data")

_config_instance: Optional[AGIConfig] = None

def get_config() -> AGIConfig:
    """Returns a singleton instance of the AGIConfig."""
    global _config_instance
    if _config_instance is None:
        _config_instance = AGIConfig()
    return _config_instance

# Robots.txt checker
from .config_manager import ConfigManager
robots_checker = ConfigManager()