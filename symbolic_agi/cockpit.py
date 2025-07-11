# cockpit.py

import time
from typing import Any, Dict, Optional

import pandas as pd
import requests
import streamlit as st

# --- Configuration ---
API_BASE_URL = "http://127.0.0.1:8000"
STATUS_URL = f"{API_BASE_URL}/status"
GOALS_URL = f"{API_BASE_URL}/goals"
POLL_INTERVAL_SECONDS = 2

st.set_page_config(page_title="SymbolicAGI Cockpit", layout="wide")

st.title("🚀 SymbolicAGI Cockpit")

# --- Goal Submission Form ---
with st.form("new_goal_form", clear_on_submit=True):
    st.subheader("Submit a New Goal")
    goal_description = st.text_area("Goal Description:", height=100, placeholder="e.g., 'Analyze the latest AI research papers on arxiv and summarize the top 3 trends.'")
    submitted = st.form_submit_button("Submit Goal")

    if submitted:
        if not goal_description or len(goal_description) < 10:
            st.toast("🔥 Please enter a more detailed goal description.", icon="⚠️")
        else:
            try:
                response = requests.post(GOALS_URL, json={"description": goal_description})
                response.raise_for_status()
                st.toast(f"✅ Goal submitted successfully! (ID: {response.json()['id']})", icon="🎯")
            except requests.RequestException as e:
                st.toast(f"🔥 Failed to submit goal: {e}", icon="❌")

st.divider()

# --- UI Placeholders ---
header_ph = st.empty()
col1, col2, col3 = st.columns(3)

with col1:
    goal_manager_ph = st.empty()
with col2:
    agent_pool_ph = st.empty()
with col3:
    consciousness_ph = st.empty()

st.divider()
active_goal_ph = st.empty()

# --- Data Fetching & UI Rendering ---
def fetch_status() -> Optional[Dict[str, Any]]:
    try:
        response = requests.get(STATUS_URL, timeout=1.5)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return None

def update_ui(status: Dict[str, Any]):
    state = status.get("system_state", "UNKNOWN")
    if state == "ACTIVE":
        color = "green"
    elif state == "DEGRADED":
        color = "orange"
    else:
        color = "red"
    header_ph.header(f"System State: :{color}[{state}]")

    with goal_manager_ph.container(border=True):
        st.subheader("🎯 Goal Manager")
        st.metric("Active Goals", status.get("active_goals", 0))
        st.metric("Queued Goals", status.get("queued_goals", 0))
        st.metric("Completed Goals", status.get("completed_goals", 0))

    with agent_pool_ph.container(border=True):
        st.subheader("👥 Agent Pool")
        st.metric("Total Agents", status.get("total_agents", 0))
        # Placeholder for agent data
        st.info("Agent monitoring coming soon.")

    with consciousness_ph.container(border=True):
        st.subheader("🧠 Consciousness")
        # Placeholder for consciousness data
        st.info("Consciousness monitoring coming soon.")

    with active_goal_ph.container():
        st.subheader("Current Focus: Active Goal")
        goal = status.get("active_goal_details")
        if goal:
            with st.container(border=True):
                st.text_area("Description", value=goal.get('description'), height=100, disabled=True)
                c1, c2, c3 = st.columns(3)
                c1.metric("Status", goal.get('status', 'N/A').upper())
                c2.metric("Failures", goal.get('failures', 0))
                c3.text_input("Goal ID", value=goal.get('goal_id'), disabled=True)
        else:
            st.info("No active goal.")

# --- Main Application Loop ---
while True:
    latest_status = fetch_status()
    if latest_status:
        update_ui(latest_status)
    else:
        header_ph.header("System State: :red[DISCONNECTED]")
        goal_manager_ph.empty()
        agent_pool_ph.empty()
        consciousness_ph.empty()
        active_goal_ph.empty()

    time.sleep(POLL_INTERVAL_SECONDS)