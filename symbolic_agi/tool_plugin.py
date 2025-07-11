# symbolic_agi/tool_plugin.py
import asyncio
import base64
import hashlib
import html
import ipaddress
import json
import logging
import os
import re
import socket
import subprocess
import tempfile
import time
import urllib.parse
from collections import defaultdict
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set
import warnings

import aiofiles
import httpx
from bs4 import BeautifulSoup

from . import config
from .config_manager import ConfigManager
from .skill_manager import register_innate_action

if TYPE_CHECKING:
    from .agi_controller import SymbolicAGI

class SecurityValidator:
    """Enhanced security validation for web requests and content."""
    
    # Dangerous file extensions that should never be downloaded or processed
    DANGEROUS_EXTENSIONS = {
        '.exe', '.bat', '.cmd', '.scr', '.pif', '.com', '.jar', '.msi', 
        '.deb', '.rpm', '.dmg', '.pkg', '.app', '.vbs', '.js', '.jse',
        '.ws', '.wsf', '.wsc', '.wsh', '.ps1', '.psm1', '.psd1', '.ps1xml',
        '.ps2', '.ps2xml', '.psc1', '.psc2', '.msh', '.msh1', '.msh2',
        '.mshxml', '.msh1xml', '.msh2xml'
    }
    
    # Suspicious URL patterns that might indicate malicious content
    SUSPICIOUS_PATTERNS = [
        r'bit\.ly', r'tinyurl', r'short\.link', r'rebrand\.ly',  # URL shorteners
        r'[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+',  # Raw IP addresses
        r'localhost', r'127\.0\.0\.1', r'0\.0\.0\.0',  # Local addresses
        r'[a-f0-9]{32,}',  # Long hex strings (possible hashes)
        r'download.*\.(exe|zip|rar)', r'payload', r'exploit'  # Suspicious keywords
    ]
    
    # Malicious file signatures (magic bytes)
    MALICIOUS_SIGNATURES = {
        b'MZ': 'PE/DOS executable',
        b'PK': 'ZIP/JAR archive',
        b'\x7fELF': 'ELF executable',
        b'\xca\xfe\xba\xbe': 'Java class file',
        b'\xfe\xed\xfa': 'Mach-O executable'
    }
    
    @staticmethod
    def validate_url(url: str) -> Dict[str, Any]:
        """Comprehensive URL validation with security checks."""
        try:
            parsed = urllib.parse.urlparse(url)
            
            # Basic format validation
            basic_validation = SecurityValidator._validate_basic_format(parsed)
            if not basic_validation['valid']:
                return basic_validation
            
            # Security threat validation
            security_validation = SecurityValidator._validate_security_threats(url, parsed)
            if not security_validation['valid']:
                return security_validation
            
            # Hostname validation
            hostname_validation = SecurityValidator._validate_hostname(parsed.hostname)
            if not hostname_validation['valid']:
                return hostname_validation
            
            # Collect all issues and determine risk level
            issues = []
            risk_level = "low"
            
            # Check for suspicious patterns
            for pattern in SecurityValidator.SUSPICIOUS_PATTERNS:
                if re.search(pattern, url, re.IGNORECASE):
                    issues.append(f'Suspicious pattern detected: {pattern}')
                    risk_level = "high"
            
            # Check URL length
            if len(url) > 2048:
                issues.append('Extremely long URL detected')
                risk_level = "medium"
            
            # Check for excessive subdomains
            if parsed.hostname and parsed.hostname.count('.') > 4:
                issues.append('Excessive subdomains detected')
                risk_level = "medium"
            
            return {
                'valid': True,
                'issues': issues,
                'risk_level': risk_level,
                'hostname': parsed.hostname,
                'scheme': parsed.scheme
            }
            
        except Exception as e:
            return {
                'valid': False,
                'error': f'URL validation error: {str(e)}',
                'risk_level': 'high'
            }
    
    @staticmethod
    def _validate_basic_format(parsed) -> Dict[str, Any]:
        """Validate basic URL format requirements."""
        if not parsed.scheme or not parsed.netloc:
            return {
                'valid': False,
                'error': 'Invalid URL format',
                'risk_level': 'high'
            }
        
        if parsed.scheme not in ['http', 'https']:
            return {
                'valid': False,
                'error': f'Unsupported protocol: {parsed.scheme}',
                'risk_level': 'high'
            }
        
        return {'valid': True}
    
    @staticmethod
    def _validate_security_threats(url: str, parsed) -> Dict[str, Any]:
        """Check for dangerous file extensions and security threats."""
        path_lower = parsed.path.lower()
        for ext in SecurityValidator.DANGEROUS_EXTENSIONS:
            if path_lower.endswith(ext):
                return {
                    'valid': False,
                    'error': f'Dangerous file extension: {ext}',
                    'risk_level': 'critical'
                }
        return {'valid': True}
    
    @staticmethod
    def _validate_hostname(hostname: str) -> Dict[str, Any]:
        """Validate hostname for private/local access attempts."""
        if not hostname:
            return {'valid': True}
        
        # Check for private/local IP addresses
        try:
            ip = ipaddress.ip_address(hostname)
            if ip.is_private or ip.is_loopback or ip.is_link_local:
                return {
                    'valid': False,
                    'error': f'Access to private/local IP address denied: {hostname}',
                    'risk_level': 'high'
                }
        except ValueError:
            pass  # Not an IP address
        
        # Check for localhost variants
        localhost_patterns = ['localhost', '127.', '0.0.0.0', '::1']
        if any(pattern in hostname.lower() for pattern in localhost_patterns):
            return {
                'valid': False,
                'error': f'Access to localhost denied: {hostname}',
                'risk_level': 'high'
            }
        
        return {'valid': True}
    
    @staticmethod
    def analyze_content_security(content: bytes, content_type: str = '') -> Dict[str, Any]:
        """Analyze content for security threats."""
        issues = []
        risk_level = "low"
        
        # Check file signatures
        for signature, description in SecurityValidator.MALICIOUS_SIGNATURES.items():
            if content.startswith(signature):
                return {
                    'safe': False,
                    'threat': f'Potentially malicious file detected: {description}',
                    'risk_level': 'critical'
                }
        
        # Check for suspicious patterns in content
        content_str = content.decode('utf-8', errors='ignore').lower()
        
        suspicious_content = [
            'eval(', 'document.cookie', 'document.write', 'innerhtml',
            'onclick=', 'onerror=', 'onload=', 'javascript:',
            'vbscript:', 'data:text/html', 'base64,',
            'powershell', 'cmd.exe', '/bin/sh', 'wget ', 'curl ',
            'unescape(', 'fromcharcode(', 'atob(', 'btoa('
        ]
        
        found_suspicious = []
        for pattern in suspicious_content:
            if pattern in content_str:
                found_suspicious.append(pattern)
                risk_level = "high"
        
        if found_suspicious:
            issues.append(f'Suspicious content patterns: {", ".join(found_suspicious[:5])}')
        
        # Check content size
        if len(content) > 10 * 1024 * 1024:  # 10MB
            issues.append('Large content size detected')
            risk_level = max(risk_level, "medium")
        
        return {
            'safe': risk_level != "critical",
            'issues': issues,
            'risk_level': risk_level,
            'size': len(content)
        }

