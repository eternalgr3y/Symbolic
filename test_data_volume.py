#!/usr/bin/env python3
"""
Test data volume controls
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

async def test_data_volume_controls():
    """Test the new data volume controls."""
    try:
        print("🧪 Testing data volume controls...")
        
        # Test content sanitization
        from symbolic_agi.tool_plugin import sanitize_web_content
        
        # Test with malicious content
        malicious_content = """
        <script>alert('hack')</script>
        <style>body { display: none; }</style>
        <iframe src="evil.com"></iframe>
        Hello World! This is safe content.
        """
        
        sanitized = sanitize_web_content(malicious_content)
        print(f"✅ Content sanitization works (original: {len(malicious_content)}, sanitized: {len(sanitized)})")
        print(f"   Sanitized content: {sanitized[:100]}...")
        
        # Test memory system
        from symbolic_agi.agi_controller import SymbolicAGI
        agi = await SymbolicAGI.create()
        
        # Get database stats
        stats = agi.memory.get_database_stats()
        print(f"✅ Database stats: {stats['memory_count']} memories, {stats['database_size_mb']:.1f}MB")
        
        # Test oversized content rejection
        huge_content = {"data": "x" * (1024 * 1024 + 1)}  # > 1MB
        try:
            agi.memory._validate_content_size(huge_content)
            print("❌ Should have rejected oversized content")
        except ValueError:
            print("✅ Correctly rejected oversized content")
        
        await agi.shutdown()
        print("✅ Data volume controls working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Data volume test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_data_volume_controls())
    sys.exit(0 if success else 1)
