# SQLite Security Recommendations for Web Browsing AGI

## Current Security Status: ✅ GOOD
The codebase uses parameterized queries and proper input sanitization.

## Recommended Enhancements:

### 1. Database File Security
```python
# Set restrictive file permissions on SQLite database
import os
import stat

def secure_database_file(db_path: str):
    """Set secure permissions on database file"""
    if os.path.exists(db_path):
        # Owner read/write only (600)
        os.chmod(db_path, stat.S_IRUSR | stat.S_IWUSR)
```

### 2. Content Size Limits
```python
# Add to symbolic_memory.py
MAX_CONTENT_SIZE = 1024 * 1024  # 1MB limit per memory entry

async def add_memory(self, memory: MemoryEntryModel) -> None:
    content_str = json.dumps(memory.content)
    if len(content_str) > MAX_CONTENT_SIZE:
        raise ValueError(f"Memory content too large: {len(content_str)} bytes")
    # ... rest of method
```

### 3. Web Content Sanitization
```python
# Add to tool_plugin.py
import html
import re

def sanitize_web_content(content: str) -> str:
    """Sanitize web content before storing"""
    # Remove scripts and dangerous tags
    content = re.sub(r'<script.*?</script>', '', content, flags=re.IGNORECASE | re.DOTALL)
    content = re.sub(r'<style.*?</style>', '', content, flags=re.IGNORECASE | re.DOTALL)
    # HTML escape
    content = html.escape(content)
    return content
```

### 4. Database Size Monitoring
```python
# Add to symbolic_memory.py
async def check_database_size(self) -> None:
    """Monitor database size and rotate if needed"""
    if os.path.exists(self._db_path):
        size_mb = os.path.getsize(self._db_path) / (1024 * 1024)
        if size_mb > 500:  # 500MB limit
            await self._rotate_database()
```

### 5. Memory Encryption (Optional)
```python
# For sensitive content, consider encryption
from cryptography.fernet import Fernet

class EncryptedMemory:
    def __init__(self):
        self.key = Fernet.generate_key()
        self.cipher = Fernet(self.key)
    
    def encrypt_content(self, content: str) -> bytes:
        return self.cipher.encrypt(content.encode())
    
    def decrypt_content(self, encrypted: bytes) -> str:
        return self.cipher.decrypt(encrypted).decode()
```

## Web Browsing Security Checklist:

- ✅ Domain whitelist enforcement
- ✅ URL validation
- ✅ Robots.txt compliance
- ⚠️ Add rate limiting
- ⚠️ Add content type validation
- ⚠️ Add virus scanning for downloads
- ⚠️ Add HTTPS-only enforcement

## Implementation Priority:
1. **High**: Database file permissions
2. **Medium**: Content size limits
3. **Medium**: Web content sanitization
4. **Low**: Database size monitoring
5. **Optional**: Memory encryption
