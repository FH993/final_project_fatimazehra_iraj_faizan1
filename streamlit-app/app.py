"""
Chicago 311 Service Delivery Dashboard
From Request to Resolution: An interactive exploration of how Chicago
responds to its residents' needs — and who waits the longest.

Launch:
    streamlit run streamlit-app/app.py
"""

import os
import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

# Config
st.set_page_config(
    page_title="From Request to Resolution | Chicago 311",
    page_icon=":cityscape:",
    layout="wide",
)

alt.data_transformers.disable_max_rows()

JOHNSON_INAUGURATION = pd.Timestamp("2023-05-15")

# Data loading (cached)
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "derived-data")


@st.cache_data
def load_data():
    csv_path = os.path.join(DATA_DIR, "311_cleaned.csv")
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path, low_memory=False)
    else:
        st.error("Data not found. Run `python code/preprocessing.py` first.")
        st.stop()
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


# Inauguration annotation helpers
rule_df = pd.DataFrame({"date": [JOHNSON_INAUGURATION]})


def inaug_rule():
    return (
        alt.Chart(rule_df)
        .mark_rule(color="black", strokeDash=[4, 4], strokeWidth=2)
        .encode(x="date:T")
    )


def inaug_text():
    return (
        alt.Chart(rule_df)
        .mark_text(align="left", dx=5, dy=-10, fontSize=11, fontWeight="bold")
        .encode(x="date:T", text=alt.value("Johnson Inauguration"))
    )

# Load data
df = load_data()
ca_stats = load_community_stats()

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
st.sidebar.header("Explore the Data")
st.sidebar.markdown(
    "Use the controls below to focus on specific service types, "
    "time periods, or income groups."
)

# Service type checkboxes — top 5
st.sidebar.subheader("Service Types")
top_types = df["sr_type"].value_counts().head(5).index.tolist()

selected_types = []
for stype in top_types:
    if st.sidebar.checkbox(stype, value=True, key=f"cb_{stype}"):
        selected_types.append(stype)

st.sidebar.divider()

# Date range
st.sidebar.subheader("Time Period")
min_date = df["created_date"].min().date()
max_date = df["created_date"].max().date()
date_range = st.sidebar.slider(
    "Date Range", min_value=min_date, max_value=max_date,
    value=(min_date, max_date), format="YYYY-MM",
)

st.sidebar.divider()

# Income quintile
st.sidebar.subheader("Neighborhood Income")
quintiles = ["All"] + sorted(df["income_quintile"].dropna().unique().tolist())
selected_quintile = st.sidebar.selectbox("Income Quintile", quintiles)

# ---------------------------------------------------------------------------
# Apply filters
# ---------------------------------------------------------------------------
if selected_types:
    mask = (
        df["sr_type"].isin(selected_types)
        & (df["created_date"].dt.date >= date_range[0])
        & (df["created_date"].dt.date <= date_range[1])
    )
else:
    mask = (
        (df["created_date"].dt.date >= date_range[0])
        & (df["created_date"].dt.date <= date_range[1])
    )
if selected_quintile != "All":
    mask &= df["income_quintile"] == selected_quintile
filtered = df[mask].copy()


# ---------------------------------------------------------------------------
# Title & Introduction
# ---------------------------------------------------------------------------
st.title("From Request to Resolution")
st.markdown(
    "### How does Chicago respond when its residents ask for help?"
)
st.markdown(
    "Every year, hundreds of thousands of Chicagoans dial **311** to report "
    "potholes, request garbage pickup, flag broken streetlights, and more. "
    "Each request generates a timestamped record: *when* the call was made, "
    "*what* was requested, *where* the problem is, and *when* (or if) it was "
    "resolved."
)
st.markdown(
    "This dashboard uses **326,000+ service requests from 2021--2024** to ask "
    "a simple question: **is the city getting better or worse at serving its "
    "residents?** We pay special attention to the transition between "
    "administrations --- Mayor Brandon Johnson took office in May 2023 --- "
    "and to whether lower-income neighborhoods wait longer for the same services."
)

# Key metrics
st.markdown("---")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Requests Selected", f"{len(filtered):,}")
med_resp = filtered["response_time_days"].median()
col2.metric("Median Wait (days)", f"{med_resp:.1f}" if pd.notna(med_resp) else "N/A")
col3.metric("Service Types", f"{filtered['sr_type'].nunique()}")
n_areas = filtered["community_area"].nunique()
col4.metric("Neighborhoods", f"{n_areas}")
st.markdown("---")

