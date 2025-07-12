# symbolic_agi/config.py

import os
from datetime import timedelta
from typing import Set

# --- Model & Embedding Configuration ---
FAST_MODEL = "gpt-3.5-turbo"
HIGH_STAKES_MODEL = "gpt-4-turbo"
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536

# --- Redis & Database Configuration ---
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
DB_PATH = os.path.join("data", "symbolic_agi.db")

# --- File Paths ---
MUTATION_FILE_PATH = "data/reasoning_mutations.json"
WORKSPACE_DIR = "data/workspace"

# --- Behavioral & Ethical Tuning ---
PLAN_EVALUATION_THRESHOLD = 0.7
SELF_MODIFICATION_THRESHOLD = 0.8
DEBATE_TIMEOUT_SECONDS = 90
ENERGY_REGEN_AMOUNT = 5.0
INITIAL_TRUST_SCORE = 0.5
MAX_TRUST_SCORE = 1.0
TRUST_DECAY_RATE = 0.1  # Amount of trust lost on failure
TRUST_REWARD_RATE = 0.05  # Amount of trust gained on success
TRUST_REHEAL_RATE = 0.01  # Slow healing rate towards neutral (0.5)
TRUST_REHEAL_INTERVAL_HOURS = 24  # How often to run the healing job
ALLOWED_DOMAINS: Set[str] = {
    "api.openai.com",
    "duckduckgo.com",
    "pypi.org",
    "files.pythonhosted.org",
    "github.com",
    "the-internet.herokuapp.com",
}

# --- Meta-Task Frequencies (seconds) ---
META_TASK_SLEEP_SECONDS = 10
META_TASK_TIMEOUT = 60

# --- Time-based Thresholds ---
MEMORY_COMPRESSION_WINDOW = timedelta(days=1)
SOCIAL_INTERACTION_THRESHOLD = timedelta(hours=6)
MEMORY_FORGETTING_THRESHOLD = 0.2

import urllib.robotparser
import urllib.parse
from typing import Dict, Set, Optional
import asyncio
import logging
import time

class RobotsChecker:
    """Checks and caches robots.txt compliance for domains."""
    
    def __init__(self):
        self._robots_cache: Dict[str, urllib.robotparser.RobotFileParser] = {}
        self._cache_timestamps: Dict[str, float] = {}
        self._cache_duration = 3600  # 1 hour cache
        self._user_agent = "SymbolicAGI/1.0 (+https://github.com/yourproject/symbolic_agi)"
    
    async def can_fetch(self, url: str) -> bool:
        """Check if we can fetch the given URL according to robots.txt"""
        try:
            parsed_url = urllib.parse.urlparse(url)
            domain = parsed_url.netloc.lower()
            
            # Get robots.txt for this domain
            robots_parser = await self._get_robots_parser(domain)
            
            if robots_parser is None:
                # If we can't get robots.txt, assume we can fetch
                logging.warning(f"Could not fetch robots.txt for {domain}, assuming allowed")
                return True
            
            # Check if we can fetch this URL
            can_fetch = robots_parser.can_fetch(self._user_agent, url)
            
            logging.info(f"Robots.txt check for {url}: {'ALLOWED' if can_fetch else 'BLOCKED'}")
            return can_fetch
            
        except Exception as e:
            logging.error(f"Error checking robots.txt for {url}: {e}")
            # Default to allowing if there's an error
            return True
    
    async def _get_robots_parser(self, domain: str) -> Optional[urllib.robotparser.RobotFileParser]:
        """Get cached or fetch robots.txt parser for domain"""
        current_time = time.time()
        
        # Check if we have a valid cached version
        if (domain in self._robots_cache and 
            domain in self._cache_timestamps and
            current_time - self._cache_timestamps[domain] < self._cache_duration):
            return self._robots_cache[domain]
        
        try:
            # Fetch robots.txt
            robots_url = f"https://{domain}/robots.txt"
            
            # Use asyncio to run the blocking operation
            robots_parser = await asyncio.to_thread(self._fetch_robots_sync, robots_url)
            
            # Cache the result
            self._robots_cache[domain] = robots_parser
            self._cache_timestamps[domain] = current_time
            
            return robots_parser
            
        except Exception as e:
            logging.error(f"Failed to fetch robots.txt for {domain}: {e}")
            return None
    
    def _fetch_robots_sync(self, robots_url: str) -> urllib.robotparser.RobotFileParser:
        """Synchronous robots.txt fetching"""
        robots_parser = urllib.robotparser.RobotFileParser()
        robots_parser.set_url(robots_url)
        robots_parser.read()
        return robots_parser
    
    def get_crawl_delay(self, domain: str) -> float:
        """Get crawl delay for domain from robots.txt"""
        if domain in self._robots_cache:
            robots_parser = self._robots_cache[domain]
            delay = robots_parser.crawl_delay(self._user_agent)
            return float(delay) if delay else 1.0  # Default 1 second
        return 1.0

# Global robots checker instance
robots_checker = RobotsChecker()

