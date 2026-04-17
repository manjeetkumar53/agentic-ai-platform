"""
Agentic AI Platform — Analytics Dashboard

Run from repo root:
    streamlit run dashboard/app.py

Expects the FastAPI server to be running on http://localhost:8000 (configurable
via the PLATFORM_BASE_URL env var or the sidebar input field).
"""
from __future__ import annotations

import os
import time

import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Agentic AI Platform · Analytics",
    page_icon="🤖",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Sidebar — connection settings
# ---------------------------------------------------------------------------

with st.sidebar:
    st.title("⚙️ Settings")
    base_url = st.text_input(
        "Platform API URL",
        value=os.getenv("PLATFORM_BASE_URL", "http://localhost:8000"),
    )
    refresh_interval = st.selectbox(
        "Auto-refresh (seconds)",
        options=[0, 5, 10, 30, 60],
        index=2,
        format_func=lambda v: "off" if v == 0 else f"{v}s",
    )
    max_events = st.slider("Max events to fetch", 50, 1000, 200, step=50)
    st.divider()
    st.caption("Agentic AI Platform — Day 5")


# ---------------------------------------------------------------------------
# Data fetchers
# ---------------------------------------------------------------------------

@st.cache_data(ttl=5)
def fetch_health(base_url: str) -> dict:
    try:
        r = requests.get(f"{base_url}/health", timeout=3)
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}


@st.cache_data(ttl=5)
def fetch_summary(base_url: str) -> dict:
    try:
        r = requests.get(f"{base_url}/v1/metrics/summary", timeout=3)
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        return {}


@st.cache_data(ttl=5)
def fetch_events(base_url: str, limit: int) -> list[dict]:
    try:
        r = requests.get(f"{base_url}/v1/eval/events", params={"limit": limit}, timeout=5)
        r.raise_for_status()
        return r.json().get("events", [])
    except Exception as exc:
        return []


@st.cache_data(ttl=5)
def fetch_breaker(base_url: str) -> dict:
    try:
        r = requests.get(f"{base_url}/v1/circuit-breaker/status", timeout=3)
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        return {}


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.title("🤖 Agentic AI Platform · Analytics")
st.caption(f"Connected to: `{base_url}`")

health = fetch_health(base_url)
status = health.get("status", "unknown")
color  = "green" if status == "ok" else "red"
st.markdown(f"**API status:** :{color}[{status}]")

if status != "ok":
    st.error(f"Cannot reach platform API at {base_url}. Start it with `uvicorn app.main:app --reload`.")
    st.stop()

# ---------------------------------------------------------------------------
# Summary KPIs
# ---------------------------------------------------------------------------

summary = fetch_summary(base_url)
breaker = fetch_breaker(base_url)

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Total Requests",    summary.get("request_count", 0))
k2.metric("Avg Latency (ms)",  f"{summary.get('avg_latency_ms', 0):.1f}")
k3.metric("Avg Cost (USD)",    f"${summary.get('avg_cost_usd', 0):.6f}")
k4.metric("Total Cost (USD)",  f"${summary.get('total_cost_usd', 0):.4f}")
k5.metric("Fallbacks",         summary.get("fallback_count", 0))

st.divider()

# ---------------------------------------------------------------------------
# Circuit breaker badge
# ---------------------------------------------------------------------------

breaker_state = breaker.get("state", "UNKNOWN")
badge_color   = {"CLOSED": "green", "OPEN": "red", "HALF_OPEN": "orange"}.get(breaker_state, "gray")
st.markdown(f"**Circuit Breaker:** :{badge_color}[{breaker_state}]")

st.divider()

# ---------------------------------------------------------------------------
# Event-level charts (need at least 1 event)
# ---------------------------------------------------------------------------

events = fetch_events(base_url, max_events)

if not events:
    st.info("No telemetry events yet. Send a request to `/v1/agent/run` to populate the dashboard.")
