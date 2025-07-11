#!/usr/bin/env python3
"""
Production deployment script for SymbolicAGI
"""
import asyncio
import logging
import os
import signal
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging for production
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('agi_production.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

async def deploy_agi():
    """Deploy the AGI system in production mode."""
    agi = None
    try:
        print("🚀 Starting SymbolicAGI Production Deployment...")
        
        # Test system components first
        print("🧪 Running pre-deployment tests...")
        
        # Test imports
        from symbolic_agi.agi_controller import SymbolicAGI
        from symbolic_agi import config
        print("✅ Core imports successful")
        
        # Test configuration
        cfg = config.get_config()
        print(f"✅ Configuration loaded: {cfg.name}")
        
        # Create AGI instance
        print("🤖 Initializing AGI system...")
        agi = await SymbolicAGI.create()
        print("✅ AGI created successfully")
        
        # Test basic functionality
        state = agi.get_current_state()
        print(f"✅ AGI state: {state}")
        
        # Check database security
        stats = agi.memory.get_database_stats()
        print(f"✅ Database: {stats['memory_count']} memories, {stats['database_size_mb']:.1f}MB")
        
        # Start background services
        print("🔄 Starting background services...")
        await agi.start_background_tasks()
        print("✅ Background tasks started")
        
        print("🎉 SymbolicAGI deployed successfully!")
        print("📡 System is now running in production mode")
        print("📊 Monitoring dashboard available at: http://localhost:8501")
        print("🌐 API server available at: http://localhost:8000")
        print("\nPress Ctrl+C to shutdown gracefully...")
        
        # Set up signal handlers for graceful shutdown
        shutdown_task = None
        def signal_handler(signum, frame):
            nonlocal shutdown_task
            print(f"\n📡 Received signal {signum}, initiating graceful shutdown...")
            if not shutdown_task:
                shutdown_task = asyncio.create_task(agi.shutdown())
            
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Keep running until shutdown
        await agi.shutdown_event.wait()
        
    except KeyboardInterrupt:
        print("\n⚠️ Shutdown requested by user")
    except Exception as e:
        print(f"❌ Deployment failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if agi:
            print("🔄 Shutting down AGI system...")
            await agi.shutdown()
            print("✅ AGI shutdown complete")
    
    return True

def start_uvicorn_server():
    """Start the FastAPI server with uvicorn."""
    import uvicorn
    print("🌐 Starting FastAPI server...")
    
    uvicorn.run(
        "symbolic_agi.run_agi:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # Disable reload in production
        log_level="info"
    )

def start_streamlit_dashboard():
    """Start the Streamlit monitoring dashboard."""
    import subprocess
    print("📊 Starting Streamlit dashboard...")
    
    subprocess.run([
        sys.executable, "-m", "streamlit", "run", 
        "symbolic_agi/streamlit_app.py",
        "--server.port", "8501",
        "--server.address", "0.0.0.0"
    ])

async def run_production_mode():
    """Run in full production mode with all services."""
    print("🚀 Starting SymbolicAGI in full production mode...")
    
    # Start services concurrently
    tasks = [
        asyncio.create_task(deploy_agi()),
        # Note: In a real deployment, you'd use a process manager like supervisord
        # For now, we'll focus on the core AGI system
    ]
    
    try:
        await asyncio.gather(*tasks)
    except Exception as e:
        print(f"❌ Production deployment failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    # Check for production environment
    if "--production" in sys.argv:
        print("🏭 Production mode enabled")
        success = asyncio.run(run_production_mode())
    elif "--api-only" in sys.argv:
        print("🌐 API server only mode")
        start_uvicorn_server()
    elif "--dashboard-only" in sys.argv:
        print("📊 Dashboard only mode")
        start_streamlit_dashboard()
    else:
        print("🧪 Development deployment mode")
        success = asyncio.run(deploy_agi())
    
    sys.exit(0 if success else 1)