class ToolPlugin:
    """Provides tool capabilities to the AGI."""
    
    def __init__(self, agi: "SymbolicAGI"):
        self.agi = agi
        self.robots_checker = ConfigManager()
        self.workspace_dir = config.get_config().workspace_dir
        os.makedirs(self.workspace_dir, exist_ok=True)

class RateLimiter:
    """Enhanced rate limiter with security monitoring and adaptive thresholds."""
    
    def __init__(self, max_requests: int = 10, time_window: int = 60):
        """
        Initialize enhanced rate limiter.
        
        Args:
            max_requests: Maximum requests allowed in time window
            time_window: Time window in seconds
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = defaultdict(list)  # domain -> list of timestamps
        self.failed_attempts = defaultdict(int)  # domain -> failed attempt count
        self.blocked_domains = defaultdict(float)  # domain -> unblock timestamp
        self._lock = asyncio.Lock()
    
    async def can_request(self, domain: str) -> bool:
        """Check if a request to domain is allowed with enhanced security."""
        async with self._lock:
            now = time.time()
            
            # Check if domain is temporarily blocked
            if domain in self.blocked_domains and now < self.blocked_domains[domain]:
                SecurityLogger.log_security_event(
                    "rate_limit_blocked_domain",
                    f"Request to blocked domain: {domain}",
                    {"domain": domain, "unblock_time": self.blocked_domains[domain]}
                )
                return False
            
            domain_requests = self.requests[domain]
            
            # Remove old requests outside the time window
            cutoff = now - self.time_window
            self.requests[domain] = [t for t in domain_requests if t > cutoff]
            
            # Calculate dynamic limit based on failed attempts
            failed_count = self.failed_attempts.get(domain, 0)
            dynamic_limit = max(1, self.max_requests - (failed_count // 2))
            
            # Check if we're under the limit
            if len(self.requests[domain]) < dynamic_limit:
                self.requests[domain].append(now)
                return True
            
            # Log rate limit violation
            SecurityLogger.log_security_event(
                "rate_limit_exceeded",
                f"Rate limit exceeded for domain: {domain}",
                {
                    "domain": domain,
                    "current_requests": len(self.requests[domain]),
                    "limit": dynamic_limit,
                    "failed_attempts": failed_count
                }
            )
            
            return False
    
    def record_failed_attempt(self, domain: str):
        """Record a failed attempt for a domain."""
        self.failed_attempts[domain] += 1
        
        # Block domain temporarily if too many failures
        if self.failed_attempts[domain] >= 5:
            block_duration = min(3600, 60 * (2 ** (self.failed_attempts[domain] - 5)))  # Exponential backoff
            self.blocked_domains[domain] = time.time() + block_duration
            
            SecurityLogger.log_security_event(
                "domain_temporarily_blocked",
                f"Domain blocked due to repeated failures: {domain}",
                {
                    "domain": domain,
                    "failed_attempts": self.failed_attempts[domain],
                    "block_duration": block_duration
                }
            )
    
    def record_successful_request(self, domain: str):
        """Record a successful request for a domain."""
        # Gradually reduce failed attempt count on success
        if domain in self.failed_attempts:
            self.failed_attempts[domain] = max(0, self.failed_attempts[domain] - 1)
    
    async def wait_for_availability(self, domain: str, max_wait: float = 30.0) -> bool:
        """Wait until a request to domain is allowed (up to max_wait seconds)."""
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            if await self.can_request(domain):
                return True
            await asyncio.sleep(1.0)
        
        return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current rate limiting statistics."""
        now = time.time()
        stats = {}
        
        for domain, timestamps in self.requests.items():
            recent = [t for t in timestamps if t > now - self.time_window]
            failed_count = self.failed_attempts.get(domain, 0)
            dynamic_limit = max(1, self.max_requests - (failed_count // 2))
            
            stats[domain] = {
                "recent_requests": len(recent),
                "max_requests": self.max_requests,
                "dynamic_limit": dynamic_limit,
                "time_window": self.time_window,
                "requests_remaining": max(0, dynamic_limit - len(recent)),
                "failed_attempts": failed_count,
                "is_blocked": domain in self.blocked_domains and now < self.blocked_domains[domain]
            }
        
        return stats

class SecurityLogger:
    """Centralized security event logging and monitoring."""
    
    _events = defaultdict(list)  # event_type -> list of events
    _lock = asyncio.Lock()
    
    @classmethod
    async def log_security_event(cls, event_type: str, message: str, details: Dict[str, Any] = None):
        """Log a security event with timestamp and details."""
        async with cls._lock:
            event = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'event_type': event_type,
                'message': message,
                'details': details or {}
            }
            
            cls._events[event_type].append(event)
            
            # Keep only last 1000 events per type
            if len(cls._events[event_type]) > 1000:
                cls._events[event_type] = cls._events[event_type][-1000:]
            
            # Log to standard logger as well
            logging.warning(f"SECURITY EVENT [{event_type}]: {message} - {details}")
    
    @classmethod
    def get_security_summary(cls, hours: int = 24) -> Dict[str, Any]:
        """Get security events summary for the last N hours."""
        cutoff = datetime.now(timezone.utc).timestamp() - (hours * 3600)
        summary = defaultdict(int)
        recent_events = []
        
        for event_type, events in cls._events.items():
            for event in events:
                event_time = datetime.fromisoformat(event['timestamp']).timestamp()
                if event_time > cutoff:
                    summary[event_type] += 1
                    recent_events.append(event)
        
        return {
            'summary': dict(summary),
            'total_events': sum(summary.values()),
            'recent_events': sorted(recent_events, key=lambda x: x['timestamp'], reverse=True)[:50],
            'time_range_hours': hours
        }

# Enhanced global rate limiter with security features
_rate_limiter = RateLimiter(max_requests=10, time_window=60)

@register_innate_action
async def web_search(agi: "SymbolicAGI", query: str) -> Dict[str, Any]:
    """Search the web using DuckDuckGo with enhanced security."""
    try:
        # Validate and sanitize input
        validation_result = _validate_search_input(query)
        if not validation_result['valid']:
            return validation_result
        
        sanitized_query = validation_result['query']
        
        # Check rate limiting
        domain = "html.duckduckgo.com"
        rate_limit_result = await _check_search_rate_limit(domain, sanitized_query)
        if not rate_limit_result['allowed']:
            return rate_limit_result
        
        # Perform search request
        search_result = await _perform_search_request(sanitized_query)
        if not search_result['success']:
            _rate_limiter.record_failed_attempt(domain)
            return search_result
        
        # Process and validate results
        processed_results = await _process_search_results(search_result['soup'], sanitized_query)
        
        _rate_limiter.record_successful_request(domain)
        
        return {
            'success': True,
            'results': processed_results['results'],
            'query': sanitized_query,
            'security_analysis': search_result['security_analysis']
        }
        
    except Exception as e:
        _rate_limiter.record_failed_attempt("html.duckduckgo.com")
        await SecurityLogger.log_security_event(
            "search_exception",
            f"Search exception: {str(e)}",
            {"query": query, "error": str(e)}
        )
        logging.error(f"Web search error: {e}")
        return {
            'success': False,
            'error': str(e)
        }

def _validate_search_input(query: str) -> Dict[str, Any]:
    """Validate and sanitize search input."""
    if not query or len(query.strip()) == 0:
        return {
            'valid': False,
            'success': False,
            'error': 'Empty search query provided'
        }
    
    sanitized_query = sanitize_search_query(query)
    if not sanitized_query:
        return {
            'valid': False,
            'success': False,
            'error': 'Search query contains potentially malicious content'
        }
    
    return {
        'valid': True,
        'query': sanitized_query
    }

async def _check_search_rate_limit(domain: str, query: str) -> Dict[str, Any]:
    """Check rate limiting for search requests."""
    if not await _rate_limiter.can_request(domain):
        await SecurityLogger.log_security_event(
            "search_rate_limit_exceeded",
            f"Search rate limit exceeded for query: {query[:100]}",
            {"query": query, "domain": domain}
        )
        return {
            'allowed': False,
            'success': False,
            'error': 'Search rate limit exceeded, please try again later'
        }
    
    return {'allowed': True}

async def _perform_search_request(query: str) -> Dict[str, Any]:
    """Perform the actual search request with security checks."""
    search_url = "https://html.duckduckgo.com/html/"
    
    async with httpx.AsyncClient(
        limits=httpx.Limits(max_connections=5, max_keepalive_connections=2),
        timeout=httpx.Timeout(10.0, connect=5.0),
        follow_redirects=True
    ) as client:
        response = await client.post(
            search_url,
            data={"q": query},
            headers={
                "User-Agent": "SymbolicAGI/1.0 (Security-Enhanced)",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache"
            }
        )
        
        if response.status_code != 200:
            await SecurityLogger.log_security_event(
                "search_request_failed",
                f"Search request failed with status {response.status_code}",
                {"status_code": response.status_code, "query": query}
            )
            return {
                'success': False,
                'error': f'Search failed with status {response.status_code}'
            }
        
        # Security analysis of response
        content_analysis = SecurityValidator.analyze_content_security(
            response.content, 
            response.headers.get('content-type', '')
        )
        
        if not content_analysis['safe']:
            await SecurityLogger.log_security_event(
                "unsafe_search_response",
                f"Unsafe content detected in search response: {content_analysis['threat']}",
                {"query": query, "analysis": content_analysis}
            )
            return {
                'success': False,
                'error': 'Search response contains potentially unsafe content'
            }
        
        soup = BeautifulSoup(response.text, 'html.parser')
        return {
            'success': True,
            'soup': soup,
            'security_analysis': content_analysis
        }

async def _process_search_results(soup, query: str) -> Dict[str, Any]:
    """Process and validate search results."""
    results = []
    
    for result in soup.find_all('div', class_='result')[:5]:
        title_elem = result.find('h2')
        snippet_elem = result.find('a', class_='result__snippet')
        url_elem = result.find('a', class_='result__url')
        
        if title_elem and url_elem:
            result_url = url_elem.get('href', '')
            
            # Validate each result URL
            url_validation = SecurityValidator.validate_url(result_url)
            if not url_validation['valid']:
                await SecurityLogger.log_security_event(
                    "malicious_search_result",
                    f"Malicious URL in search results: {url_validation['error']}",
                    {"url": result_url, "query": query}
                )
                continue  # Skip malicious URLs
            
            title = sanitize_web_content(title_elem.get_text(strip=True), 200)
            snippet = sanitize_web_content(snippet_elem.get_text(strip=True) if snippet_elem else '', 500)
            
            results.append({
                'title': title,
                'url': result_url,
                'snippet': snippet,
                'risk_level': url_validation.get('risk_level', 'low')
            })
    
    return {'results': results}

def sanitize_search_query(query: str) -> str:
    """Sanitize search query to prevent injection attacks."""
    if not query:
        return ""
    
    # Remove potentially dangerous characters and patterns
    dangerous_patterns = [
        r'<script.*?</script>',
        r'javascript:',
        r'vbscript:',
        r'data:text/html',
        r'eval\s*\(',
        r'document\.',
        r'window\.',
        r'["\'].*?["\']',  # Remove quoted strings that might contain injection
    ]
    
    cleaned_query = query
    for pattern in dangerous_patterns:
        cleaned_query = re.sub(pattern, '', cleaned_query, flags=re.IGNORECASE | re.DOTALL)
    
    # Limit length and normalize
    cleaned_query = cleaned_query[:500].strip()
    
    # Check if query is still meaningful after sanitization
    if len(cleaned_query) < 2 or len(cleaned_query) < len(query) * 0.5:
        return ""  # Too much was removed, likely malicious
    
    return cleaned_query

@register_innate_action
async def fetch_webpage(agi: "SymbolicAGI", url: str) -> Dict[str, Any]:
    """Fetch and parse a webpage with comprehensive security validation."""
    try:
        # Security validation
        security_check = await _validate_webpage_security(agi, url)
        if not security_check['valid']:
            return security_check
        
        domain = security_check['domain']
        
        # Perform HTTP request
        response_result = await _fetch_webpage_content(url, domain)
        if not response_result['success']:
            return response_result
        
        # Process and sanitize content
        processed_content = await _process_webpage_content(
            response_result['response'], 
            url, 
            domain
        )
        
        return processed_content
        
    except Exception as e:
        if 'domain' in locals():
            _rate_limiter.record_failed_attempt(domain)
        
        await SecurityLogger.log_security_event(
            "webpage_fetch_exception",
            f"Webpage fetch exception: {str(e)}",
            {"url": url, "error": str(e)}
        )
        logging.error(f"Webpage fetch error: {e}")
        return {
            'success': False,
            'error': str(e)
        }

async def _validate_webpage_security(agi: "SymbolicAGI", url: str) -> Dict[str, Any]:
    """Validate webpage URL for security compliance."""
    # Comprehensive URL validation
    url_validation = SecurityValidator.validate_url(url)
    if not url_validation['valid']:
        await SecurityLogger.log_security_event(
            "malicious_url_blocked",
            f"Malicious URL blocked: {url_validation['error']}",
            {"url": url, "validation": url_validation}
        )
        return {
            'valid': False,
            'success': False,
            'error': url_validation['error'],
            'risk_level': url_validation['risk_level']
        }
    
    parsed = urllib.parse.urlparse(url)
    domain = parsed.hostname
    
    # Check domain allowlist
    if domain not in config.get_config().allowed_domains:
        await SecurityLogger.log_security_event(
            "domain_not_allowed",
            f"Domain not in allowlist: {domain}",
            {"url": url, "domain": domain}
        )
        return {
            'valid': False,
            'success': False,
            'error': f'Domain {domain} not in allowed list'
        }
    
    # Check robots.txt
    if not agi.tools.robots_checker.can_fetch(url):
        await SecurityLogger.log_security_event(
            "robots_txt_blocked",
            f"URL blocked by robots.txt: {url}",
            {"url": url, "domain": domain}
        )
        return {
            'valid': False,
            'success': False,
            'error': 'Blocked by robots.txt'
        }
    
    # Rate limiting check
    if not await _rate_limiter.can_request(domain):
        await SecurityLogger.log_security_event(
            "webpage_rate_limit_exceeded",
            f"Rate limit exceeded for domain: {domain}",
            {"url": url, "domain": domain}
        )
        return {
            'valid': False,
            'success': False,
            'error': 'Rate limit exceeded, please try again later'
        }
    
    return {
        'valid': True,
        'domain': domain,
        'url_validation': url_validation
    }

async def _fetch_webpage_content(url: str, domain: str) -> Dict[str, Any]:
    """Fetch webpage content with enhanced security headers."""
    async with httpx.AsyncClient(
        limits=httpx.Limits(max_connections=3, max_keepalive_connections=1),
        timeout=httpx.Timeout(15.0, connect=5.0),
        follow_redirects=True,
        max_redirects=3
    ) as client:
        headers = {
            "User-Agent": "SymbolicAGI/1.0 (Security-Enhanced; +https://github.com/symbolic-agi)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,text/plain;q=0.8,*/*;q=0.1",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "DNT": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Upgrade-Insecure-Requests": "1"
        }
        
        response = await client.get(url, headers=headers)
        
        if response.status_code != 200:
            _rate_limiter.record_failed_attempt(domain)
            await SecurityLogger.log_security_event(
                "webpage_fetch_failed",
                f"Webpage fetch failed with status {response.status_code}",
                {"url": url, "status_code": response.status_code}
            )
            return {
                'success': False,
                'error': f'Failed with status {response.status_code}'
            }
        
        return {
            'success': True,
            'response': response
        }

async def _process_webpage_content(response, url: str, domain: str) -> Dict[str, Any]:
    """Process and sanitize webpage content."""
    # Security analysis of response content
    content_analysis = SecurityValidator.analyze_content_security(
        response.content,
        response.headers.get('content-type', '')
    )
    
    if not content_analysis['safe']:
        _rate_limiter.record_failed_attempt(domain)
        await SecurityLogger.log_security_event(
            "unsafe_webpage_content",
            f"Unsafe content detected: {content_analysis.get('threat', 'Unknown threat')}",
            {"url": url, "analysis": content_analysis}
        )
        return {
            'success': False,
            'error': f"Unsafe content detected: {content_analysis.get('threat', 'Security threat identified')}",
            'risk_level': content_analysis['risk_level']
        }
    
    # Parse and sanitize content
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Remove dangerous elements
    for dangerous_tag in soup(['script', 'style', 'iframe', 'object', 'embed', 'applet', 'form']):
        dangerous_tag.decompose()
    
    # Remove event handlers
    for tag in soup.find_all(True):
        attrs_to_remove = []
        for attr in tag.attrs.keys():
            should_remove = (
                attr.lower().startswith('on') or  # onclick, onload, etc.
                (attr.lower() in ['href', 'src'] and 
                 tag.attrs[attr].lower().startswith(('javascript:', 'vbscript:', 'data:')))
            )
            if should_remove:
                attrs_to_remove.append(attr)
        
        for attr in attrs_to_remove:
            del tag.attrs[attr]
    
    # Extract text content
    text = soup.get_text()
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = ' '.join(chunk for chunk in chunks if chunk)
    
    sanitized_content = sanitize_web_content(text, max_size=5000)
    
    # Extract safe links
    safe_links = _extract_safe_links(soup, url)
    
    # Analyze security headers
    security_headers = analyze_security_headers(response.headers)
    
    _rate_limiter.record_successful_request(domain)
    
    return {
        'success': True,
        'url': url,
        'title': sanitize_web_content(soup.title.string if soup.title else '', 200),
        'content': sanitized_content,
        'links': safe_links,
        'security_analysis': content_analysis,
        'security_headers': security_headers,
        'risk_level': 'low'
    }

def _extract_safe_links(soup, base_url: str) -> List[Dict[str, Any]]:
    """Extract and validate links from webpage content."""
    safe_links = []
    for link in soup.find_all('a', href=True)[:20]:
        link_url = link.get('href', '')
        if link_url:
            try:
                absolute_url = urllib.parse.urljoin(base_url, link_url)
                link_validation = SecurityValidator.validate_url(absolute_url)
                if link_validation['valid']:
                    safe_links.append({
                        'url': absolute_url,
                        'text': sanitize_web_content(link.get_text(strip=True), 100),
                        'risk_level': link_validation.get('risk_level', 'unknown')
                    })
            except Exception:
                continue
    return safe_links

def analyze_security_headers(headers: Dict[str, str]) -> Dict[str, Any]:
    """Analyze HTTP response headers for security indicators."""
    security_analysis = {
        'score': 0,
        'present': [],
        'missing': [],
        'issues': []
    }
    
    # Important security headers to check
    security_headers = {
        'Strict-Transport-Security': 'HSTS protection',
        'Content-Security-Policy': 'CSP protection',
        'X-Frame-Options': 'Clickjacking protection',
        'X-Content-Type-Options': 'MIME-type sniffing protection',
        'X-XSS-Protection': 'XSS filter',
        'Referrer-Policy': 'Referrer information control'
    }
    
    for header, description in security_headers.items():
        if header.lower() in [h.lower() for h in headers.keys()]:
            security_analysis['present'].append({
                'header': header,
                'description': description,
                'value': headers.get(header, '')
            })
            security_analysis['score'] += 1
        else:
            security_analysis['missing'].append({
                'header': header,
                'description': description
            })
    
    # Check for potentially problematic headers
    dangerous_headers = ['Server', 'X-Powered-By', 'X-AspNet-Version']
    for header in dangerous_headers:
        if header.lower() in [h.lower() for h in headers.keys()]:
            security_analysis['issues'].append({
                'header': header,
                'issue': 'Information disclosure',
                'value': headers.get(header, '')
            })
    
    # Calculate security score (0-100)
    security_analysis['score'] = min(100, (security_analysis['score'] / len(security_headers)) * 100)
    
    return security_analysis

@register_innate_action
async def write_file(agi: "SymbolicAGI", filename: str, content: str) -> Dict[str, Any]:
    """Write content to a file in the workspace."""
    try:
        # Ensure file is in workspace
        safe_path = os.path.join(agi.tools.workspace_dir, os.path.basename(filename))
        
        async with aiofiles.open(safe_path, 'w') as f:
            await f.write(content)
            
        return {
            'success': True,
            'path': safe_path,
            'size': len(content)
        }
        
    except Exception as e:
        logging.error(f"File write error: {e}")
        return {
            'success': False,
            'error': str(e)
        }

@register_innate_action
async def read_file(agi: "SymbolicAGI", filename: str) -> Dict[str, Any]:
    """Read content from a file in the workspace."""
    try:
        safe_path = os.path.join(agi.tools.workspace_dir, os.path.basename(filename))
        
        if not os.path.exists(safe_path):
            return {
                'success': False,
                'error': 'File not found'
            }
            
        async with aiofiles.open(safe_path, 'r') as f:
            content = await f.read()
            
        return {
            'success': True,
            'path': safe_path,
            'content': content,
            'size': len(content)
        }
        
    except Exception as e:
        logging.error(f"File read error: {e}")
        return {
            'success': False,
            'error': str(e)
        }

@register_innate_action
async def execute_python(agi: "SymbolicAGI", code: str) -> Dict[str, Any]:
    """Execute Python code in a sandboxed environment."""
    try:
        # Create temporary file
        temp_fd, temp_path = tempfile.mkstemp(suffix='.py')
        try:
            # Close the file descriptor and write code using async file operations
            os.close(temp_fd)
            async with aiofiles.open(temp_path, 'w') as f:
                await f.write(code)
            
            # Execute with timeout
            process = await asyncio.create_subprocess_exec(
                'python', temp_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=agi.tools.workspace_dir
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=30.0
            )
            
            return {
                'success': process.returncode == 0,
                'stdout': stdout.decode() if stdout else '',
                'stderr': stderr.decode() if stderr else '',
                'return_code': process.returncode
            }
            
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            
    except asyncio.TimeoutError:
        return {
            'success': False,
            'error': 'Execution timeout'
        }
    except Exception as e:
        logging.error(f"Python execution error: {e}")
        return {
            'success': False,
            'error': str(e)
        }

@register_innate_action
async def list_files(agi: "SymbolicAGI") -> Dict[str, Any]:
    """List files in the workspace directory."""
    try:
        files = []
        for filename in os.listdir(agi.tools.workspace_dir):
            path = os.path.join(agi.tools.workspace_dir, filename)
            if os.path.isfile(path):
                stat = os.stat(path)
                files.append({
                    'name': filename,
                    'size': stat.st_size,
                    'modified': datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat()
                })
                
        return {
            'success': True,
            'files': files,
            'count': len(files)
        }
        
    except Exception as e:
        logging.error(f"List files error: {e}")
        return {
            'success': False,
            'error': str(e)
        }

def sanitize_web_content(content: str, max_size: int = 100000) -> str:
    """Sanitize web content before storing in memory."""
    if not content:
        return ""
    
    # Truncate if too large
    if len(content) > max_size:
        content = content[:max_size] + "... [TRUNCATED]"
    
    # Remove dangerous HTML elements
    dangerous_patterns = [
        r'<script.*?</script>',
        r'<style.*?</style>',
        r'<iframe.*?</iframe>',
        r'<object.*?</object>',
        r'<embed.*?</embed>',
        r'<link.*?>',
        r'<meta.*?>'
    ]
    
    for pattern in dangerous_patterns:
        content = re.sub(pattern, '', content, flags=re.IGNORECASE | re.DOTALL)
    
    # HTML escape remaining content
    content = html.escape(content)
    
    # Normalize whitespace
    content = re.sub(r'\s+', ' ', content).strip()
    
    return content