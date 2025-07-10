# symbolic_agi/tools/web.py

import asyncio
import json
import logging
from typing import Dict, Any
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
try:
    from ddgs import DDGS
except ImportError:
    DDGS = None

from symbolic_agi.tools.base import BaseTool
from symbolic_agi import config
from symbolic_agi.skill_manager import register_innate_action

class WebTools(BaseTool):
    """Tools for interacting with the World Wide Web."""

    NO_ACTIVE_PAGE_MSG = "No active page in the browser."

    def _is_url_allowed(self, url: str) -> bool:
        """Checks if a URL's domain is in the configured allow-list."""
        try:
            hostname = urlparse(url).hostname
            if hostname and hostname in config.ALLOWED_DOMAINS:
                return True
            logging.critical("URL BLOCKED: Attempted to access non-allowed domain: %s", hostname)
            return False
        except Exception as e:
            logging.error("URL validation failed for '%s': %s", url, e)
            return False

    async def _check_robots_compliance(self, url: str) -> bool:
        """Checks if URL is compliant with robots.txt rules."""
        return await config.robots_checker.can_fetch(url)

    async def _get_crawl_delay(self, url: str) -> float:
        """Gets appropriate crawl delay for URL's domain."""
        hostname = urlparse(url).hostname
        return config.robots_checker.get_crawl_delay(hostname) if hostname else 1.0

    @register_innate_action("orchestrator", "Opens a new browser page and navigates to the URL.")
    async def browser_new_page(self, url: str, **kwargs: Any) -> Dict[str, Any]:
        if not self.agi.browser:
            return {"status": "failure", "description": "Browser is not initialized."}
        try:
            self.agi.page = await self.agi.browser.new_page()
            await self.agi.page.goto(url, wait_until="domcontentloaded")
            return {"status": "success", "description": f"Successfully navigated to {url}."}
        except Exception as e:
            return {"status": "failure", "description": f"Failed to navigate to {url}: {e}"}

    @register_innate_action("orchestrator", "Gets a simplified representation of the current page's interactive elements.")
    async def browser_get_content(self, **kwargs: Any) -> Dict[str, Any]:
        if not self.agi.page:
            return {"status": "failure", "description": self.NO_ACTIVE_PAGE_MSG}
        try:
            page_elements = await self.agi.page.evaluate(
                """() => {
                const query = 'a, button, input, select, textarea, [role="button"], [role="link"]';
                return Array.from(document.querySelectorAll(query)).map(el => ({
                    tag: el.tagName.toLowerCase(),
                    text: el.innerText.trim().substring(0, 100),
                    name: el.name, id: el.id, 'aria-label': el.getAttribute('aria-label')
                }));
            }"""
            )
            return {"status": "success", "content": json.dumps(page_elements, indent=2)}
        except Exception as e:
            return {"status": "failure", "description": f"Failed to get page content: {e}"}

    @register_innate_action("orchestrator", "Clicks an element on the page identified by a CSS selector.")
    async def browser_click(self, selector: str, **kwargs: Any) -> Dict[str, Any]:
        if not self.agi.page:
            return {"status": "failure", "description": self.NO_ACTIVE_PAGE_MSG}
        try:
            await self.agi.page.locator(selector).click(timeout=5000)
            await self.agi.page.wait_for_load_state("domcontentloaded", timeout=10000)
            return {"status": "success", "description": f"Successfully clicked element '{selector}'."}
        except Exception as e:
            return {"status": "failure", "description": f"Failed to click element '{selector}': {e}"}

    @register_innate_action("orchestrator", "Fills an input field on the page with the given text.")
    async def browser_fill(self, selector: str, text: str, **kwargs: Any) -> Dict[str, Any]:
        if not self.agi.page:
            return {"status": "failure", "description": self.NO_ACTIVE_PAGE_MSG}
        try:
            await self.agi.page.locator(selector).fill(text, timeout=5000)
            return {"status": "success", "description": f"Successfully filled element '{selector}'."}
        except Exception as e:
            return {"status": "failure", "description": f"Failed to fill element '{selector}': {e}"}

    @register_innate_action("orchestrator", "Fetches and returns the text content of a webpage.")
    async def browse_webpage(self, url: str, **kwargs: Any) -> Dict[str, Any]:
        if not self._is_url_allowed(url) or not await self._check_robots_compliance(url):
            return {"status": "failure", "description": f"Access to URL '{url}' is blocked."}

        await asyncio.sleep(await self._get_crawl_delay(url))

        try:
            headers = {"User-Agent": "SymbolicAGI/1.0 (Research Bot)"}
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            for script in soup(["script", "style"]):
                script.extract()
            text = soup.get_text(separator='\n', strip=True)
            return {"status": "success", "content": text[:8000]}
        except Exception as e:
            return {"status": "failure", "description": f"Error browsing webpage: {e}"}

    @register_innate_action("orchestrator", "Performs a web search and returns the results.")
    async def web_search(self, query: str, num_results: int = 3, **kwargs: Any) -> Dict[str, Any]:
        if DDGS is None:
            return {"status": "failure", "description": "Web search unavailable: ddgs library not installed."}

        try:
            with DDGS() as ddgs:
                results = [r for r in ddgs.text(query, max_results=num_results) if self._is_url_allowed(r['href'])]

            if not results:
                return {"status": "success", "data": "No results found from allowed domains."}

            summary = "\n\n".join(f"Title: {r['title']}\nSnippet: {r['body']}\nURL: {r['href']}" for r in results)
            return {"status": "success", "data": summary}
        except Exception as e:
            return {"status": "failure", "description": f"Web search error: {e}"}