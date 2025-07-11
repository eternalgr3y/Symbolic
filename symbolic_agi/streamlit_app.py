import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

import httpx
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from streamlit_autorefresh import st_autorefresh

# Configure page
st.set_page_config(
    page_title="SymbolicAGI Control Center",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .stMetric {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 5px;
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        padding: 10px;
        border-radius: 5px;
    }
    .error-box {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        padding: 10px;
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'api_client' not in st.session_state:
    st.session_state.api_client = httpx.AsyncClient(base_url="http://localhost:8000")
if 'auto_refresh' not in st.session_state:
    st.session_state.auto_refresh = False
if 'refresh_rate' not in st.session_state:
    st.session_state.refresh_rate = 5000  # milliseconds

# Auto-refresh
if st.session_state.auto_refresh:
    st_autorefresh(interval=st.session_state.refresh_rate, key="datarefresh")

async def fetch_agi_status():
    """Fetch current AGI status from the API."""
    try:
        response = await st.session_state.api_client.get("/api/status")
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        st.error(f"Failed to fetch AGI status: {e}")
    return None

async def fetch_memories(memory_type: Optional[str] = None, limit: int = 50):
    """Fetch memories from the AGI."""
    params = {"limit": limit}
    if memory_type:
        params["type"] = memory_type
    
    try:
        response = await st.session_state.api_client.get("/api/memory/list", params=params)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        st.error(f"Failed to fetch memories: {e}")
    return []

async def create_goal(description: str, priority: str):
    """Create a new goal."""
    try:
        response = await st.session_state.api_client.post(
            "/api/goals/create",
            json={"description": description, "priority": priority}
        )
        if response.status_code == 200:
            return True, response.json()
        else:
            return False, response.text
    except Exception as e:
        return False, str(e)

async def fetch_goals():
    """Fetch all goals."""
    try:
        response = await st.session_state.api_client.get("/api/goals/list")
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        st.error(f"Failed to fetch goals: {e}")
    return []

async def cancel_goal(goal_id: str):
    """Cancel a goal."""
    try:
        response = await st.session_state.api_client.post(f"/api/goals/{goal_id}/cancel")
        return response.status_code == 200
    except:
        return False

async def send_message(content: str):
    """Send a message to the AGI."""
    try:
        response = await st.session_state.api_client.post(
            "/api/interact",
            json={"content": content}
        )
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        st.error(f"Failed to send message: {e}")
    return None

def main():
    """Main Streamlit application."""
    st.title("🧠 SymbolicAGI Control Center")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Controls")
        
        # Auto-refresh toggle
        st.session_state.auto_refresh = st.checkbox(
            "Auto-refresh",
            value=st.session_state.auto_refresh
        )
        
        if st.session_state.auto_refresh:
            st.session_state.refresh_rate = st.slider(
                "Refresh rate (seconds)",
                min_value=1,
                max_value=30,
                value=st.session_state.refresh_rate // 1000
            ) * 1000
        
        # Manual refresh
        if st.button("🔄 Refresh Now"):
            st.rerun()
        
        st.divider()
        
        # Quick Actions
        st.header("🚀 Quick Actions")
        
        if st.button("🧹 Clear Old Memories"):
            # TODO: Implement memory cleanup
            st.info("Memory cleanup triggered")
        
        if st.button("💾 Export Memories"):
            # TODO: Implement memory export
            st.info("Memory export started")
    
    # Main content area with tabs
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 Dashboard",
        "🎯 Goals",
        "💬 Interact",
        "🧠 Memory",
        "👥 Agents",
        "📈 Metrics"
    ])
    
    # Dashboard Tab
    with tab1:
        # Fetch status
        status = asyncio.run(fetch_agi_status())
        
        if status:
            # Metrics row
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    "🔋 Cognitive Energy",
                    f"{status['energy']['current']}/{status['energy']['max']}",
                    f"{status['energy']['current'] / status['energy']['max'] * 100:.0f}%"
                )
            
            with col2:
                st.metric(
                    "🎯 Active Goals",
                    status['goals']['active'],
                    f"Total: {status['goals']['total']}"
                )
            
            with col3:
                st.metric(
                    "🧠 Memory Entries",
                    status['memory']['total_entries'],
                    f"Recent: {status['memory']['recent_entries']}"
                )
            
            with col4:
                st.metric(
                    "👥 Active Agents",
                    status['agents']['active'],
                    f"Total: {status['agents']['total']}"
                )
            
            # Consciousness State
            st.subheader("🧘 Consciousness State")
            col1, col2 = st.columns(2)
            
            with col1:
                # Emotional state visualization
                emotion_data = status.get('consciousness', {})
                if emotion_data:
                    fig = go.Figure(data=[
                        go.Bar(
                            x=['Valence', 'Intensity'],
                            y=[emotion_data.get('valence', 0), emotion_data.get('intensity', 0)],
                            marker_color=['lightblue', 'lightcoral']
                        )
                    ])
                    fig.update_layout(
                        title=f"Emotional State: {emotion_data.get('primary', 'neutral')}",
                        yaxis=dict(range=[-1, 1]),
                        height=300
                    )
                    st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.info(f"**Attention Focus**: {emotion_data.get('attention_focus', 'None')}")
                st.info(f"**Awareness Level**: {emotion_data.get('awareness_level', 0):.2f}")
                
                # Recent thoughts
                thoughts = emotion_data.get('recent_thoughts', [])
                if thoughts:
                    st.write("**Recent Thoughts:**")
                    for thought in thoughts[-3:]:
                        st.write(f"• {thought}")
            
            # System Health
            st.subheader("🏥 System Health")
            health_metrics = status.get('health', {})
            
            # Create health indicators
            health_cols = st.columns(5)
            health_indicators = [
                ("API", health_metrics.get('api_responsive', False)),
                ("Memory", health_metrics.get('memory_healthy', False)),
                ("Redis", health_metrics.get('redis_connected', False)),
                ("Execution", health_metrics.get('execution_running', False)),
                ("Meta-cognition", health_metrics.get('meta_cognition_active', False))
            ]
            
            for col, (name, healthy) in zip(health_cols, health_indicators):
                with col:
                    if healthy:
                        st.success(f"✅ {name}")
                    else:
                        st.error(f"❌ {name}")
        
        else:
            st.error("Unable to connect to AGI system")
    
    # Goals Tab
    with tab2:
        st.header("🎯 Goal Management")
        
        # Create new goal
        with st.expander("➕ Create New Goal", expanded=True):
            goal_description = st.text_area(
                "Goal Description",
                placeholder="Enter a clear, actionable goal for the AGI..."
            )
            
            col1, col2 = st.columns([3, 1])
            with col1:
                priority = st.select_slider(
                    "Priority",
                    options=["LOW", "MEDIUM", "HIGH", "CRITICAL"],
                    value="MEDIUM"
                )
            
            with col2:
                if st.button("Create Goal", type="primary"):
                    if goal_description:
                        success, result = asyncio.run(create_goal(goal_description, priority))
                        if success:
                            st.success(f"Goal created successfully! ID: {result.get('goal_id')}")
                            st.rerun()
                        else:
                            st.error(f"Failed to create goal: {result}")
                    else:
                        st.warning("Please enter a goal description")
        
        # List existing goals
        goals = asyncio.run(fetch_goals())
        
        if goals:
            # Group goals by status
            active_goals = [g for g in goals if g['status'] in ['PENDING', 'ACTIVE']]
            completed_goals = [g for g in goals if g['status'] == 'COMPLETED']
            failed_goals = [g for g in goals if g['status'] == 'FAILED']
            
            # Active Goals
            if active_goals:
                st.subheader("🔄 Active Goals")
                for goal in active_goals:
                    with st.container():
                        col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                        
                        with col1:
                            st.write(f"**{goal['description']}**")
                            st.caption(f"ID: {goal['id']} | Created: {goal['created_at']}")
                        
                        with col2:
                            priority_colors = {
                                "LOW": "🟢",
                                "MEDIUM": "🟡", 
                                "HIGH": "🟠",
                                "CRITICAL": "🔴"
                            }
                            st.write(f"{priority_colors.get(goal['priority'], '⚪')} {goal['priority']}")
                        
                        with col3:
                            status_badge = {
                                "PENDING": "⏳",
                                "ACTIVE": "🔄"
                            }
                            st.write(f"{status_badge.get(goal['status'], '❓')} {goal['status']}")
                        
                        with col4:
                            if st.button("Cancel", key=f"cancel_{goal['id']}"):
                                if asyncio.run(cancel_goal(goal['id'])):
                                    st.success("Goal cancelled")
                                    st.rerun()
                                else:
                                    st.error("Failed to cancel goal")
                        
                        st.divider()
            
            # Completed Goals
            if completed_goals:
                with st.expander(f"✅ Completed Goals ({len(completed_goals)})"):
                    for goal in completed_goals[:5]:
                        st.success(f"**{goal['description']}**")
                        st.caption(f"Completed: {goal.get('completed_at', 'N/A')}")
            
            # Failed Goals
            if failed_goals:
                with st.expander(f"❌ Failed Goals ({len(failed_goals)})"):
                    for goal in failed_goals[:5]:
                        st.error(f"**{goal['description']}**")
                        if 'metadata' in goal and 'failure_reason' in goal['metadata']:
                            st.caption(f"Reason: {goal['metadata']['failure_reason']}")
    
    # Interact Tab
    with tab3:
        st.header("💬 Interact with AGI")
        
        # Chat interface
        if 'chat_history' not in st.session_state:
            st.session_state.chat_history = []
        
        # Display chat history
        chat_container = st.container()
        with chat_container:
            for message in st.session_state.chat_history:
                if message['role'] == 'user':
                    st.chat_message("user").write(message['content'])
                else:
                    st.chat_message("assistant").write(message['content'])
        
        # Input area
        user_input = st.chat_input("Send a message to the AGI...")
        
        if user_input:
            # Add user message to history
            st.session_state.chat_history.append({
                'role': 'user',
                'content': user_input,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
            # Send to AGI
            response = asyncio.run(send_message(user_input))
            
            if response:
                # Add AGI response to history
                st.session_state.chat_history.append({
                    'role': 'assistant',
                    'content': response.get('response', 'No response'),
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
                
                # Show reasoning steps if available
                if 'reasoning_steps' in response:
                    with st.expander("🤔 Reasoning Steps"):
                        for step in response['reasoning_steps']:
                            st.write(f"• {step}")
            
            st.rerun()
    
    # Memory Tab
    with tab4:
        st.header("🧠 Memory System")
        
        # Memory filters
        col1, col2, col3 = st.columns(3)
        
        with col1:
            memory_type = st.selectbox(
                "Memory Type",
                ["All", "DECISION", "ACTION", "OBSERVATION", "REFLECTION", "ERROR", "GOAL", "KNOWLEDGE"]
            )
        
        with col2:
            limit = st.number_input("Limit", min_value=10, max_value=200, value=50)
        
        with col3:
            if st.button("Refresh Memories"):
                st.rerun()
        
        # Fetch and display memories
        memories = asyncio.run(fetch_memories(
            memory_type if memory_type != "All" else None,
            limit
        ))
        
        if memories:
            # Memory statistics
            st.subheader("📊 Memory Statistics")
            
            # Create memory type distribution
            memory_types = {}
            importance_values = []
            
            for mem in memories:
                mem_type = mem.get('type', 'Unknown')
                memory_types[mem_type] = memory_types.get(mem_type, 0) + 1
                importance_values.append(mem.get('importance', 0))
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Memory type pie chart
                fig = px.pie(
                    values=list(memory_types.values()),
                    names=list(memory_types.keys()),
                    title="Memory Type Distribution"
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                # Importance histogram
                fig = px.histogram(
                    x=importance_values,
                    nbins=20,
                    title="Memory Importance Distribution",
                    labels={'x': 'Importance', 'y': 'Count'}
                )
                st.plotly_chart(fig, use_container_width=True)
            
            # Memory list
            st.subheader("📝 Recent Memories")
            
            for mem in memories[:20]:
                with st.expander(
                    f"{mem.get('type', 'Unknown')} - {mem.get('id', 'No ID')[:8]}... "
                    f"(Importance: {mem.get('importance', 0):.2f})"
                ):
                    st.json(mem.get('content', {}))
                    st.caption(f"Created: {mem.get('timestamp', 'Unknown')}")
    
    # Agents Tab
    with tab5:
        st.header("👥 Agent Pool")
        
        # Fetch agents status
        status = asyncio.run(fetch_agi_status())
        
        if status and 'agents' in status:
            agents = status['agents'].get('pool', [])
            
            if agents:
                # Agent overview
                st.subheader(f"Total Agents: {len(agents)}")
                
                # Agent grid
                cols = st.columns(3)
                
                for idx, agent in enumerate(agents):
                    with cols[idx % 3]:
                        with st.container():
                            st.write(f"**{agent['name']}**")
                            st.write(f"🎭 Persona: {agent['persona']}")
                            st.write(f"📊 Trust Score: {agent['trust_score']:.2f}")
                            st.write(f"✅ Tasks: {agent['completed_tasks']}")
                            
                            # Status indicator
                            if agent.get('busy', False):
                                st.warning("🔄 Busy")
                            else:
                                st.success("✅ Available")
                            
                            st.divider()
            else:
                st.info("No agents in the pool")
        
        # Create new agent
        with st.expander("➕ Create New Agent"):
            col1, col2 = st.columns(2)
            
            with col1:
                agent_name = st.text_input("Agent Name")
            
            with col2:
                persona = st.selectbox(
                    "Persona",
                    ["research", "coding", "qa", "creative", "analytical"]
                )
            
            if st.button("Create Agent"):
                # TODO: Implement agent creation API
                st.info(f"Creating agent: {agent_name} with {persona} persona")
    
    # Metrics Tab
    with tab6:
        st.header("📈 System Metrics")
        
        # Fetch metrics
        status = asyncio.run(fetch_agi_status())
        
        if status and 'metrics' in status:
            metrics = status['metrics']
            
            # Performance metrics
            st.subheader("⚡ Performance Metrics")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    "Goal Success Rate",
                    f"{metrics.get('goal_success_rate', 0) * 100:.1f}%"
                )
            
            with col2:
                st.metric(
                    "Avg Goal Time",
                    f"{metrics.get('average_goal_time', 0):.1f}s"
                )
            
            with col3:
                st.metric(
                    "Memory Efficiency",
                    f"{metrics.get('memory_efficiency', 0) * 100:.1f}%"
                )
            
            with col4:
                st.metric(
                    "Energy Efficiency",
                    f"{metrics.get('energy_efficiency', 0) * 100:.1f}%"
                )
            
            # Token usage
            if 'token_usage' in metrics:
                st.subheader("🎫 Token Usage")
                
                token_data = metrics['token_usage']
                
                # Create token usage chart
                fig = go.Figure(data=[
                    go.Bar(
                        x=list(token_data.keys()),
                        y=list(token_data.values()),
                        text=list(token_data.values()),
                        textposition='auto',
                    )
                ])
                fig.update_layout(
                    title="Token Usage by Model",
                    xaxis_title="Model",
                    yaxis_title="Tokens",
                    height=400
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # Cost estimation
                if 'estimated_cost' in metrics:
                    st.info(f"💰 Estimated Cost: ${metrics['estimated_cost']:.2f}")
            
            # Error tracking
            if 'errors' in metrics:
                st.subheader("⚠️ Error Tracking")
                
                error_data = metrics['errors']
                if error_data:
                    df_errors = pd.DataFrame(
                        error_data.items(),
                        columns=['Error Type', 'Count']
                    )
                    st.dataframe(df_errors, use_container_width=True)
                else:
                    st.success("No errors recorded")

if __name__ == "__main__":
    main()