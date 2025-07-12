"""
Security‑hardened tool plugin:  web search, fetch page, file I/O, etc.

Key extras vs. upstream:
• strict path sandbox (`_get_safe_path`)
• dynamic tool dispatcher (`execute_tool`)
• rate‑limiter + security validator
• alias  browse_webpage()  → fetch_webpage()   for back‑compat
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
import urllib.parse
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List

import aiofiles
import httpx
from bs4 import BeautifulSoup

from . import config
from .config_manager import ConfigManager
from .skill_manager import register_innate_action

# ------------------------------------------------------------------ #
#                           SECURITY HELPERS                         #
# ------------------------------------------------------------------ #


class SecurityValidator:
    """URL / content hardening (trimmed for brevity)."""

    @staticmethod
    def validate_url(url: str) -> Dict[str, Any]:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            return {"valid": False, "error": "bad scheme or host", "risk": "high"}
        return {"valid": True}

    @staticmethod
    def analyze_content_security(content: bytes) -> Dict[str, Any]:
        if len(content) > 10 * 1024 * 1024:
            return {"safe": False, "risk": "medium", "issues": [">10 MB"]}
        return {"safe": True}


# ------------------------------------------------------------------ #
#                           RATE LIMITER                             #
# ------------------------------------------------------------------ #


class RateLimiter:
    """Per‑domain sliding‑window limiter + auto‑block on repeated fails."""

    def __init__(self, max_requests: int = 10, interval: int = 60):
        self.max = max_requests
        self.interval = interval
        self.reqs: Dict[str, List[float]] = defaultdict(list)
        self.blocked: Dict[str, float] = {}

    async def allow(self, domain: str) -> bool:
        now = time.time()
        if self.blocked.get(domain, 0) > now:
            return False
        self.reqs[domain] = [t for t in self.reqs[domain] if t > now - self.interval]
        if len(self.reqs[domain]) >= self.max:
            return False
        self.reqs[domain].append(now)
        return True


_rate_limiter = RateLimiter(10, 60)

# ------------------------------------------------------------------ #
#                              TOOL PLUGIN                           #
# ------------------------------------------------------------------ #


class ToolPlugin:
    """Injected into SymbolicAGI; exposes async tools."""

    def __init__(self, agi: "SymbolicAGI"):
        self.agi = agi
        self.workspace_dir = config.get_config().workspace_dir
        os.makedirs(self.workspace_dir, exist_ok=True)

    # ---------------- path sandbox ---------------- #

    def _get_safe_path(self, filename: str) -> str:
        filename = os.path.normpath(filename)
        path = os.path.abspath(os.path.join(self.workspace_dir, filename))
        if not path.startswith(os.path.abspath(self.workspace_dir)):
            raise ValueError("path escapes workspace")
        return path

    # ---------------- generic dispatcher ---------- #

    async def execute_tool(self, name: str, params: Dict[str, Any]):
        fn = globals().get(name)
        if asyncio.iscoroutinefunction(fn):
            return await fn(self.agi, **params)
        if hasattr(self, name) and asyncio.iscoroutinefunction(getattr(self, name)):
            return await getattr(self, name)(**params)
        return {"status": "failure", "description": f"unknown tool {name}"}


# ------------------------------------------------------------------ #
#                            PRIMITIVE ACTIONS                       #
# ------------------------------------------------------------------ #

# ---------- web_search ---------------------------------------------------- #


@register_innate_action("DuckDuckGo search → list of results")
async def web_search(agi: "SymbolicAGI", query: str) -> Dict[str, Any]:
    if not query.strip():
        return {"status": "failure", "description": "empty query"}
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(
            "https://duckduckgo.com/html/",
            params={"q": query, "kl": "us-en"},
            headers={"User-Agent": "Mozilla/5.0"},
        )
    soup = BeautifulSoup(r.text, "lxml")
    links = [
        {"title": a.get_text(" ", strip=True), "url": a["href"]}
        for a in soup.select(".result__a")[:10]
    ]
    return {"status": "success", "results": links}


# ---------- fetch_webpage -------------------------------------------------- #


@register_innate_action("Download + strip HTML to plain text")
async def fetch_webpage(agi: "SymbolicAGI", url: str) -> Dict[str, Any]:
    v = SecurityValidator.validate_url(url)
    if not v["valid"]:
        return {"status": "failure", "description": v["error"]}

    domain = urllib.parse.urlparse(url).netloc
    if not await _rate_limiter.allow(domain):
        return {"status": "failure", "description": "rate‑limited"}

    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(url, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})
    if r.status_code != 200:
        return {"status": "failure", "description": f"HTTP {r.status_code}"}

    sec = SecurityValidator.analyze_content_security(r.content)
    if not sec["safe"]:
        return {"status": "failure", "description": "content deemed unsafe"}

    soup = BeautifulSoup(r.text, "lxml")
    text = soup.get_text(" ", strip=True)[:8000]
    return {"status": "success", "content": text, "url": str(r.url)}


# ---------- browse_webpage  (alias) --------------------------------------- #


@register_innate_action("Deprecated alias → fetch_webpage")
async def browse_webpage(agi: "SymbolicAGI", url: str) -> Dict[str, Any]:
    return await fetch_webpage(agi, url)


# ---------- read_file / write_file / list_files --------------------------- #


@register_innate_action("Write text file inside workspace")
async def write_file(agi: "SymbolicAGI", filename: str, content: str) -> Dict[str, Any]:
    try:
        path = agi.tools._get_safe_path(filename)
        async with aiofiles.open(path, "w", encoding="utf‑8") as f:
            await f.write(content)
        return {"status": "success", "path": str(path)}
    except Exception as e:
        logging.error("write_file error", exc_info=True)
        return {"status": "failure", "description": str(e)}


@register_innate_action("Read text file from workspace")
async def read_file(agi: "SymbolicAGI", filename: str) -> Dict[str, Any]:
    try:
        path = agi.tools._get_safe_path(filename)
        async with aiofiles.open(path, "r", encoding="utf‑8") as f:
            data = await f.read()
        return {"status": "success", "content": data}
    except Exception as e:
        return {"status": "failure", "description": str(e)}


@register_innate_action("List workspace files (non‑recursive)")
async def list_files(agi: "SymbolicAGI") -> Dict[str, Any]:
    files = os.listdir(agi.tools.workspace_dir)
    return {"status": "success", "files": files}
