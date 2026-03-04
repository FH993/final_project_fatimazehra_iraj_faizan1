"""
Shared data loading and helpers for the multi-page Chicago 311 dashboard.
"""

import os
import json
import streamlit as st
import pandas as pd
import numpy as np

JOHNSON_INAUGURATION = pd.Timestamp("2023-05-15")

# Muted, professional palette
PRE_COLOR = "#5B8DB8"
POST_COLOR = "#D97B53"
PERIOD_COLORS = {"Pre-Johnson": PRE_COLOR, "Johnson Admin": POST_COLOR}
QUINTILE_COLORS = {
    "Q1 (Lowest)": "#c0392b",
    "Q2": "#e67e22",
    "Q3": "#f1c40f",
    "Q4": "#27ae60",
    "Q5 (Highest)": "#2980b9",
}
QUINTILE_ORDER = ["Q1 (Lowest)", "Q2", "Q3", "Q4", "Q5 (Highest)"]

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "derived-data")


@st.cache_data
def load_data():
    csv_path = os.path.join(DATA_DIR, "311_cleaned.csv")
    if not os.path.exists(csv_path):
        st.error("Data not found. Run `python code/preprocessing.py` first.")
        st.stop()
    df = pd.read_csv(csv_path, low_memory=False)
    df["created_date"] = pd.to_datetime(df["created_date"], errors="coerce")
    df["closed_date"] = pd.to_datetime(df["closed_date"], errors="coerce")
    df["year_month"] = df["created_date"].dt.to_period("M").dt.to_timestamp()
    df["period"] = np.where(
        df["created_date"] < JOHNSON_INAUGURATION, "Pre-Johnson", "Johnson Admin"
    )
    df["community_area"] = (
        pd.to_numeric(df["community_area"], errors="coerce")
        .astype("Int64").astype(str)
    )
    return df


@st.cache_data
def load_community_stats():
    path = os.path.join(DATA_DIR, "community_area_stats.csv")
    if os.path.exists(path):
        cs = pd.read_csv(path)
        cs["area_numbe"] = cs["area_numbe"].astype(str)
        return cs
    return None


@st.cache_data
def load_geojson():
    path = os.path.join(DATA_DIR, "community_areas.geojson")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return None


def style_fig(fig, height=440, showlegend=True):
    """Consistent, clean chart styling."""
    fig.update_layout(
        template="simple_white",
        height=height,
        font=dict(size=12, color="#333"),
        title_font=dict(size=15, color="#222"),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
            font=dict(size=11), bgcolor="rgba(0,0,0,0)",
        ),
        showlegend=showlegend,
        margin=dict(l=50, r=20, t=60, b=50),
        plot_bgcolor="white", paper_bgcolor="white",
    )
    fig.update_xaxes(showgrid=False, linecolor="#ddd")
    fig.update_yaxes(showgrid=True, gridcolor="#f0f0f0", linecolor="#ddd")
    return fig


def johnson_line(fig):
    """Dashed vertical line for inauguration."""
    fig.add_vline(
        x=JOHNSON_INAUGURATION.timestamp() * 1000,
        line_dash="dot", line_color="#555", line_width=1.5, opacity=0.6,
    )
    fig.add_annotation(
        x=JOHNSON_INAUGURATION, y=1, yref="paper",
        text="Johnson Inauguration", showarrow=False,
        font=dict(size=10, color="#555"), yshift=10,
    )
    return fig


def apply_sidebar_filters(df):
    """Render sidebar filters and return filtered DataFrame."""
    with st.sidebar:
        st.header("Filters")

        st.subheader("Time Period")
        min_yr, max_yr = int(df["year"].min()), int(df["year"].max())
        year_range = st.slider("Year Range", min_yr, max_yr, (min_yr, max_yr))

        st.subheader("Service Types")
        all_types = sorted(df["sr_type"].unique().tolist())
        mode = st.radio("Mode", ["Top categories", "Custom"], label_visibility="collapsed")
        if mode == "Top categories":
            n = st.slider("Top N", 3, 15, 8)
            sel_types = df["sr_type"].value_counts().head(n).index.tolist()
        else:
            top5 = df["sr_type"].value_counts().head(5).index.tolist()
            sel_types = st.multiselect("Choose", all_types, default=top5)

        st.subheader("Income Group")
        q_opts = ["All"] + sorted(df["income_quintile"].dropna().unique().tolist())
        sel_q = st.selectbox("Income Quintile", q_opts)

        st.subheader("Administration")
        period_f = st.radio("Period", ["Both", "Pre-Johnson Only", "Johnson Admin Only"])

    mask = (df["year"] >= year_range[0]) & (df["year"] <= year_range[1])
    if sel_types:
        mask &= df["sr_type"].isin(sel_types)
    if sel_q != "All":
        mask &= df["income_quintile"] == sel_q
    if period_f == "Pre-Johnson Only":
        mask &= df["period"] == "Pre-Johnson"
    elif period_f == "Johnson Admin Only":
        mask &= df["period"] == "Johnson Admin"

    return df[mask].copy(), sel_types


def page_config():
    """Set consistent page config."""
    st.set_page_config(
        page_title="Chicago 311 Dashboard",
        page_icon="🏙️",
        layout="wide",
    )
    st.markdown("""
    <style>
        .main .block-container { max-width: 1100px; padding-top: 1.5rem; }
        #MainMenu, footer { visibility: hidden; }
    </style>
    """, unsafe_allow_html=True)
