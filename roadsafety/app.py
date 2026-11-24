"""
GuardianNodes RoadSoS — Next-Gen Intelligent Road Accident Emergency Response Platform
======================================================================================
Production-grade Computer-Aided Dispatch (CAD) & Emergency Operations Command Center
Delhi NCR Node · Palantir-Style Tactical Interface · Persistent SQLite Relational DB
"""

from __future__ import annotations

import datetime
import json
import logging
import os
import random
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Path configuration
APP_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(APP_DIR))

from modules.database import get_db_connection, init_database
from modules.auth import (
    authenticate_user,
    has_permission,
    log_audit_action,
    get_all_users,
    get_recent_audit_logs,
)
from modules.incident_service import (
    create_incident,
    get_all_incidents,
    get_incident_by_id,
    update_incident_status,
    get_incident_kpis,
)
from modules.fleet_service import (
    get_all_vehicles,
    get_available_vehicles,
    dispatch_vehicle,
    update_vehicle_status,
    cancel_dispatch,
    get_dispatch_history,
)
from modules.hospital_service import (
    get_all_hospitals,
    reserve_hospital_bed,
    update_patient_handover,
    get_active_reservations,
)
from modules.triage_engine import IntelligentTriageEngine, CANDIDATE_LABELS
from modules.routing_engine import GraphRoutingEngine, VEHICLE_PROFILES, REGIONAL_HOSPITALS
from modules.mesh_simulator import MeshProtocolSimulator, generate_cap_payload

logger = logging.getLogger("roadsafety.app")

# ---------------------------------------------------------------------------
# Streamlit Page Setup
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="GuardianNodes RoadSoS | Command CAD",
    page_icon="🚨",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Custom CSS — Palantir-Style Tactical Dark Command Interface
# ---------------------------------------------------------------------------
CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;700&display=swap');

:root {
    --bg-base:        #060a12;
    --bg-panel:       #0c1322;
    --bg-card:        rgba(15, 24, 42, 0.88);
    --border-subtle:  rgba(255, 255, 255, 0.08);
    --border-active:  rgba(0, 210, 255, 0.35);
    --accent-cyan:    #00d2ff;
    --accent-blue:    #3b82f6;
    --accent-red:     #ef4444;
    --accent-orange:  #f97316;
    --accent-green:   #10b981;
    --accent-amber:   #f59e0b;
    --accent-purple:  #a855f7;
    --text-primary:   #f1f5f9;
    --text-secondary: #94a3b8;
    --text-dim:       #475569;
}

* { box-sizing: border-box; }

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    background: var(--bg-base) !important;
    color: var(--text-primary) !important;
}

#MainMenu, footer, header { visibility: hidden; }
.stDeployButton { display: none; }

.main .block-container {
    padding: 0.8rem 1.8rem 2.5rem !important;
    max-width: 100% !important;
}

