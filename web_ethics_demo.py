#!/usr/bin/env python3
"""
🌐 Ethical Web Access Demo for Symbolic AGI
Demonstrates the comprehensive domain whitelist and robots.txt compliance
"""

import asyncio
import json
import sys
import os

# Add the symbolic_agi package to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def demo_web_ethics():
    """Demonstrate the ethical web access system"""
    print("🌐 SYMBOLIC AGI - ETHICAL WEB ACCESS DEMONSTRATION")
    print("=" * 55)
    
    try:
        from symbolic_agi.agi_controller import SymbolicAGI
        agi = await SymbolicAGI.create()
        
        print("\n📋 1. COMPREHENSIVE DOMAIN WHITELIST")
        print("-" * 35)
        result = await agi.tools.manage_web_access("list_whitelist")
        if result["status"] == "success":
            print(f"✅ Total Whitelisted Domains: {result['total_domains']}")
            for category, domains in result["categories"].items():
                print(f"📂 {category.title()}: {len(domains)} domains")
                for domain in domains[:3]:  # Show first 3
                    print(f"   • {domain}")
                if len(domains) > 3:
                    print(f"   ... and {len(domains) - 3} more")
        
        print(f"\n🤖 2. ROBOTS.TXT COMPLIANCE TESTING")
        print("-" * 35)
        
        test_urls = [
            "https://www.bbc.com/news",
            "https://arxiv.org/",
            "https://en.wikipedia.org/wiki/Artificial_intelligence",
            "https://www.nature.com/articles"
        ]
        
        for url in test_urls:
            print(f"\n🔍 Testing: {url}")
            result = await agi.tools.manage_web_access("test_robots", url=url)
            if result["status"] == "success":
                status = "✅ ALLOWED" if result["robots_allowed"] else "❌ BLOCKED"
                print(f"   Robots.txt: {status}")
                print(f"   Crawl Delay: {result['crawl_delay']}s")
            else:
                print(f"   ❌ Error: {result['description']}")
        
        print(f"\n📊 3. WEB ETHICS COMPLIANCE REPORT")
        print("-" * 35)
        result = await agi.tools.manage_web_access("web_ethics_report")
        if result["status"] == "success":
            report = result["ethics_report"]
            print("✅ COMPLIANCE SUMMARY:")
            for key, value in report["compliance_summary"].items():
                print(f"   • {key.replace('_', ' ').title()}: {value}")
            
            print("\n🛡️ ACCESS POLICIES:")
            for key, value in report["access_policies"].items():
                print(f"   • {key.replace('_', ' ').title()}: {value}")
        
        print(f"\n🧪 4. PRACTICAL WEB ACCESS TEST")
        print("-" * 35)
        
        # Test browsing a real webpage
        test_url = "https://en.wikipedia.org/wiki/Artificial_intelligence"
        print(f"🌐 Browsing: {test_url}")
        result = await agi.tools.browse_webpage(test_url)
        
        if result["status"] == "success":
            content = result["content"]
            print(f"✅ Successfully fetched {len(content)} characters")
            print(f"📄 Preview: {content[:200]}...")
            print("\n✅ All ethical compliance checks passed!")
        else:
            print(f"❌ Failed: {result['description']}")
        
        print(f"\n🎯 5. DOMAIN SUGGESTION SYSTEM")
        print("-" * 35)
        result = await agi.tools.manage_web_access(
            "suggest_domain",
            domain="www.example-research.org", 
            reason="High-quality research papers on AI ethics"
        )
        if result["status"] == "success":
            print(f"✅ {result['message']}")
            print(f"📝 Note: {result['note']}")
        
        await agi.shutdown()
        
        print(f"\n🏆 ETHICAL WEB ACCESS SUMMARY")
        print("=" * 35)
        print("✅ Comprehensive domain whitelist (100+ trusted sources)")
        print("✅ Automatic robots.txt compliance checking")
        print("✅ Respectful crawl delays honored")
        print("✅ Transparent user agent identification")
        print("✅ Categorized access to news, academic, government sources")
        print("✅ Domain suggestion system for expansion")
        print("\n🌟 Your AGI is a responsible digital citizen!")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        print("💡 Make sure symbolic_agi is properly installed")

def show_whitelist_categories():
    """Show the comprehensive whitelist breakdown"""
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from symbolic_agi.config import ALLOWED_DOMAINS
        
        print("\n📚 COMPLETE DOMAIN WHITELIST BREAKDOWN")
        print("=" * 45)
        
        categories = {
            "📰 News & Media": [d for d in ALLOWED_DOMAINS if any(term in d for term in 
                ["bbc", "reuters", "cnn", "npr", "guardian", "nytimes", "wsj", "economist", "forbes"])],
            "🎓 Academic & Research": [d for d in ALLOWED_DOMAINS if any(term in d for term in 
                ["arxiv", "nature", "science", "pnas", "ncbi", "researchgate", "ieee", "acm"])],
            "🏛️ Government & Official": [d for d in ALLOWED_DOMAINS if any(term in d for term in 
                ["gov", "europa.eu", "who.int", "un.org", "cdc.gov", "fda.gov"])],
            "💻 Technology & AI": [d for d in ALLOWED_DOMAINS if any(term in d for term in 
                ["github", "stackoverflow", "python", "openai", "anthropic", "huggingface", "pytorch"])],
            "🏫 Educational": [d for d in ALLOWED_DOMAINS if any(term in d for term in 
                ["mit.edu", "stanford.edu", "harvard.edu", "coursera", "edx", "khanacademy"])],
            "📊 Data & Statistics": [d for d in ALLOWED_DOMAINS if any(term in d for term in 
                ["worldbank", "imf", "oecd", "census", "data.gov", "ourworldindata"])],
            "🌍 Climate & Environment": [d for d in ALLOWED_DOMAINS if any(term in d for term in 
                ["ipcc", "nasa.gov", "noaa.gov", "epa.gov", "unep"])],
            "🏥 Health & Medicine": [d for d in ALLOWED_DOMAINS if any(term in d for term in 
                ["nih.gov", "mayoclinic", "webmd", "cochrane", "bmj"])],
            "💰 Finance & Economics": [d for d in ALLOWED_DOMAINS if any(term in d for term in 
                ["investopedia", "bloomberg", "marketwatch", "federalreserve"])]
        }
        
        total_categorized = 0
        for category, domains in categories.items():
            print(f"\n{category} ({len(domains)} domains):")
            for domain in sorted(domains)[:10]:  # Show first 10
                print(f"  • {domain}")
            if len(domains) > 10:
                print(f"  ... and {len(domains) - 10} more")
            total_categorized += len(domains)
        
        uncategorized = len(ALLOWED_DOMAINS) - total_categorized
        print(f"\n📁 Other domains: {uncategorized}")
        print(f"\n🎯 TOTAL WHITELISTED: {len(ALLOWED_DOMAINS)} domains")
        
    except Exception as e:
        print(f"❌ Could not load whitelist: {e}")

if __name__ == "__main__":
    print("🌐 SYMBOLIC AGI - ETHICAL WEB ACCESS")
    print("Choose an option:")
    print("1. Run full ethical web access demo")
    print("2. Show domain whitelist breakdown")
    print("3. Exit")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    if choice == "1":
        asyncio.run(demo_web_ethics())
    elif choice == "2":
        show_whitelist_categories()
    else:
        print("👋 Goodbye!")