else:
    import pandas as pd

    df = pd.DataFrame(events)
    df["created_at"] = pd.to_datetime(df["created_at"])
    df = df.sort_values("created_at")

    col_left, col_right = st.columns(2)

    # ── Requests over time (line) ──────────────────────────────────────────
    with col_left:
        st.subheader("Requests Over Time")
        df_time = df.set_index("created_at").resample("1min").size().reset_index(name="count")
        fig = px.line(df_time, x="created_at", y="count", markers=True,
                      labels={"created_at": "Time", "count": "Requests"})
        fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=250)
        st.plotly_chart(fig, width="stretch")

    # ── Provider mix (pie) ─────────────────────────────────────────────────
    with col_right:
        st.subheader("Provider Mix")
        provider_counts = df["provider"].value_counts().reset_index()
        provider_counts.columns = ["provider", "count"]
        fig = px.pie(provider_counts, values="count", names="provider", hole=0.4)
        fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=250)
        st.plotly_chart(fig, width="stretch")

    col_left2, col_right2 = st.columns(2)

    # ── Latency distribution (histogram) ──────────────────────────────────
    with col_left2:
        st.subheader("Latency Distribution (ms)")
        fig = px.histogram(df, x="latency_ms", nbins=20,
                           labels={"latency_ms": "Latency (ms)"})
        fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=250)
        st.plotly_chart(fig, width="stretch")

    # ── Cost trend (area) ─────────────────────────────────────────────────
    with col_right2:
        st.subheader("Cost Trend (USD)")
        df["cumulative_cost"] = df["estimated_cost_usd"].cumsum()
        fig = px.area(df, x="created_at", y="cumulative_cost",
                      labels={"created_at": "Time", "cumulative_cost": "Cumulative Cost (USD)"})
        fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=250)
        st.plotly_chart(fig, width="stretch")

    # ── Fallback rate & tool usage ─────────────────────────────────────────
    col_left3, col_right3 = st.columns(2)

    with col_left3:
        st.subheader("Fallback Rate")
        fallback_counts = df["fallback_used"].value_counts().reset_index()
        fallback_counts.columns = ["fallback", "count"]
        fallback_counts["label"] = fallback_counts["fallback"].map({True: "Fallback", False: "Primary"})
        fig = px.bar(fallback_counts, x="label", y="count", color="label",
                     color_discrete_map={"Fallback": "#ef4444", "Primary": "#22c55e"},
                     labels={"label": "", "count": "Requests"})
        fig.update_layout(showlegend=False, margin=dict(l=0, r=0, t=10, b=0), height=250)
        st.plotly_chart(fig, width="stretch")

    with col_right3:
        st.subheader("Tool Usage per Request")
        tool_dist = df["tool_count"].value_counts().sort_index().reset_index()
        tool_dist.columns = ["tools_used", "count"]
        tool_dist["label"] = tool_dist["tools_used"].astype(str) + " tool(s)"
        fig = px.bar(tool_dist, x="label", y="count",
                     labels={"label": "Tools Selected", "count": "Requests"})
        fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=250)
        st.plotly_chart(fig, width="stretch")

    # ── Provider metrics table ─────────────────────────────────────────────
    st.subheader("Provider Metrics")
    by_provider = summary.get("by_provider", {})
    if by_provider:
        rows = []
        for provider, value in by_provider.items():
            # value may be an int (request count) or a dict with detailed metrics
            if isinstance(value, dict):
                rows.append({
                    "Provider":       provider,
                    "Requests":       value.get("request_count", 0),
                    "Avg Latency ms": f"{value.get('avg_latency_ms', 0):.1f}",
                    "Avg Cost USD":   f"${value.get('avg_cost_usd', 0):.6f}",
                    "Total Cost USD": f"${value.get('total_cost_usd', 0):.4f}",
                })
            else:
                rows.append({"Provider": provider, "Requests": int(value)})
        st.dataframe(rows, width="stretch")

    # ── Raw event log ──────────────────────────────────────────────────────
    with st.expander("Raw Event Log"):
        display_df = df[["created_at", "request_id", "provider", "latency_ms",
                          "tokens_in", "tokens_out", "estimated_cost_usd",
                          "fallback_used", "tool_count"]].copy()
        display_df["request_id"] = display_df["request_id"].str[:8] + "…"
        st.dataframe(display_df, width="stretch")

# ---------------------------------------------------------------------------
# Auto-refresh
# ---------------------------------------------------------------------------

if refresh_interval > 0:
    time.sleep(refresh_interval)
    st.rerun()