/* === TOP COMMAND HEADER === */
.cad-header {
    background: linear-gradient(90deg, #090f1d 0%, #0d172c 50%, #090f1d 100%);
    border: 1px solid var(--border-subtle);
    border-radius: 12px;
    padding: 0.9rem 1.6rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;
    box-shadow: 0 4px 20px rgba(0,0,0,0.5);
}
.cad-brand {
    display: flex;
    align-items: center;
    gap: 12px;
}
.cad-title {
    font-size: 1.45rem;
    font-weight: 900;
    letter-spacing: -0.02em;
    background: linear-gradient(90deg, #ff4757, #ff6b35, #00d2ff);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin: 0;
}
.cad-subtitle {
    font-size: 0.72rem;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.12em;
    font-weight: 600;
}
.cad-meta {
    display: flex;
    align-items: center;
    gap: 15px;
}
.status-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(16, 185, 129, 0.12);
    border: 1px solid rgba(16, 185, 129, 0.35);
    color: #10b981;
    font-size: 0.72rem;
    font-weight: 700;
    padding: 3px 10px;
    border-radius: 20px;
    text-transform: uppercase;
}
.status-pill::before {
    content: '';
    width: 6px; height: 6px;
    background: #10b981;
    border-radius: 50%;
    box-shadow: 0 0 6px #10b981;
}
.user-badge {
    background: rgba(0, 210, 255, 0.08);
    border: 1px solid rgba(0, 210, 255, 0.25);
    color: #00d2ff;
    padding: 4px 12px;
    border-radius: 8px;
    font-size: 0.75rem;
    font-weight: 700;
}

/* === KPI CARDS === */
.kpi-container {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
    gap: 10px;
    margin-bottom: 1.2rem;
}
.kpi-card {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: 10px;
    padding: 0.85rem 1rem;
    transition: transform 0.15s ease, border-color 0.15s ease;
}
.kpi-card:hover {
    border-color: var(--border-active);
    transform: translateY(-1px);
}
.kpi-label {
    font-size: 0.68rem;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-weight: 700;
    margin-bottom: 4px;
}
.kpi-value {
    font-size: 1.7rem;
    font-weight: 900;
    line-height: 1.1;
    color: var(--text-primary);
}
.kpi-sub {
    font-size: 0.68rem;
    color: var(--text-dim);
    margin-top: 3px;
}

/* === OPERATIONAL PANELS === */
.op-panel {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: 12px;
    padding: 1.2rem;
    margin-bottom: 1rem;
    box-shadow: 0 4px 18px rgba(0,0,0,0.3);
}
.panel-header {
    font-size: 0.75rem;
    font-weight: 800;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.12em;
    margin-bottom: 0.9rem;
    display: flex;
    align-items: center;
    gap: 8px;
}
.panel-header::before {
    content: '';
    display: inline-block;
    width: 3px;
    height: 14px;
    background: var(--accent-cyan);
    border-radius: 2px;
}

/* === STATUS TAGS === */
.badge-status {
    padding: 3px 8px;
    border-radius: 6px;
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    display: inline-block;
}
.status-reported   { background: rgba(148, 163, 184, 0.15); color: #94a3b8; border: 1px solid rgba(148, 163, 184, 0.3); }
.status-analyzed   { background: rgba(168, 85, 247, 0.15); color: #a855f7; border: 1px solid rgba(168, 85, 247, 0.3); }
.status-verified   { background: rgba(59, 130, 246, 0.15); color: #3b82f6; border: 1px solid rgba(59, 130, 246, 0.3); }
.status-dispatched { background: rgba(245, 158, 11, 0.15); color: #f59e0b; border: 1px solid rgba(245, 158, 11, 0.3); }
.status-enroute    { background: rgba(249, 115, 22, 0.15); color: #f97316; border: 1px solid rgba(249, 115, 22, 0.3); }
.status-onscene    { background: rgba(239, 68, 68, 0.18); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.35); }
.status-resolved   { background: rgba(16, 185, 129, 0.15); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.3); }
.status-cancelled  { background: rgba(100, 116, 139, 0.15); color: #64748b; border: 1px solid rgba(100, 116, 139, 0.3); }

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, #ff4757 0%, #ff6b35 100%) !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 700 !important;
    letter-spacing: 0.03em !important;
    padding: 0.5rem 1.1rem !important;
    font-size: 0.82rem !important;
    transition: all 0.2s ease !important;
}
.stButton > button:hover {
    box-shadow: 0 4px 15px rgba(255, 71, 87, 0.4) !important;
    transform: translateY(-1px) !important;
}
</style>
"""

# ---------------------------------------------------------------------------
# Global Singletons
# ---------------------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def get_routing_engine():
    return GraphRoutingEngine(seed=42)

@st.cache_resource(show_spinner=False)
def get_mesh_simulator():
    return MeshProtocolSimulator(seed=None)

# ---------------------------------------------------------------------------
# Session State Setup & Authentication
# ---------------------------------------------------------------------------
def init_app_session():
    init_database()
    if "current_user" not in st.session_state:
        # Default active session: Commander Rohit Singh (Admin)
        st.session_state.current_user = {
            "id": 1,
            "username": "admin",
            "full_name": "Commander Rohit Singh",
            "role": "admin",
            "badge_number": "GN-CMD-01",
        }
    if "active_view" not in st.session_state:
        st.session_state.active_view = "Command Center"
    if "selected_incident_id" not in st.session_state:
        st.session_state.selected_incident_id = None
    if "map_center" not in st.session_state:
        st.session_state.map_center = [28.6140, 77.2280]


# ---------------------------------------------------------------------------
# Top Header Renderer
# ---------------------------------------------------------------------------
def render_top_header():
    u = st.session_state.current_user
    now_str = datetime.datetime.now().strftime("%d %b %Y · %H:%M:%S")

    st.markdown(f"""
    <div class="cad-header">
        <div class="cad-brand">
            <div>
                <div class="cad-title">🚨 GuardianNodes RoadSoS</div>
                <div class="cad-subtitle">Emergency Computer-Aided Dispatch (CAD) Platform · Delhi NCR Command Node</div>
            </div>
        </div>
        <div class="cad-meta">
            <a href="http://localhost:8000" target="_blank" style="text-decoration:none;"><span class="status-pill" style="border-color:#00d2ff;color:#00d2ff;">🌐 Ecosystem Apps (:8000)</span></a>
            <span class="status-pill">System Operational</span>
            <span style="font-size:0.75rem;color:#8892b0;font-family:'JetBrains Mono',monospace;">🕒 {now_str}</span>
            <span class="user-badge">👤 {u['full_name']} ({u['role'].upper()})</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Sidebar Navigation & User Session
# ---------------------------------------------------------------------------
def render_sidebar():
    st.sidebar.markdown("""
    <div style="padding:0.4rem 0 1rem;border-bottom:1px solid rgba(255,255,255,0.08);margin-bottom:1rem;">
        <div style="font-size:1.15rem;font-weight:900;color:#00d2ff;">GUARDIANNODES</div>
        <div style="font-size:0.68rem;color:#8892b0;text-transform:uppercase;letter-spacing:0.1em;">Tactical CAD System v2.6</div>
        <div style="margin-top:0.5rem;font-size:0.7rem;color:#38bdf8;">
            <a href="http://localhost:8000" target="_blank" style="color:#00d2ff;text-decoration:none;">🚀 Open Public App & Driver PWA ↗</a>
        </div>
    </div>
    """, unsafe_allow_html=True)

    nav_options = [
        "🚨 Command Center",
        "📋 Incident Management",
        "🗺️ Live Emergency Map",
        "🚒 Vehicle Fleet",
        "🏥 Hospital Coordination",
        "🧠 AI Intelligence",
        "📡 V2X Mesh Inspector",
        "📊 Operations Analytics",
        "📑 Reports & Documentation",
        "⚙️ Settings & Users",
    ]

    # Find index
    current_idx = 0
    for idx, opt in enumerate(nav_options):
        if st.session_state.active_view in opt:
            current_idx = idx
            break

    selected = st.sidebar.radio("Navigation", nav_options, index=current_idx, label_visibility="collapsed")
    # Clean up selection
    clean_view = selected.split(" ", 1)[1] if " " in selected else selected
    st.session_state.active_view = clean_view

    # Quick Switch User Profile for testing RBAC
    st.sidebar.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)
    st.sidebar.caption("🔑 Active Operator Profile (RBAC Simulation):")
    users = get_all_users()
    u_map = {f"{u['full_name']} ({u['role']})": u for u in users}
    current_label = next((k for k, v in u_map.items() if v["username"] == st.session_state.current_user["username"]), list(u_map.keys())[0])

    new_user_label = st.sidebar.selectbox("Switch Operator", list(u_map.keys()), index=list(u_map.keys()).index(current_label))
    if u_map[new_user_label]["username"] != st.session_state.current_user["username"]:
        st.session_state.current_user = u_map[new_user_label]
        st.rerun()

    st.sidebar.markdown(f"""
    <div style="font-size:0.7rem;color:#64748b;margin-top:1.5rem;padding-top:1rem;border-top:1px solid rgba(255,255,255,0.05);">
        GuardianNodes RoadSoS CAD<br>
        Built with Python 3.14 + Streamlit 1.67<br>
        Zero-Shot NLP + Dijkstra + V2X Mesh
    </div>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# VIEW 1: Command Center (Palantir-Style Tactical Dashboard)
# ---------------------------------------------------------------------------
def render_command_center(routing_engine, mesh_sim):
    kpis = get_incident_kpis()

    # KPI Banner
    st.markdown(f"""
    <div class="kpi-container">
        <div class="kpi-card">
            <div class="kpi-label">Total Incidents</div>
            <div class="kpi-value" style="color:#00d2ff;">{kpis['total_incidents']}</div>
            <div class="kpi-sub">Lifetime logged</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Active Emergencies</div>
            <div class="kpi-value" style="color:#ef4444;">{kpis['active_incidents']}</div>
            <div class="kpi-sub">Dispatch in progress</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Available Fleet</div>
            <div class="kpi-value" style="color:#10b981;">{kpis['available_vehicles']}</div>
            <div class="kpi-sub">Ready for assignment</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Dispatched Units</div>
            <div class="kpi-value" style="color:#f59e0b;">{kpis['dispatched_vehicles']}</div>
            <div class="kpi-sub">En route / on scene</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Trauma ICU Beds</div>
            <div class="kpi-value" style="color:#3b82f6;">{kpis['available_icu_beds']}</div>
            <div class="kpi-sub">Delhi NCR capacity</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Avg Response ETA</div>
            <div class="kpi-value" style="color:#a855f7;">{kpis['avg_response_time']}m</div>
            <div class="kpi-sub">Golden Hour target &le; 8m</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 2-Column Tactical Layout (Left: Live Map & Dispatches, Right: Critical Triage & Quick Report)
    col_main, col_side = st.columns([2.3, 1.2])

    with col_main:
        st.markdown('<div class="op-panel">', unsafe_allow_html=True)
        st.markdown('<div class="panel-header">🗺️ LIVE TACTICAL ROAD NETWORK MAP (DELHI NCR COMMAND)</div>', unsafe_allow_html=True)

        incidents = get_all_incidents(limit=25)
        vehicles = get_all_vehicles()
        hospitals = get_all_hospitals()

        # Build Plotly Map Tactical Map
        fig = go.Figure()

        # 1. Municipal Grid Nodes
        all_coords = routing_engine.all_node_coords
        lats = [c[0] for c in all_coords.values()]
        lons = [c[1] for c in all_coords.values()]
        fig.add_trace(go.Scattermap(
            lat=lats, lon=lons, mode="markers",
            marker=dict(size=4, color="rgba(148, 163, 184, 0.25)"),
            name="Municipal Grid Intersections",
            hoverinfo="none",
        ))

        # 2. Hospitals
        h_lats = [h["latitude"] for h in hospitals]
        h_lons = [h["longitude"] for h in hospitals]
        h_names = [f"🏥 {h['name']}<br>ICU Beds Free: {h['available_icu_beds']}/{h['total_icu_beds']}" for h in hospitals]
        fig.add_trace(go.Scattermap(
            lat=h_lats, lon=h_lons, mode="markers+text",
            marker=dict(size=14, color="#3b82f6", symbol="hospital"),
            text=[h['name'].split()[0] for h in hospitals],
            textposition="top right",
            hovertext=h_names, hoverinfo="text",
            name="Trauma Hospitals",
        ))

        # 3. Emergency Vehicles
        v_lats = [v["current_lat"] for v in vehicles]
        v_lons = [v["current_lon"] for v in vehicles]
        v_colors = ["#10b981" if v["status"] == "Available" else "#f59e0b" for v in vehicles]
        v_texts = [f"{v['callsign']} ({v['status']})" for v in vehicles]
        fig.add_trace(go.Scattermap(
            lat=v_lats, lon=v_lons, mode="markers+text",
            marker=dict(size=12, color=v_colors),
            text=[v['callsign'] for v in vehicles],
            textposition="bottom right",
            hovertext=v_texts, hoverinfo="text",
            name="Emergency Vehicles",
        ))

        # 4. Active Accidents
        active_incs = [i for i in incidents if i["status"] not in ("Resolved", "Cancelled")]
        if active_incs:
            i_lats = [i["latitude"] for i in active_incs]
            i_lons = [i["longitude"] for i in active_incs]
            i_colors = ["#ef4444" if i["urgency_index"] >= 8.0 else "#f97316" for i in active_incs]
            i_texts = [f"🚨 {i['incident_id']} - {i['category']}<br>Urgency: {i['urgency_index']:.2f}<br>{i['landmark']}" for i in active_incs]
            fig.add_trace(go.Scattermap(
                lat=i_lats, lon=i_lons, mode="markers+text",
                marker=dict(size=18, color=i_colors),
                text=[f"💥 {i['incident_id'][-4:]}" for i in active_incs],
                textposition="top left",
                hovertext=i_texts, hoverinfo="text",
                name="Active Crash Sites",
            ))

        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=0, b=0),
            height=380,
            map=dict(
                style="carto-darkmatter",
                center=dict(lat=28.595, lon=77.215),
                zoom=11.6,
            ),
            legend=dict(
                bgcolor="rgba(12, 19, 34, 0.85)",
                bordercolor="rgba(255,255,255,0.08)",
                borderwidth=1,
                font=dict(size=10, color="#94a3b8"),
                yanchor="top", y=0.98, xanchor="left", x=0.02,
            ),
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)

        # Recent Dispatches & Tactical Feed
        st.markdown('<div class="op-panel">', unsafe_allow_html=True)
        st.markdown('<div class="panel-header">⚡ ACTIVE DISPATCHES & EMERGENCY FLEET TELEMETRY</div>', unsafe_allow_html=True)
        dispatches = get_dispatch_history(limit=8)
        if dispatches:
            df_disp = pd.DataFrame(dispatches)[[
                "dispatch_id", "incident_id", "callsign", "incident_category",
                "incident_landmark", "status", "route_time_min", "assigned_at"
            ]]
            df_disp.columns = ["Dispatch ID", "Incident", "Unit", "Category", "Target Landmark", "Status", "ETA (min)", "Dispatched At"]
            st.dataframe(df_disp, use_container_width=True, hide_index=True)
        else:
            st.info("No active dispatches. Fleet on standby.")
        st.markdown("</div>", unsafe_allow_html=True)

    with col_side:
        # Quick Emergency Incident Report Form
        st.markdown('<div class="op-panel">', unsafe_allow_html=True)
        st.markdown('<div class="panel-header">🚨 RAPID INCIDENT INTAKE</div>', unsafe_allow_html=True)

        with st.form("rapid_incident_form", clear_on_submit=True):
            st_text = st.text_area(
                "Witness Report / Telematics",
                placeholder="E.g. Head-on truck collision near AIIMS Flyover, two trapped, fire visible...",
                height=90,
            )
            col_loc1, col_loc2 = st.columns(2)
            with col_loc1:
                st_lat = st.number_input("Latitude", value=28.5672, format="%.4f")
            with col_loc2:
                st_lon = st.number_input("Longitude", value=77.2100, format="%.4f")

            st_witness = st.text_input("Reporter Name", value="Control Room Officer")
            st_tags = st.multiselect(
                "Evidence Flags",
                ["Airbag Deployed", "Fire / Heavy Smoke", "Vehicle Intrusion", "Hazardous Fluid Spill", "Multiple Casualties"],
            )

            btn_submit = st.form_submit_button("🚨 PROCESS & LOG EMERGENCY", use_container_width=True)
            if btn_submit:
                if st_text.strip():
                    try:
                        inc = create_incident(
                            witness_statement=st_text,
                            latitude=st_lat,
                            longitude=st_lon,
                            witness_name=st_witness,
                            visual_tags=st_tags,
                            username=st.session_state.current_user["username"],
                        )
                        st.success(f"Incident {inc['incident_id']} logged! Assigned Urgency: {inc['urgency_index']:.2f}")
                        st.session_state.selected_incident_id = inc["incident_id"]
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error logging incident: {e}")
                else:
                    st.warning("Please provide report text.")

        st.markdown("</div>", unsafe_allow_html=True)

        # Quick Scenario Presets
        st.markdown('<div class="op-panel">', unsafe_allow_html=True)
        st.markdown('<div class="panel-header">⚡ QUICK SCENARIO SIMULATORS</div>', unsafe_allow_html=True)
        preset_scenarios = [
            ("💥 Fuel Depot Blast", "Major explosion at the central fuel depot! 3 vehicles burning, toxic smoke, 2 casualties.", 28.6140, 77.2280, ["Fire / Heavy Smoke", "Multiple Casualties"]),
            ("🚗 NH-48 Pileup", "Multi-car highway pileup on NH-48 Airport Express. 4 cars, 3 injured, 1 trapped driver.", 28.5355, 77.1025, ["Vehicle Intrusion", "Multiple Casualties"]),
            ("☣️ DND Chemical Leak", "Industrial chemical tanker overturned at DND Toll Plaza. Corrosive acid spilling.", 28.5833, 77.2833, ["Hazardous Fluid Spill"]),
            ("⚡ Minor Fender Bender", "Small collision between two sedans, minor bumper dent, zero injuries reported.", 28.5701, 77.2345, []),
        ]
        for title, text, p_lat, p_lon, p_tags in preset_scenarios:
            if st.button(title, key=f"cmd_preset_{title}", use_container_width=True):
                inc = create_incident(
                    witness_statement=text,
                    latitude=p_lat,
                    longitude=p_lon,
                    witness_name="Automated Highway Sensor / eCall",
                    visual_tags=p_tags,
                    username=st.session_state.current_user["username"],
                )
                st.toast(f"Logged {inc['incident_id']} — Urgency: {inc['urgency_index']:.2f}", icon="🚨")
                st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# VIEW 2: Incident Management (List, Filter, Details, Status Lifecycle)
# ---------------------------------------------------------------------------
def render_incident_management(routing_engine):
    st.markdown('<div class="cad-header"><div class="cad-title">📋 EMERGENCY INCIDENT REGISTRY & STATUS LIFECYCLE</div></div>', unsafe_allow_html=True)

    # Filter Bar
    c_f1, c_f2, c_f3 = st.columns([1.5, 1.5, 2.5])
    with c_f1:
        status_filter = st.selectbox(
            "Filter Status",
            ["All", "Reported", "AI Analyzed", "Verified", "Dispatched", "En Route", "On Scene", "Resolved", "Cancelled"],
        )
    with c_f2:
        category_filter = st.selectbox(
            "Filter Category",
            ["All", "Critical Medical Trauma", "Fire/Explosion", "Vehicle Entrapment", "Hazardous Material Leak", "Minor Collision"],
        )
    with c_f3:
        search_kw = st.text_input("Search (ID, Statement, Landmark)", placeholder="Search keywords…")

    incidents = get_all_incidents(
        status_filter=status_filter,
        category_filter=category_filter,
        search_query=search_kw,
    )

    col_list, col_inspect = st.columns([1.3, 1.7])

    with col_list:
        st.markdown(f"**Showing {len(incidents)} Incidents**")
        for inc in incidents:
            st_color = {
                "Reported": "#94a3b8", "AI Analyzed": "#a855f7", "Verified": "#3b82f6",
                "Dispatched": "#f59e0b", "En Route": "#f97316", "On Scene": "#ef4444",
                "Resolved": "#10b981", "Cancelled": "#64748b",
            }.get(inc["status"], "#94a3b8")

            with st.container():
                st.markdown(f"""
                <div class="op-panel" style="padding:0.9rem;border-left:4px solid {st_color};">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <span style="font-size:0.85rem;font-weight:800;color:#00d2ff;">{inc['incident_id']}</span>
                        <span class="badge-status" style="background:{st_color}22;color:{st_color};">{inc['status']}</span>
                    </div>
                    <div style="font-size:0.95rem;font-weight:700;margin:4px 0;">{inc['category']}</div>
                    <div style="font-size:0.75rem;color:#94a3b8;">📍 {inc['landmark']}</div>
                    <div style="font-size:0.78rem;color:#f1f5f9;margin-top:4px;">{inc['witness_statement'][:85]}…</div>
                </div>
                """, unsafe_allow_html=True)
                if st.button("Inspect Incident", key=f"insp_btn_{inc['incident_id']}", use_container_width=True):
                    st.session_state.selected_incident_id = inc["incident_id"]
                    st.rerun()

    with col_inspect:
        target_id = st.session_state.selected_incident_id
        if not target_id and incidents:
            target_id = incidents[0]["incident_id"]

        if target_id:
            full_inc = get_incident_by_id(target_id)
            if full_inc:
                st.markdown(f"""
                <div class="op-panel">
                    <div class="panel-header">🚨 INCIDENT DOSSIER: {full_inc['incident_id']}</div>
                    <div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:10px;margin-bottom:12px;">
                        <div>
                            <span style="font-size:0.7rem;color:#94a3b8;text-transform:uppercase;">Category</span>
                            <div style="font-size:1.1rem;font-weight:800;color:#00d2ff;">{full_inc['category']}</div>
                        </div>
                        <div>
                            <span style="font-size:0.7rem;color:#94a3b8;text-transform:uppercase;">Urgency Score</span>
                            <div style="font-size:1.1rem;font-weight:800;color:#ef4444;">{full_inc['urgency_index']:.2f}/10.00</div>
                        </div>
                        <div>
                            <span style="font-size:0.7rem;color:#94a3b8;text-transform:uppercase;">Golden Hour SLA</span>
                            <div style="font-size:1.1rem;font-weight:800;color:#f59e0b;">&le; {full_inc['golden_hour_sla_min']:.0f} min</div>
                        </div>
                        <div>
                            <span style="font-size:0.7rem;color:#94a3b8;text-transform:uppercase;">Current Status</span>
                            <div style="font-size:1.1rem;font-weight:800;color:#10b981;">{full_inc['status']}</div>
                        </div>
                    </div>
                    <div style="font-size:0.85rem;line-height:1.5;margin-bottom:12px;background:rgba(0,0,0,0.3);padding:10px;border-radius:8px;">
                        <strong>Report Description:</strong> {full_inc['witness_statement']}
                    </div>
                    <div style="font-size:0.8rem;color:#94a3b8;margin-bottom:8px;">
                        <strong>AI Clinical & Tactical Reasoning:</strong> {full_inc['ai_analysis_reasoning']}
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # Status Transition Action Bar (RBAC Protected)
                st.markdown('<div class="op-panel">', unsafe_allow_html=True)
                st.markdown('<div class="panel-header">⚡ OPERATIONAL LIFECYCLE TRANSITION</div>', unsafe_allow_html=True)

                status_options = ["Reported", "AI Analyzed", "Verified", "Dispatched", "En Route", "On Scene", "Resolved", "Cancelled"]
                curr_status_idx = status_options.index(full_inc["status"]) if full_inc["status"] in status_options else 0
                new_status = st.selectbox("Update Status To", status_options, index=curr_status_idx)

                if st.button("Apply Status Transition", use_container_width=True):
                    try:
                        update_incident_status(
                            incident_id=full_inc["incident_id"],
                            new_status=new_status,
                            username=st.session_state.current_user["username"],
                        )
                        st.success(f"Status updated to '{new_status}'!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error updating status: {e}")

                st.markdown("</div>", unsafe_allow_html=True)

                # Dispatches for this incident
                st.markdown('<div class="op-panel">', unsafe_allow_html=True)
                st.markdown('<div class="panel-header">🚒 ASSIGNED EMERGENCY UNITS</div>', unsafe_allow_html=True)
                if full_inc["dispatches"]:
                    for d in full_inc["dispatches"]:
                        st.markdown(f"""
                        <div style="display:flex;justify-content:space-between;padding:8px;background:rgba(0,0,0,0.25);border-radius:6px;margin-bottom:6px;">
                            <span><strong>{d['vehicle_label']}</strong> ({d['callsign']})</span>
                            <span>Status: <strong style="color:#f59e0b;">{d['status']}</strong> | ETA: {d['route_time_min']:.1f}m</span>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("No vehicles dispatched yet to this incident.")

                # Quick dispatch trigger
                avail_vehicles = get_available_vehicles()
                if avail_vehicles and full_inc["status"] not in ("Resolved", "Cancelled"):
                    st.caption("Assign an available emergency unit:")
                    v_choice = st.selectbox(
                        "Select Fleet Unit",
                        avail_vehicles,
                        format_func=lambda x: f"{x['label']} ({x['callsign']}) - Base: {x['station_base']}",
                        key=f"quick_dispatch_{full_inc['incident_id']}",
                    )
                    if st.button("🚨 Dispatch Selected Unit", use_container_width=True):
                        try:
                            dsp_id = dispatch_vehicle(
                                incident_id=full_inc["incident_id"],
                                vehicle_id=v_choice["id"],
                                assigned_by=st.session_state.current_user["username"],
                                route_time_min=round(random.uniform(5.0, 12.0), 1),
                                dispatch_notes="Dispatched via Incident Dossier view",
                            )
                            st.success(f"Dispatched {v_choice['callsign']}! Ref: {dsp_id}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Dispatch failed: {e}")

                st.markdown("</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# VIEW 3: Live Emergency Map
# ---------------------------------------------------------------------------
def render_live_map(routing_engine):
    st.markdown('<div class="cad-header"><div class="cad-title">🗺️ INTERACTIVE EMERGENCY TACTICAL MAP & CORRIDORS</div></div>', unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        show_incidents = st.checkbox("Show Active Crashes", value=True)
    with c2:
        show_fleet = st.checkbox("Show Emergency Fleet", value=True)
    with c3:
        show_hospitals = st.checkbox("Show Regional Trauma Centers", value=True)

    vehicles = get_all_vehicles()
    hospitals = get_all_hospitals()
    incidents = get_all_incidents(limit=30)

    fig = go.Figure()

    # Network Grid
    all_coords = routing_engine.all_node_coords
    lats = [c[0] for c in all_coords.values()]
    lons = [c[1] for c in all_coords.values()]
    fig.add_trace(go.Scattermap(
        lat=lats, lon=lons, mode="markers",
        marker=dict(size=4, color="rgba(148, 163, 184, 0.25)"),
        name="Road Network Graph",
        hoverinfo="none",
    ))

    if show_hospitals:
        fig.add_trace(go.Scattermap(
            lat=[h["latitude"] for h in hospitals],
            lon=[h["longitude"] for h in hospitals],
            mode="markers+text",
            marker=dict(size=14, color="#3b82f6"),
            text=[h['name'].split()[0] for h in hospitals],
            textposition="top right",
            hovertext=[f"🏥 {h['name']}<br>ICU Free: {h['available_icu_beds']}/{h['total_icu_beds']}<br>Tel: {h['emergency_hotline']}" for h in hospitals],
            hoverinfo="text",
            name="Trauma Centers",
        ))

    if show_fleet:
        v_colors = ["#10b981" if v["status"] == "Available" else "#f59e0b" for v in vehicles]
        fig.add_trace(go.Scattermap(
            lat=[v["current_lat"] for v in vehicles],
            lon=[v["current_lon"] for v in vehicles],
            mode="markers+text",
            marker=dict(size=12, color=v_colors),
            text=[v['callsign'] for v in vehicles],
            textposition="bottom right",
            hovertext=[f"Unit: {v['label']}<br>Status: {v['status']}<br>Crew: {v['crew_lead']}" for v in vehicles],
            hoverinfo="text",
            name="Fleet Units",
        ))

    if show_incidents:
        active_incs = [i for i in incidents if i["status"] not in ("Resolved", "Cancelled")]
        if active_incs:
            fig.add_trace(go.Scattermap(
                lat=[i["latitude"] for i in active_incs],
                lon=[i["longitude"] for i in active_incs],
                mode="markers+text",
                marker=dict(size=18, color=["#ef4444" if i["urgency_index"] >= 8.0 else "#f97316" for i in active_incs]),
                text=[f"💥 {i['incident_id'][-4:]}" for i in active_incs],
                textposition="top left",
                hovertext=[f"🚨 {i['incident_id']}<br>{i['category']}<br>Urgency: {i['urgency_index']:.2f}<br>{i['landmark']}" for i in active_incs],
                hoverinfo="text",
                name="Incidents",
            ))

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=0, b=0),
        height=550,
        map=dict(
            style="carto-darkmatter",
            center=dict(lat=28.595, lon=77.215),
            zoom=11.8,
        ),
        legend=dict(
            bgcolor="rgba(12, 19, 34, 0.85)",
            bordercolor="rgba(255,255,255,0.08)",
            borderwidth=1,
            font=dict(size=10, color="#94a3b8"),
            yanchor="top", y=0.98, xanchor="left", x=0.02,
        ),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# ---------------------------------------------------------------------------
# VIEW 4: Vehicle Fleet Management (Fleet Live Tracking, Dispatch & Maintenance)
# ---------------------------------------------------------------------------
def render_vehicle_fleet():
    st.markdown('<div class="cad-header"><div class="cad-title">🚒 EMERGENCY VEHICLE FLEET MANAGEMENT & AVAILABILITY</div></div>', unsafe_allow_html=True)

    vehicles = get_all_vehicles()
    incidents = get_all_incidents()
    active_incidents = [i for i in incidents if i["status"] not in ("Resolved", "Cancelled")]

    c_f1, c_f2 = st.columns([2, 1.2])

    with c_f1:
        st.markdown('<div class="op-panel">', unsafe_allow_html=True)
        st.markdown('<div class="panel-header">🚨 FLEET INVENTORY & REAL-TIME OPERATIONAL STATUS</div>', unsafe_allow_html=True)

        df_v = pd.DataFrame(vehicles)[[
            "callsign", "vehicle_type", "label", "station_base",
            "status", "fuel_level_pct", "crew_lead", "active_incident_id"
        ]]
        df_v.columns = ["Callsign", "Type", "Vehicle Label", "Station Base", "Status", "Fuel %", "Crew Lead", "Active Incident"]
        st.dataframe(df_v, use_container_width=True, hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with c_f2:
        st.markdown('<div class="op-panel">', unsafe_allow_html=True)
        st.markdown('<div class="panel-header">⚡ MANUAL VEHICLE STATUS OVERRIDE</div>', unsafe_allow_html=True)

        v_sel = st.selectbox(
            "Select Vehicle",
            vehicles,
            format_func=lambda x: f"{x['callsign']} - {x['label']} ({x['status']})",
        )
        new_status = st.selectbox(
            "Target Status",
            ["Available", "Dispatched", "En Route", "On Scene", "Busy", "Maintenance"],
            index=["Available", "Dispatched", "En Route", "On Scene", "Busy", "Maintenance"].index(v_sel["status"]),
        )
        if st.button("Update Vehicle Status", use_container_width=True):
            try:
                update_vehicle_status(
                    vehicle_id=v_sel["id"],
                    new_status=new_status,
                    username=st.session_state.current_user["username"],
                )
                st.success(f"{v_sel['callsign']} updated to '{new_status}'!")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to update status: {e}")

        st.markdown("</div>", unsafe_allow_html=True)

    # Active Dispatches Table with Cancellation & Reassignment
    st.markdown('<div class="op-panel">', unsafe_allow_html=True)
    st.markdown('<div class="panel-header">📋 ACTIVE DISPATCH CORRIDORS (CANCELLATION & REASSIGNMENT)</div>', unsafe_allow_html=True)

    dispatches = get_dispatch_history(limit=25)
    active_dispatches = [d for d in dispatches if d["status"] in ("Active", "En Route", "On Scene")]

    if active_dispatches:
        for disp in active_dispatches:
            col_d1, col_d2, col_d3 = st.columns([2, 1, 1])
            with col_d1:
                st.markdown(f"**{disp['dispatch_id']}** · Unit: **{disp['callsign']}** ➔ Incident: **{disp['incident_id']}** ({disp['incident_landmark']})")
                st.caption(f"Dispatched at: {disp['assigned_at']} | ETA: {disp['route_time_min']:.1f}m | Status: {disp['status']}")
            with col_d2:
                cancel_reason = st.text_input("Cancel Reason", key=f"rsn_{disp['dispatch_id']}", placeholder="E.g. False alarm / stand down")
            with col_d3:
                if st.button("Cancel Dispatch", key=f"cnc_{disp['dispatch_id']}"):
                    try:
                        cancel_dispatch(disp["dispatch_id"], st.session_state.current_user["username"], reason=cancel_reason)
                        st.success(f"Cancelled {disp['dispatch_id']} and released {disp['callsign']} back to fleet.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error cancelling dispatch: {e}")
            st.divider()
    else:
        st.info("No active dispatches currently in progress. All fleet units are standing by.")
    st.markdown("</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# VIEW 5: Hospital Coordination (Live Bed Capacity & Patient Handover)
# ---------------------------------------------------------------------------
def render_hospital_coordination():
    st.markdown('<div class="cad-header"><div class="cad-title">🏥 REGIONAL TRAUMA HOSPITAL NETWORK & LIVE BED RESERVATION</div></div>', unsafe_allow_html=True)

    hospitals = get_all_hospitals()
    incidents = get_all_incidents()
    active_incidents = [i for i in incidents if i["status"] not in ("Resolved", "Cancelled")]

    # Hospital Cards
    cols = st.columns(len(hospitals))
    for idx, h in enumerate(hospitals):
        with cols[idx]:
            pct = (h["available_icu_beds"] / h["total_icu_beds"]) * 100 if h["total_icu_beds"] > 0 else 0
            color = "#10b981" if pct >= 30 else "#f59e0b" if pct > 0 else "#ef4444"
            st.markdown(f"""
            <div class="op-panel" style="border-top:4px solid {color};padding:0.9rem;">
                <div style="font-size:0.68rem;font-weight:700;color:{color};text-transform:uppercase;">{h['category']}</div>
                <div style="font-size:0.95rem;font-weight:800;margin:4px 0;">{h['name']}</div>
                <div style="margin:8px 0;">
                    <div style="font-size:1.4rem;font-weight:900;color:{color};">{h['available_icu_beds']} / {h['total_icu_beds']}</div>
                    <div style="font-size:0.68rem;color:#94a3b8;text-transform:uppercase;">Available ICU Trauma Beds</div>
                </div>
                <div style="font-size:0.75rem;color:#94a3b8;">🩺 Trauma Bays: <strong>{h['trauma_bays']}</strong></div>
                <div style="font-size:0.75rem;color:#94a3b8;">🚑 Pending: <strong>{h['pending_admissions']}</strong></div>
                <div style="font-size:0.72rem;color:#f59e0b;margin-top:6px;">📞 {h['emergency_hotline']}</div>
            </div>
            """, unsafe_allow_html=True)

    # Bed Reservation Form & Patient Handover
    c_res1, c_res2 = st.columns([1.2, 1.8])

    with c_res1:
        st.markdown('<div class="op-panel">', unsafe_allow_html=True)
        st.markdown('<div class="panel-header">🛏️ RESERVE TRAUMA BED IN ADVANCE</div>', unsafe_allow_html=True)

        if active_incidents:
            h_choice = st.selectbox("Select Target Hospital", hospitals, format_func=lambda x: f"{x['name']} ({x['available_icu_beds']} free ICU)")
            i_choice = st.selectbox("Select Active Incident", active_incidents, format_func=lambda x: f"{x['incident_id']} - {x['category']} ({x['landmark']})")
            p_ident = st.text_input("Patient Identifier / Triage Tag", value=f"PATIENT-{random.randint(100, 999)} (Red Tag)")
            b_type = st.selectbox("Bed Requirement", ["ICU Trauma Bay", "Critical Resuscitation Suite", "Burns Isolation Unit", "General Emergency Bed"])
            res_notes = st.text_input("Clinical Handover Notes", value="Polytrauma with suspected intracranial hematoma, intubated")

            if st.button("Confirm Bed Reservation", use_container_width=True):
                try:
                    res_id = reserve_hospital_bed(
                        hospital_id=h_choice["id"],
                        incident_id=i_choice["incident_id"],
                        patient_identifier=p_ident,
                        bed_type=b_type,
                        reserved_by=st.session_state.current_user["username"],
                        notes=res_notes,
                    )
                    st.success(f"Bed reserved at {h_choice['name']}! Ref: {res_id}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Reservation failed: {e}")
        else:
            st.info("No active incidents requiring hospital reservation.")

        st.markdown("</div>", unsafe_allow_html=True)

    with c_res2:
        st.markdown('<div class="op-panel">', unsafe_allow_html=True)
        st.markdown('<div class="panel-header">📋 ACTIVE BED RESERVATIONS & HANDOVER TRACKING</div>', unsafe_allow_html=True)

        reservations = get_active_reservations(limit=25)
        if reservations:
            for r in reservations:
                st_color = "#10b981" if r["patient_handover_status"] == "Patient Admitted" else "#f59e0b"
                col_r1, col_r2 = st.columns([2, 1.2])
                with col_r1:
                    st.markdown(f"**{r['reservation_id']}** · Hospital: **{r['hospital_name']}**")
                    st.markdown(f"Patient: **{r['patient_identifier']}** · Incident: **{r['incident_id']}** ({r['incident_category']})")
                    st.caption(f"Bed Type: {r['bed_type']} | Reserved at: {r['reserved_at']} | Status: {r['patient_handover_status']}")
                with col_r2:
                    h_statuses = ["Pending Arrival", "Patient Admitted", "Transferred", "Released"]
                    curr_h_idx = h_statuses.index(r["patient_handover_status"]) if r["patient_handover_status"] in h_statuses else 0
                    new_h_status = st.selectbox("Update Handover", h_statuses, index=curr_h_idx, key=f"h_stat_{r['reservation_id']}")
                    if st.button("Update Handover", key=f"btn_h_{r['reservation_id']}"):
                        try:
                            update_patient_handover(r["reservation_id"], new_h_status, st.session_state.current_user["username"])
                            st.success(f"Handover updated to '{new_h_status}'!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")
                st.divider()
        else:
            st.info("No active hospital reservations recorded.")
        st.markdown("</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# VIEW 6: AI Intelligence (Deep-Dive NLP, NER & Explainability)
# ---------------------------------------------------------------------------
def render_ai_intelligence():
    st.markdown('<div class="cad-header"><div class="cad-title">🧠 AI TRIAGE INTELLIGENCE & EXPLAINABLE REASONING ENGINE</div></div>', unsafe_allow_html=True)

    triage_engine = IntelligentTriageEngine()

    st.markdown("""
    The GuardianNodes RoadSoS AI Engine evaluates free-text witness reports and sensor telematics through:
    1. **Zero-Shot NLP Classification**: DistilBERT MNLI / heuristic semantic classification over 5 emergency categories.
    2. **Negation-Aware Extraction**: Suppresses medical trauma bonuses when witness states *"no injuries reported"*.
    3. **Mathematical Sigmoid Bounding**: Computes continuous Urgency Index `[1.00 - 10.00]` with Golden Hour SLA allocation.
    """)

    st.markdown("#### 🧪 Interactive AI Reasoning Sandbox")
    sample_texts = [
        "Major explosion at fuel storage tanker, two cars ablaze, three people severely burned and unconscious.",
        "Head-on collision on express corridor between delivery truck and sedan. Driver pinned under dashboard with leg fracture.",
        "Chemical tanker leaking fuming hydrochloric acid on highway shoulder. Strong vapor cloud spreading.",
        "Minor rear-end collision between two cars at traffic light. Small bumper scratch, zero injuries reported.",
    ]

    selected_sample = st.selectbox("Load Sample Incident Text", sample_texts)
    user_test_text = st.text_area("Test Statement", value=selected_sample, height=80)
    user_tags = st.multiselect("Test Visual Flags", ["Airbag Deployed", "Fire / Heavy Smoke", "Vehicle Intrusion", "Hazardous Fluid Spill"], default=["Fire / Heavy Smoke"] if "explosion" in user_test_text else [])

    if st.button("Run AI Analysis Pipeline", use_container_width=True):
        res = triage_engine.analyze(user_test_text, visual_tags=user_tags)

        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.metric("Top Classification", res.top_label)
        with col_b:
            st.metric("Urgency Index", f"{res.urgency_index:.2f} / 10.00")
        with col_c:
            st.metric("Golden Hour SLA", f"&le; {res.golden_hour_sla_min:.0f} min")

        col_radar, col_bars = st.columns([1, 1])
        with col_radar:
            # Radar chart
            labels = list(res.label_scores.keys())
            vals = list(res.label_scores.values())
            labels.append(labels[0])
            vals.append(vals[0])
            fig_r = go.Figure(go.Scatterpolar(r=vals, theta=labels, fill="toself", fillcolor="rgba(0,210,255,0.15)", line=dict(color="#00d2ff")))
            fig_r.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=260, margin=dict(l=10, r=10, t=20, b=10))
            st.plotly_chart(fig_r, use_container_width=True)

        with col_bars:
            st.markdown("##### Extracted Entities (NER):")
            st.json(res.entities)
            st.markdown("##### Recommended Response Fleet:")
            for u in res.recommended_units:
                st.markdown(f"- {u}")


# ---------------------------------------------------------------------------
# VIEW 7: V2X Mesh Protocol Inspector
# ---------------------------------------------------------------------------
def render_mesh_inspector(mesh_sim):
    st.markdown('<div class="cad-header"><div class="cad-title">📡 DECENTRALIZED V2X BLE/RF MESH PROTOCOL INSPECTOR</div></div>', unsafe_allow_html=True)

    st.markdown("""
    When municipal cellular 4G/5G towers are disabled or congested, **GuardianNodes RoadSoS** relays emergency telemetry
    over ad-hoc vehicular nodes using compact 24-byte binary packets protected with **CRC-32 checksums**.
    """)

    col_spec, col_sim = st.columns([1.2, 1.8])

    with col_spec:
        st.markdown('<div class="op-panel">', unsafe_allow_html=True)
        st.markdown('<div class="panel-header">📦 24-BYTE COMPACT BINARY FRAME SPECIFICATION</div>', unsafe_allow_html=True)
        st.markdown("""
        ```
        +-------------------------------------------------------+
        | Field Name        | Type    | Size    | Description    |
        +-------------------------------------------------------+
        | Latitude          | float32 | 4 Bytes | Incident Lat   |
        | Longitude         | float32 | 4 Bytes | Incident Lon   |
        | Urgency Index     | float32 | 4 Bytes | Priority 1-10  |
        | Timestamp         | uint32  | 4 Bytes | Epoch seconds  |
        | Sequence Number   | uint16  | 2 Bytes | Packet Counter |
        | Bit Flags         | uint8   | 1 Byte  | Status Flags   |
        | Reserved          | uint8   | 1 Byte  | Protocol Pad   |
        | CRC-32 Checksum   | uint32  | 4 Bytes | Integrity Hash |
        +-------------------------------------------------------+
        | Total Binary Payload: 24 Bytes (BLE Advertisement)   |
        +-------------------------------------------------------+
        ```
        """)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_sim:
        st.markdown('<div class="op-panel">', unsafe_allow_html=True)
        st.markdown('<div class="panel-header">🧪 INTERACTIVE PACKET TRANSMISSION & RETRANSMISSION SIMULATOR</div>', unsafe_allow_html=True)

        t_lat = st.number_input("Simulator Latitude", value=28.6140, format="%.4f")
        t_lon = st.number_input("Simulator Longitude", value=77.2280, format="%.4f")
        t_urg = st.slider("Simulator Urgency", 1.0, 10.0, 9.2)
        t_hops = st.slider("Simulated Relay Hops", 3, 7, 4)

        if st.button("Transmit Packet Over Ad-Hoc V2X Mesh", use_container_width=True):
            res = mesh_sim.transmit_sync(t_lat, t_lon, t_urg, num_hops=t_hops)

            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Transmission Result", "✓ DELIVERED" if res.success else "✗ FAILED")
            with c2:
                st.metric("Delivery Ratio", f"{res.delivery_ratio*100:.1f}%")
            with c3:
                st.metric("Total Latency", f"{res.total_latency_ms:.1f} ms")

            st.markdown("##### 24-Byte Raw Payload Hex Dump (CRC-32 in Red):")
            st.code(f"{res.raw_payload_hex[:-8]} {res.raw_payload_hex[-8:]}")

            st.markdown("##### Hop-by-Hop Transmission & Retransmission Log:")
            for h in res.hop_logs:
                icon = "✓" if h.status in ("PASS", "RETRANSMIT_OK") else "✗"
                st.markdown(f"- **{icon} Hop {h.hop_number:02d}** · Node: `{h.relay_node_id}` | Latency: `{h.latency_ms:.1f}ms` | RSSI: `{h.rssi_dbm} dBm` | Notes: {h.notes}")

        st.markdown("</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# VIEW 8: Operations Analytics (Real DB Metrics, Trends, Export)
# ---------------------------------------------------------------------------
def render_analytics():
    st.markdown('<div class="cad-header"><div class="cad-title">📊 REAL-TIME OPERATIONS ANALYTICS & HISTORICAL AUDIT</div></div>', unsafe_allow_html=True)

    incidents = get_all_incidents(limit=200)
    dispatches = get_dispatch_history(limit=200)

    if not incidents:
        st.info("No incident records available for analytics.")
        return

    df_inc = pd.DataFrame(incidents)

    # 4 Top Analytics Cards
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.metric("Total Emergency Records", len(df_inc))
    with k2:
        resolved_pct = (len(df_inc[df_inc["status"] == "Resolved"]) / len(df_inc)) * 100
        st.metric("Resolution Rate", f"{resolved_pct:.1f}%")
    with k3:
        avg_urg = df_inc["urgency_index"].mean()
        st.metric("Mean Urgency Index", f"{avg_urg:.2f} / 10.00")
    with k4:
        crit_count = len(df_inc[df_inc["urgency_index"] >= 8.0])
        st.metric("Critical Incidents", crit_count)

    col_ch1, col_ch2 = st.columns(2)

    with col_ch1:
        st.markdown('<div class="op-panel">', unsafe_allow_html=True)
        st.markdown('<div class="panel-header">🚨 INCIDENTS BY EMERGENCY CATEGORY</div>', unsafe_allow_html=True)
        fig_cat = px.pie(
            df_inc, names="category",
            color_discrete_sequence=["#ef4444", "#f97316", "#00d2ff", "#10b981", "#a855f7"],
            hole=0.45,
        )
        fig_cat.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=280, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig_cat, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_ch2:
        st.markdown('<div class="op-panel">', unsafe_allow_html=True)
        st.markdown('<div class="panel-header">📈 RESPONSE TIME TRENDLINE (MINUTES)</div>', unsafe_allow_html=True)
        if dispatches:
            df_dsp = pd.DataFrame(dispatches)
            fig_time = px.line(
                df_dsp, x="assigned_at", y="route_time_min",
                markers=True,
                labels={"route_time_min": "Response Time (min)", "assigned_at": "Dispatch Timestamp"},
            )
            fig_time.update_traces(line_color="#00d2ff")
            fig_time.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=280, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig_time, use_container_width=True)
        else:
            st.info("No dispatch history recorded.")
        st.markdown("</div>", unsafe_allow_html=True)

    # Export Section
    st.markdown('<div class="op-panel">', unsafe_allow_html=True)
    st.markdown('<div class="panel-header">📥 EXPORT TELEMETRY & INCIDENT REGISTRY</div>', unsafe_allow_html=True)
    csv_bytes = df_inc.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Download Full Incident Registry (CSV)",
        data=csv_bytes,
        file_name=f"road_sos_incident_registry_{datetime.date.today()}.csv",
        mime="text/csv",
    )
    st.markdown("</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# VIEW 9: Reports & Documentation
# ---------------------------------------------------------------------------
def render_documentation():
    st.markdown('<div class="cad-header"><div class="cad-title">📑 PROJECT DOCUMENTATION & PRESENTATION SUITE</div></div>', unsafe_allow_html=True)

    c_doc1, c_doc2 = st.columns([1.8, 1.2])

    with c_doc1:
        st.markdown("""
        ### GuardianNodes RoadSoS
        **Mini-Project Title:** AI-Powered Emergency Road Accident Response, Dynamic Routing & V2X Mesh System  
        **Team Name:** Coders  
        **Contributors:** Rohit Singh, Shawsti Singh, Utsav  
        **Deployment Node:** Delhi NCR Emergency CAD Network (ERSS 112)  

        #### Executive Summary:
        GuardianNodes RoadSoS delivers a unified, production-grade Computer-Aided Dispatch (CAD) platform
        engineered to eliminate friction during the critical **Golden Hour** of road trauma:
        1. **Multi-Modal AI Triage**: Extracts vehicle counts, casualty numbers, and fire/hazmat mentions from reports.
        2. **Dijkstra Dynamic Routing**: Snaps raw witness GPS coordinates to the nearest physical road intersection and calculates vehicle-specific emergency corridors.
        3. **Decentralized V2X Mesh Relay**: Ensures zero loss of casualty telemetry during cellular blackouts via a compact 24-byte binary packet layout and CRC-32 automated error correction.
        4. **Live Hospital Fleet Coordination**: Connects dispatch directly to regional Level-1 trauma centers (AIIMS, Safdarjung, RML, Max Saket) with real-time ICU bed reservations.
        """)

    with c_doc2:
        st.markdown("#### 📄 Exportable Documentation & Slide Deck")
        st.caption("Re-generate or download project materials with a single click:")

        pdf_path = APP_DIR / "RoadSoS_Project_Document.pdf"
        if pdf_path.exists():
            with open(pdf_path, "rb") as f:
                st.download_button(
                    label="⬇️ Download Project Report (PDF)",
                    data=f.read(),
                    file_name="GuardianNodes_RoadSoS_Project_Report.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )

        ppt_path = APP_DIR / "Project_Presentation.pptx"
        if ppt_path.exists():
            with open(ppt_path, "rb") as f:
                st.download_button(
                    label="⬇️ Download Presentation Deck (PPTX)",
                    data=f.read(),
                    file_name="GuardianNodes_RoadSoS_Presentation.pptx",
                    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                    use_container_width=True,
                )

        html_path = APP_DIR / "Project_Documentation.html"
        if html_path.exists():
            with open(html_path, "r", encoding="utf-8") as f:
                st.download_button(
                    label="⬇️ Download Full HTML Report",
                    data=f.read(),
                    file_name="Project_Documentation.html",
                    mime="text/html",
                    use_container_width=True,
                )


# ---------------------------------------------------------------------------
# VIEW 10: Settings & User Administration (RBAC & Audit Trail)
# ---------------------------------------------------------------------------
def render_settings():
    st.markdown('<div class="cad-header"><div class="cad-title">⚙️ SYSTEM ADMINISTRATION, RBAC & AUDIT LOGS</div></div>', unsafe_allow_html=True)

    tab_users, tab_audit = st.tabs(["👥 System Users & Roles", "🛡️ Immutable Security Audit Trail"])

    with tab_users:
        users = get_all_users()
        df_u = pd.DataFrame(users)[["id", "username", "full_name", "role", "badge_number", "is_active", "created_at"]]
        df_u.columns = ["ID", "Username", "Full Name", "Assigned Role", "Badge Number", "Active", "Created At"]
        st.dataframe(df_u, use_container_width=True, hide_index=True)

    with tab_audit:
        audits = get_recent_audit_logs(limit=50)
        if audits:
            df_a = pd.DataFrame(audits)[["id", "timestamp", "username", "role", "action", "target_entity", "details", "ip_address"]]
            df_a.columns = ["Log ID", "Timestamp", "Operator", "Role", "Action Performed", "Target Entity", "Details", "IP Address"]
            st.dataframe(df_a, use_container_width=True, hide_index=True)
        else:
            st.info("No audit entries recorded.")


# ---------------------------------------------------------------------------
# Main Routing Logic
# ---------------------------------------------------------------------------
def main():
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    init_app_session()

    routing_engine = get_routing_engine()
    mesh_sim = get_mesh_simulator()

    render_top_header()
    render_sidebar()

    view = st.session_state.active_view

    if view == "Command Center":
        render_command_center(routing_engine, mesh_sim)
    elif view == "Incident Management":
        render_incident_management(routing_engine)
    elif view == "Live Emergency Map":
        render_live_map(routing_engine)
    elif view == "Vehicle Fleet":
        render_vehicle_fleet()
    elif view == "Hospital Coordination":
        render_hospital_coordination()
    elif view == "AI Intelligence":
        render_ai_intelligence()
    elif view == "V2X Mesh Inspector":
        render_mesh_inspector(mesh_sim)
    elif view == "Operations Analytics":
        render_analytics()
    elif view == "Reports & Documentation":
        render_documentation()
    elif view == "Settings & Users":
        render_settings()
    else:
        render_command_center(routing_engine, mesh_sim)


if __name__ == "__main__":
    main()