# Comprehensive whitelist of allowed domains
ALLOWED_DOMAINS = {
    # News & Information
    "www.bbc.com", "bbc.com", "www.reuters.com", "reuters.com",
    "www.cnn.com", "cnn.com", "www.npr.org", "npr.org",
    "www.theguardian.com", "theguardian.com", "apnews.com", "www.apnews.com",
    "www.wsj.com", "wsj.com", "www.nytimes.com", "nytimes.com",
    "www.economist.com", "economist.com", "www.forbes.com", "forbes.com",
    "www.washingtonpost.com", "washingtonpost.com", "www.ft.com", "ft.com",
    
    # Academic & Research
    "arxiv.org", "www.arxiv.org", "scholar.google.com", "www.nature.com", "nature.com",
    "www.science.org", "science.org", "www.pnas.org", "pnas.org",
    "pubmed.ncbi.nlm.nih.gov", "www.ncbi.nlm.nih.gov", "ncbi.nlm.nih.gov",
    "www.researchgate.net", "researchgate.net", "papers.ssrn.com", "ssrn.com",
    "ieeexplore.ieee.org", "dl.acm.org", "link.springer.com", "www.jstor.org",
    "www.semanticscholar.org", "semanticscholar.org", "www.mendeley.com", "mendeley.com",
    
    # Technology & AI
    "en.wikipedia.org", "wikipedia.org", "www.wikipedia.org",
    "stackoverflow.com", "www.stackoverflow.com", "github.com", "www.github.com",
    "docs.python.org", "www.python.org", "python.org",
    "openai.com", "www.openai.com", "anthropic.com", "www.anthropic.com",
    "huggingface.co", "www.huggingface.co", "pytorch.org", "www.pytorch.org",
    "tensorflow.org", "www.tensorflow.org", "scikit-learn.org", "www.scikit-learn.org",
    "www.kaggle.com", "kaggle.com", "paperswithcode.com", "www.paperswithcode.com",
    
    # Government & Official Sources
    "www.gov.uk", "gov.uk", "www.usa.gov", "usa.gov", "www.whitehouse.gov",
    "ec.europa.eu", "europa.eu", "www.un.org", "un.org",
    "www.who.int", "who.int", "www.cdc.gov", "cdc.gov",
    "www.fda.gov", "fda.gov", "www.sec.gov", "sec.gov",
    "www.treasury.gov", "treasury.gov", "www.justice.gov", "justice.gov",
    
    # Educational Institutions
    "www.mit.edu", "mit.edu", "www.stanford.edu", "stanford.edu",
    "www.harvard.edu", "harvard.edu", "www.ox.ac.uk", "ox.ac.uk",
    "www.cam.ac.uk", "cam.ac.uk", "www.berkeley.edu", "berkeley.edu",
    "www.caltech.edu", "caltech.edu", "www.cmu.edu", "cmu.edu",
    "coursera.org", "www.coursera.org", "www.edx.org", "edx.org",
    "www.khanacademy.org", "khanacademy.org", "www.futurelearn.com", "futurelearn.com",
    
    # Technical Documentation
    "docs.microsoft.com", "developer.mozilla.org", "www.w3.org", "w3.org",
    "www.ietf.org", "ietf.org", "tools.ietf.org", "datatracker.ietf.org",
    "www.iso.org", "iso.org", "standards.ieee.org", "www.rfc-editor.org",
    
    # Data & Statistics
    "data.worldbank.org", "www.worldbank.org", "worldbank.org",
    "www.imf.org", "imf.org", "data.oecd.org", "www.oecd.org", "oecd.org",
    "www.census.gov", "census.gov", "data.gov", "www.data.gov",
    "ourworldindata.org", "www.ourworldindata.org", "www.statista.com", "statista.com",
    "www.gapminder.org", "gapminder.org", "www.indexmundi.com", "indexmundi.com",
    
    # Climate & Environment
    "www.ipcc.ch", "ipcc.ch", "climate.nasa.gov", "www.nasa.gov", "nasa.gov",
    "www.noaa.gov", "noaa.gov", "www.epa.gov", "epa.gov",
    "www.unep.org", "unep.org", "www.wmo.int", "wmo.int",
    "www.iea.org", "iea.org", "www.irena.org", "irena.org",
    
    # Health & Medicine
    "www.nih.gov", "nih.gov", "www.mayoclinic.org", "mayoclinic.org",
    "www.webmd.com", "webmd.com", "medlineplus.gov", "www.medlineplus.gov",
    "www.cochrane.org", "cochrane.org", "bmj.com", "www.bmj.com",
    "www.thelancet.com", "thelancet.com", "jamanetwork.com", "www.jamanetwork.com",
    
    # Finance & Economics
    "www.investopedia.com", "investopedia.com", "finance.yahoo.com",
    "www.bloomberg.com", "bloomberg.com", "www.marketwatch.com", "marketwatch.com",
    "fred.stlouisfed.org", "www.federalreserve.gov", "federalreserve.gov",
    "www.bis.org", "bis.org", "www.ecb.europa.eu", "ecb.europa.eu",
    
    # Search & Knowledge Aggregation
    "duckduckgo.com", "www.duckduckgo.com", "search.brave.com",
    "www.bing.com", "bing.com", "yandex.com", "www.yandex.com",
    "www.wolframalpha.com", "wolframalpha.com",
    
    # Utilities & Archives
    "archive.org", "www.archive.org", "web.archive.org",
    "www.google.com", "google.com",  # For some API endpoints
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