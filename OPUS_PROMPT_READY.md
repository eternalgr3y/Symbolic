I need you to enhance a security-focused browser agent tool plugin for a Symbolic AGI system. This is production code that handles web requests, file operations, and security validation.

## Current Code Status
The file is 1051 lines and contains a comprehensive browser agent with:
- SecurityValidator class with URL validation, content analysis, malicious signature detection
- RateLimiter class with per-domain rate limiting (5 requests/minute)  
- SecurityLogger class for security event tracking
- Web functions: web_search(), fetch_webpage() with full security validation
- File operations: write_file(), read_file(), list_files() with path validation
- Content sanitization supporting up to 1MB per item

## Enhancement Requests

### 1. Add Security Status Function
Please add this function after the SecurityLogger class:

```python
@register_innate_action
async def get_security_status(agi: "SymbolicAGI") -> Dict[str, Any]:
    """Get comprehensive security status and monitoring data."""
    # Return security event summary, rate limiting status, system health
```

### 2. Add Data Export Function  
Please add this function with the other file operations:

```python
@register_innate_action
async def export_workspace_data(agi: "SymbolicAGI", include_content: bool = True) -> Dict[str, Any]:
    """Export all workspace data in a structured format."""
    # Export files as JSON with metadata, security scan results, handle large datasets
```

### 3. Optimize Content Processing
The `sanitize_web_content()` function (line 1017) and `_process_webpage_content()` function (line 751) need:
- Better memory management for 1MB+ content
- Progressive loading capabilities  
- Enhanced error recovery

### 4. Add Retry Mechanisms
Add retry logic to web requests with exponential backoff and circuit breaker patterns.

### 5. Improve Error Handling
Enhance error handling throughout with detailed diagnostics and recovery suggestions.

## Important Requirements
- Maintain all existing security features
- Keep async/await patterns consistent
- Preserve the SecurityLogger event logging
- Ensure rate limiting continues working
- All new functions must be thread-safe
- Memory usage should stay reasonable with large content
- Add proper error handling and logging

## Code to Enhance
Here's the current tool_plugin.py file:

[PASTE THE COMPLETE FILE CONTENT HERE]

Please provide the enhanced code with:
1. The requested new functions implemented
2. Optimizations to existing functions  
3. Brief explanation of improvements made
4. Any new dependencies needed

Focus on security, reliability, and performance. This is production code handling potentially sensitive data.
