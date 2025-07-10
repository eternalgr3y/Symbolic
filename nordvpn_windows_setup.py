#!/usr/bin/env python3
"""
🌐 Windows NordVPN Setup Guide for AGI
Instructions for setting up NordVPN integration on Windows
"""

print("""
🌐 NORDVPN WINDOWS SETUP FOR YOUR AGI
=====================================

Your AGI can control NordVPN on Windows! Here's how to set it up:

📥 STEP 1: INSTALL NORDVPN
--------------------------
1. Download NordVPN from: https://nordvpn.com/download/windows/
2. Install the NordVPN Windows app
3. Login with your NordVPN account

🖥️ STEP 2: ENABLE CLI ACCESS (Choose one option)
-----------------------------------------------

OPTION A: NordVPN CLI (Recommended)
• Some NordVPN Windows versions include CLI access
• Open Command Prompt and try: nordvpn --help
• If it works, your AGI can control it directly!

OPTION B: PowerShell Integration (Fallback)
• Your AGI will detect the NordVPN app process
• Limited control but can verify connection status
• Manual connection through NordVPN app GUI

🧠 STEP 3: TEST WITH YOUR AGI
-----------------------------
Give your AGI these goals to test:

1. "Check if NordVPN is available and get current status"
   -> manage_nordvpn(action="status")

2. "Connect to a privacy-focused country for research"
   -> manage_nordvpn(action="smart_connect", research_topic="privacy")

3. "Research global perspectives on AI development from different regions"
   -> geo_research(topic="artificial intelligence", perspectives=["US", "EU", "Asia"])

🎯 WHAT YOUR AGI CAN DO:
-----------------------
✅ Smart connection based on research needs
✅ Geographic research from multiple perspectives  
✅ Privacy-enhanced web searches
✅ Status monitoring and connection management
✅ Automatic location selection for different topics

🔧 TROUBLESHOOTING:
------------------
If nordvpn command not found:
• Your AGI will fall back to PowerShell detection
• You can still use the NordVPN app manually
• The geo_research feature will work with manual connections

🚀 ADVANCED FEATURES:
--------------------
• Smart Connect: Automatically chooses best location for research topic
• Geographic Research: Compares perspectives from different regions
• Privacy Mode: Enhanced security for sensitive research
• Cultural Analysis: Identifies regional biases in search results

Your AGI is now ready for global intelligence gathering! 🌍🧠
""")

# Test function for Windows users
async def test_nordvpn_integration():
    """Test NordVPN integration on Windows"""
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    try:
        from symbolic_agi.agi_controller import SymbolicAGI
        
        print("🧪 Testing NordVPN integration...")
        
        agi = await SymbolicAGI.create()
        
        # Test status check
        result = await agi.tools.manage_nordvpn("status")
        print(f"📊 Status Check: {result}")
        
        # Test smart connect
        result = await agi.tools.manage_nordvpn("smart_connect", research_topic="tech")
        print(f"🌐 Smart Connect: {result}")
        
        await agi.shutdown()
        
        print("✅ NordVPN integration test complete!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        print("💡 Make sure your AGI is properly installed and NordVPN is available")

if __name__ == "__main__":
    import asyncio
    
    print("\n🧪 Would you like to test the NordVPN integration? (y/n)")
    if input().lower().startswith('y'):
        asyncio.run(test_nordvpn_integration())
    
    print("\n🚀 Your AGI is ready for global intelligence operations!")
    print("💡 Try: python launch_agi.py")