# ---------------------------------------------------------------------------
# Section 1: Demand — Volume & Composition
# ---------------------------------------------------------------------------
st.header("1. Demand: What Is the City Being Asked to Do?")
st.markdown(
    "Before examining performance, we need to understand the **scale and "
    "composition** of demand. Which services generate the most requests? "
    "Has the volume changed over time? A spike in hard-to-resolve categories "
    "could slow response times even without any policy change."
)

# Sorted bar chart of volume by service type (Fig 3 / sorted_bar_volume)
type_counts = (
    filtered.groupby("sr_type").size().reset_index(name="count")
    .nlargest(15, "count")
)
if not type_counts.empty:
    bar_chart = (
        alt.Chart(type_counts)
        .mark_bar(color="steelblue")
        .encode(
            x=alt.X("count:Q", title="Number of Requests"),
            y=alt.Y("sr_type:N",
                     sort=alt.EncodingSortField(field="count", order="descending"),
                     title="Service Type"),
            tooltip=[
                alt.Tooltip("sr_type:N", title="Type"),
                alt.Tooltip("count:Q", title="Count", format=","),
            ],
        )
        .properties(width="container", height=400)
    )
    st.altair_chart(bar_chart, use_container_width=True)
    st.caption(
        "Service categories ranked by total volume. A small number of types "
        "dominate the workload — improvements here have the largest citywide impact."
    )

# Request volume time series (Fig 2 / request_volume)
total_pop = ca_stats["population"].sum() if ca_stats is not None else 1
vol = filtered.groupby("year_month").size().reset_index(name="count")
if not vol.empty:
    vol["per_1k"] = vol["count"] / total_pop * 1000
    vol_chart = (
        alt.Chart(vol)
        .mark_line(color="steelblue", point=True)
        .encode(
            x=alt.X("year_month:T", title="Month"),
            y=alt.Y("per_1k:Q", title="Requests per 1,000 Residents"),
            tooltip=[
                alt.Tooltip("year_month:T", format="%Y-%m"),
                alt.Tooltip("per_1k:Q", title="Per 1k", format=".2f"),
                alt.Tooltip("count:Q", title="Count", format=","),
            ],
        ).properties(width="container", height=350)
    )
    st.altair_chart(vol_chart + inaug_rule() + inaug_text(), use_container_width=True)
    st.caption(
        "Monthly request volume normalised by population. Seasonal patterns are "
        "evident, with summer months typically seeing higher demand."
    )

# ---------------------------------------------------------------------------
# Section 2: Response Times — Time Series (Fig 1 / regime_time_series)
# ---------------------------------------------------------------------------
st.markdown("---")
st.header("2. Response Times: Is the City Getting Faster or Slower?")
st.markdown(
    "The most direct measure of service quality is **how long residents wait** "
    "from the moment they submit a request to the moment the city closes it. "
    "The chart below tracks median response time month by month for each "
    "selected service type, with the mayoral transition marked."
)

monthly = (
    filtered.groupby(["year_month", "sr_type"])["response_time_days"]
    .median().reset_index()
)
if not monthly.empty:
    lines = (
        alt.Chart(monthly).mark_line(point=True)
        .encode(
            x=alt.X("year_month:T", title="Month"),
            y=alt.Y("response_time_days:Q", title="Median Response Time (days)"),
            color=alt.Color("sr_type:N", title="Service Type"),
            tooltip=[
                alt.Tooltip("year_month:T", title="Month", format="%Y-%m"),
                alt.Tooltip("sr_type:N", title="Type"),
                alt.Tooltip("response_time_days:Q", title="Median (days)", format=".1f"),
            ],
        )
    )
    chart = (lines + inaug_rule() + inaug_text()).properties(
        width="container", height=450
    )
    st.altair_chart(chart, use_container_width=True)
    st.caption(
        "The dashed line marks Mayor Johnson's inauguration (May 2023). "
        "Seasonal spikes and cross-category divergence are visible."
    )
else:
    st.info("No data for the selected filters. Select at least one service type.")

# ---------------------------------------------------------------------------
# Section 3: Equity — Who waits the longest? (Fig 4 concentration curve)
# ---------------------------------------------------------------------------
st.markdown("---")
st.header("3. Equity: Do Lower-Income Neighborhoods Wait Longer?")
st.markdown(
    "A core promise of municipal government is that **all residents receive "
    "the same quality of service** regardless of where they live. The "
    "concentration curve below tests whether slow requests (>30 days) are "
    "spread equally across neighborhoods or concentrated in lower-income areas."
)

