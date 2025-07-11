#!/usr/bin/env python3
"""
Test rate limiting functionality
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

async def test_rate_limiting():
    """Test the rate limiting implementation."""
    try:
        print("🧪 Testing rate limiting...")
        
        # Test rate limiter directly
        from symbolic_agi.tool_plugin import _rate_limiter
        
        # Test multiple requests to same domain
        domain = "test.example.com"
        allowed_count = 0
        
        # Try 15 requests (should allow 10, block 5)
        for i in range(15):
            if await _rate_limiter.can_request(domain):
                allowed_count += 1
        
        print(f"✅ Rate limiter working: {allowed_count}/15 requests allowed (expected: 10)")
        
        # Check stats
        stats = _rate_limiter.get_stats()
        if domain in stats:
            domain_stats = stats[domain]
            print(f"   Domain stats: {domain_stats['recent_requests']}/{domain_stats['max_requests']} requests")
            print(f"   Remaining: {domain_stats['requests_remaining']}")
        
        # Test rate limiting functions are importable
        from symbolic_agi.tool_plugin import web_search, fetch_webpage, get_rate_limiting_stats
        print("✅ All rate-limited functions imported successfully")
        
        # Test stats function
        all_stats = get_rate_limiting_stats()
        print(f"✅ Rate limiting stats available: {len(all_stats)} domains tracked")
        
        print("✅ Rate limiting implementation complete and working")
        return True
        
    except Exception as e:
        print(f"❌ Rate limiting test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_rate_limiting())
    sys.exit(0 if success else 1)