# Equity gap metric
q1 = filtered[filtered["income_quintile"] == "Q1 (Lowest)"][
    "response_time_days"
].median()
q5 = filtered[filtered["income_quintile"] == "Q5 (Highest)"][
    "response_time_days"
].median()
if pd.notna(q1) and pd.notna(q5):
    gap = q1 - q5
    st.markdown("#### The Equity Gap at a Glance")
    c1, c2, c3 = st.columns(3)
    c1.metric("Q1 (Lowest Income)", f"{q1:.1f} days")
    c2.metric("Q5 (Highest Income)", f"{q5:.1f} days")
    c3.metric(
        "Gap (Q1 - Q5)", f"{gap:+.1f} days",
        delta=f"{gap:+.1f} days", delta_color="inverse",
    )
    if gap > 0:
        st.markdown(
            f"Residents in the **lowest-income** quintile wait **{gap:.1f} more days** "
            f"on average than those in the highest-income quintile for the same types "
            f"of city services."
        )

# Concentration curve (Fig 4 / concentration_curve)
if ca_stats is not None:
    conc_records = []
    for period in ["Pre-Johnson", "Johnson Admin"]:
        period_df = filtered[filtered["period"] == period]
        slow = (
            period_df[period_df["response_time_days"] > 30]
            .groupby("community_area").size().reset_index(name="slow_count")
        )
        merged = ca_stats.merge(
            slow, left_on="area_numbe", right_on="community_area", how="left"
        )
        merged["slow_count"] = merged["slow_count"].fillna(0)
        merged = merged[merged["median_income"] > 0]
        merged = merged.sort_values("median_income").reset_index(drop=True)
        total_slow = merged["slow_count"].sum()
        if total_slow > 0:
            merged["cum_areas"] = np.arange(1, len(merged) + 1) / len(merged)
            merged["cum_slow"] = merged["slow_count"].cumsum() / total_slow
            for _, row in merged.iterrows():
                conc_records.append({
                    "period": period,
                    "cum_areas": row["cum_areas"],
                    "cum_slow": row["cum_slow"],
                })

    if conc_records:
        conc_df = pd.concat([
            pd.DataFrame([
                {"period": "Pre-Johnson", "cum_areas": 0, "cum_slow": 0},
                {"period": "Johnson Admin", "cum_areas": 0, "cum_slow": 0},
            ]),
            pd.DataFrame(conc_records),
        ], ignore_index=True)

        conc_chart = (
            alt.Chart(conc_df).mark_line(strokeWidth=2.5)
            .encode(
                x=alt.X("cum_areas:Q",
                         title="Cumulative Share of Areas (poorest first)"),
                y=alt.Y("cum_slow:Q",
                         title="Cumulative Share of Slow Requests (>30 days)"),
                color=alt.Color("period:N", title="Period",
                                scale=alt.Scale(
                                    domain=["Pre-Johnson", "Johnson Admin"],
                                    range=["#1f77b4", "#ff7f0e"])),
            ).properties(width="container", height=400)
        )
        eq_ref = (
            alt.Chart(pd.DataFrame({"x": [0, 1], "y": [0, 1]}))
            .mark_line(strokeDash=[4, 4], color="grey")
            .encode(x="x:Q", y="y:Q")
        )
        st.altair_chart(conc_chart + eq_ref, use_container_width=True)
        st.caption(
            "If delays were spread equally, the curve would follow the diagonal. "
            "A curve above the diagonal means poorer areas bear more delays."
        )

# ---------------------------------------------------------------------------
# Closing
# ---------------------------------------------------------------------------
st.markdown("---")
st.markdown(
    "### What This Means"
)
st.markdown(
    "The patterns above are **descriptive, not causal** --- we cannot attribute "
    "changes to any single policy or administration. But the data highlights "
    "actionable priorities: service categories that consistently lag, "
    "and income-based disparities that persist across administrations. "
    "These are starting points for deeper operational review."
)

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.divider()
st.caption(
    "Data: Chicago 311 Service Requests (City of Chicago Data Portal) | "
    "American Community Survey (U.S. Census Bureau) | "
    "PPHA 30538 Final Project --- Iraj Butt, Fatima Hussain, Faizan Rashid"
)
