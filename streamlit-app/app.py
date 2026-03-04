"""
Chicago 311 Service Delivery Dashboard
From Request to Resolution — Altair Edition

Launch:
    streamlit run streamlit-app/app.py
"""

import os, json, copy
import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

alt.data_transformers.disable_max_rows()

# ─── Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Chicago 311 Dashboard",
    page_icon="🏙️",
    layout="wide",
)

st.markdown("""<style>
.main .block-container { max-width: 1100px; padding-top: 1.5rem; }
#MainMenu, footer { visibility: hidden; }
</style>""", unsafe_allow_html=True)

JOHNSON_DATE = pd.Timestamp("2023-05-15")

# Colors
BLUE = "#5B8DB8"
ORANGE = "#D97B53"
PERIOD_LABELS = ["2021–Apr 2023", "May 2023–2024"]
PERIOD_COLORS = {"2021–Apr 2023": BLUE, "May 2023–2024": ORANGE}
Q_COLORS = {
    "Q1 (Lowest)": "#c0392b", "Q2": "#e67e22", "Q3": "#f1c40f",
    "Q4": "#27ae60", "Q5 (Highest)": "#2980b9",
}
Q_ORDER = ["Q1 (Lowest)", "Q2", "Q3", "Q4", "Q5 (Highest)"]

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "derived-data")


# ─── Data ─────────────────────────────────────────────────────────────────
@st.cache_data
def load_all():
    df = pd.read_csv(os.path.join(DATA_DIR, "311_cleaned.csv"), low_memory=False)
    df["created_date"] = pd.to_datetime(df["created_date"], errors="coerce")
    df["closed_date"] = pd.to_datetime(df["closed_date"], errors="coerce")
    df["year_month"] = df["created_date"].dt.to_period("M").dt.to_timestamp()
    df["period"] = np.where(
        df["created_date"] < JOHNSON_DATE, "2021–Apr 2023", "May 2023–2024"
    )
    df["community_area"] = (
        pd.to_numeric(df["community_area"], errors="coerce")
        .astype("Int64").astype(str)
    )
    ca = pd.read_csv(os.path.join(DATA_DIR, "community_area_stats.csv"))
    ca["area_numbe"] = ca["area_numbe"].astype(str)
    geo_path = os.path.join(DATA_DIR, "community_areas.geojson")
    geo = json.load(open(geo_path)) if os.path.exists(geo_path) else None
    return df, ca, geo


df, ca_stats, geojson = load_all()


# ─── Altair helpers ───────────────────────────────────────────────────────
def johnson_rule():
    """Return a dashed vertical rule + label at the Johnson inauguration date."""
    rule_df = pd.DataFrame({"date": [JOHNSON_DATE]})
    rule = alt.Chart(rule_df).mark_rule(
        strokeDash=[5, 4], color="#888", strokeWidth=1.5
    ).encode(x="date:T")
    label = alt.Chart(rule_df).mark_text(
        align="left", dx=5, dy=-8, fontSize=10, color="#666", text="Johnson Inauguration"
    ).encode(x="date:T")
    return rule + label


PERIOD_SCALE = alt.Scale(
    domain=PERIOD_LABELS,
    range=[BLUE, ORANGE],
)

Q_SCALE = alt.Scale(
    domain=Q_ORDER,
    range=[Q_COLORS[q] for q in Q_ORDER],
)


# ─── Sidebar filters ─────────────────────────────────────────────────────
with st.sidebar:
    st.header("Filters")
    min_yr, max_yr = int(df["year"].min()), int(df["year"].max())
    yr = st.slider("Year Range", min_yr, max_yr, (min_yr, max_yr))

    st.subheader("Service Types")
    mode = st.radio("", ["Top categories", "Custom"], label_visibility="collapsed")
    if mode == "Top categories":
        n = st.slider("Top N", 3, 15, 8)
        sel = df["sr_type"].value_counts().head(n).index.tolist()
    else:
        sel = st.multiselect("Choose", sorted(df["sr_type"].unique()),
                             default=df["sr_type"].value_counts().head(5).index.tolist())

    st.subheader("Income Group")
    q_opts = ["All"] + sorted(df["income_quintile"].dropna().unique())
    sel_q = st.selectbox("Quintile", q_opts)

    st.subheader("Administration")
    per = st.radio("Period", ["Both", "2021–Apr 2023 Only", "May 2023–2024 Only"])

# Apply
m = (df["year"] >= yr[0]) & (df["year"] <= yr[1])
if sel:
    m &= df["sr_type"].isin(sel)
if sel_q != "All":
    m &= df["income_quintile"] == sel_q
if per == "2021–Apr 2023 Only":
    m &= df["period"] == "2021–Apr 2023"
elif per == "May 2023–2024 Only":
    m &= df["period"] == "May 2023–2024"
f = df[m].copy()


# ─── Title ────────────────────────────────────────────────────────────────
st.title("From Request to Resolution")
st.markdown(
    "An interactive look at **328,000+ Chicago 311 service requests (2021–2024)** — "
    "response patterns, the Johnson administration transition, and income-based equity."
)
st.divider()

# KPIs
med = f["response_time_days"].median()
pre_m = f[f["period"] == "2021–Apr 2023"]["response_time_days"].median()
post_m = f[f["period"] == "May 2023–2024"]["response_time_days"].median()
delta = post_m - pre_m if pd.notna(pre_m) and pd.notna(post_m) else None

k1, k2, k3, k4 = st.columns(4)
k1.metric("Total Requests", f"{len(f):,}")
k2.metric("Median Wait", f"{med:.1f} days" if pd.notna(med) else "—",
           delta=f"{delta:+.1f}d" if delta is not None else None, delta_color="inverse")
k3.metric("Completion Rate", f"{(f['status'] == 'Completed').mean() * 100:.1f}%")
k4.metric("Service Types", f"{f['sr_type'].nunique()}")


# ═══════════════════════════════════════════════════════════════════════════
# TABS
# ═══════════════════════════════════════════════════════════════════════════
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Overview", "Response Times", "Equity & Income",
    "Geography", "Neighborhoods",
])


# ═══════════════════════════════════════════════════════════════════════════
# TAB 1: OVERVIEW
# ═══════════════════════════════════════════════════════════════════════════
with tab1:
    # ── Monthly Request Volume ──
    st.subheader("Monthly Request Volume (Count)")
    vol = (f.groupby(["year_month", "period"]).size()
           .reset_index(name="requests")
           .sort_values("year_month"))

    bars = alt.Chart(vol).mark_bar().encode(
        x=alt.X("year_month:T", title="Month"),
        y=alt.Y("requests:Q", title="Number of Requests"),
        color=alt.Color("period:N", scale=PERIOD_SCALE, title="Period"),
        tooltip=[
            alt.Tooltip("year_month:T", title="Month", format="%b %Y"),
            alt.Tooltip("requests:Q", title="Requests", format=","),
            alt.Tooltip("period:N", title="Period"),
        ],
    ).properties(height=380)

    st.altair_chart(bars + johnson_rule(), use_container_width=True)

    # ── Top Service Categories ──
    st.divider()
    st.subheader("Top Service Categories by Request Count")
    tc = (f.groupby("sr_type").size()
          .reset_index(name="requests")
          .nlargest(10, "requests"))
    tc["service"] = tc["sr_type"].str[:40]

    chart = alt.Chart(tc).mark_bar(color=BLUE).encode(
        x=alt.X("requests:Q", title="Number of Requests"),
        y=alt.Y("service:N", sort="-x", title=""),
        tooltip=[
            alt.Tooltip("sr_type:N", title="Service Type"),
            alt.Tooltip("requests:Q", title="Requests", format=","),
        ],
    ).properties(height=380)
    st.altair_chart(chart, use_container_width=True)

    # ── Service Mix Over Time ──
    st.divider()
    st.subheader("Service Request Mix Over Time")
    top6 = f["sr_type"].value_counts().head(6).index.tolist()
    comp = (f[f["sr_type"].isin(top6)]
            .groupby(["year_month", "sr_type"]).size()
            .reset_index(name="requests")
            .sort_values("year_month"))
    if not comp.empty:
        lines = alt.Chart(comp).mark_line(strokeWidth=2).encode(
            x=alt.X("year_month:T", title="Month"),
            y=alt.Y("requests:Q", title="Number of Requests"),
            color=alt.Color("sr_type:N",
                            scale=alt.Scale(scheme="set2"),
                            title="Service Type"),
            tooltip=[
                alt.Tooltip("year_month:T", title="Month", format="%b %Y"),
                alt.Tooltip("sr_type:N", title="Service Type"),
                alt.Tooltip("requests:Q", title="Requests", format=","),
            ],
        ).properties(height=380)
        st.altair_chart(lines + johnson_rule(), use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════
# TAB 2: RESPONSE TIMES
# ═══════════════════════════════════════════════════════════════════════════
with tab2:
    # Period comparison
    c1, c2 = st.columns(2)
    c1.metric("2021–Apr 2023 — Median Wait",
              f"{pre_m:.1f} days" if pd.notna(pre_m) else "—")
    c2.metric("May 2023–2024 — Median Wait",
              f"{post_m:.1f} days" if pd.notna(post_m) else "—")

    # ── Single Service Response Time Drill-Down ──
    st.divider()
    st.subheader("Single Service Response Time Drill-Down")
    avail = f["sr_type"].value_counts().head(15).index.tolist()
    chosen = st.selectbox("Select a service type", avail)
    svc = f[f["sr_type"] == chosen]
    sm = (svc.groupby(["year_month", "period"])["response_time_days"]
          .median().reset_index()
          .sort_values("year_month"))
    sm.columns = ["month", "period", "median_wait"]

    drill_line = alt.Chart(sm).mark_line(strokeWidth=2.5, point=True).encode(
        x=alt.X("month:T", title="Month"),
        y=alt.Y("median_wait:Q", title="Median Response Time (days)"),
        color=alt.Color("period:N", scale=PERIOD_SCALE, title="Period"),
        tooltip=[
            alt.Tooltip("month:T", title="Month", format="%b %Y"),
            alt.Tooltip("median_wait:Q", title="Median Response Time (days)", format=".1f"),
            alt.Tooltip("period:N", title="Period"),
        ],
    ).properties(height=380, title=f"Response Time — {chosen}")
    st.altair_chart(drill_line + johnson_rule(), use_container_width=True)

    # ── Which Services Got Faster or Slower? ──
    st.divider()
    st.subheader("Response Time Shift: Which Services Got Faster or Slower?")
    st.markdown("Change in median response time (days) from 2021–Apr 2023 to May 2023–2024.")

    pre_s = df[df["period"] == "2021–Apr 2023"].groupby("sr_type")["response_time_days"].median()
    post_s = df[df["period"] == "May 2023–2024"].groupby("sr_type")["response_time_days"].median()
    chg = (post_s - pre_s).dropna().reset_index()
    chg.columns = ["service_type", "change_days"]
    chg["count"] = df.groupby("sr_type").size().reindex(chg["service_type"]).values
    chg = chg[chg["count"] > 500].sort_values("change_days")
    chg["direction"] = chg["change_days"].apply(
        lambda x: "Faster" if x < -1 else ("Slower" if x > 1 else "Stable"))
    chg["label"] = chg["service_type"].str[:35]
    # Show top 8 improved + top 8 worsened
    show = pd.concat([chg.head(8), chg.tail(8)]).drop_duplicates()

    shift = alt.Chart(show).mark_bar().encode(
        x=alt.X("change_days:Q", title="Change in Median Wait (days)"),
        y=alt.Y("label:N", sort=alt.EncodingSortField(field="change_days", order="ascending"),
                title=""),
        color=alt.Color("direction:N",
                        scale=alt.Scale(
                            domain=["Faster", "Stable", "Slower"],
                            range=["#27ae60", "#bbb", "#c0392b"]),
                        title="Direction"),
        tooltip=[
            alt.Tooltip("service_type:N", title="Service Type"),
            alt.Tooltip("change_days:Q", title="Change (days)", format=".1f"),
            alt.Tooltip("direction:N", title="Direction"),
        ],
    ).properties(height=max(380, len(show) * 26))

    zero_line = alt.Chart(pd.DataFrame({"x": [0]})).mark_rule(color="#333", strokeWidth=1).encode(
        x="x:Q"
    )
    st.altair_chart(shift + zero_line, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════
# TAB 3: EQUITY & INCOME
# ═══════════════════════════════════════════════════════════════════════════
with tab3:
    f_q = f[f["income_quintile"].notna()].copy()

    q1_wait = f_q[f_q["income_quintile"] == "Q1 (Lowest)"]["response_time_days"].median()
    q5_wait = f_q[f_q["income_quintile"] == "Q5 (Highest)"]["response_time_days"].median()
    if pd.notna(q1_wait) and pd.notna(q5_wait):
        gap = q1_wait - q5_wait
        g1, g2, g3 = st.columns(3)
        g1.metric("Q1 — Lowest Income", f"{q1_wait:.1f} days")
        g2.metric("Q5 — Highest Income", f"{q5_wait:.1f} days")
        g3.metric("Gap", f"{abs(gap):.1f} days {'longer' if gap > 0 else 'shorter'}")

    # ── Median Wait by Income Quintile & Period ──
    st.divider()
    st.subheader("Median Wait by Income Quintile & Period")
    eq = (f_q.groupby(["income_quintile", "period"])["response_time_days"]
          .median().reset_index())
    eq.columns = ["income_quintile", "period", "median_wait"]

    grouped = alt.Chart(eq).mark_bar().encode(
        x=alt.X("income_quintile:N", title="Income Quintile",
                sort=Q_ORDER, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("median_wait:Q", title="Median Wait (days)"),
        color=alt.Color("period:N", scale=PERIOD_SCALE, title="Period"),
        xOffset="period:N",
        tooltip=[
            alt.Tooltip("income_quintile:N", title="Income Quintile"),
            alt.Tooltip("period:N", title="Period"),
            alt.Tooltip("median_wait:Q", title="Median Wait (days)", format=".1f"),
        ],
    ).properties(height=400)
    st.altair_chart(grouped, use_container_width=True)

    # ── Heatmap: Service Type x Income Quintile ──
    st.divider()
    st.subheader("Response Time: Service Type x Income Quintile")
    st.markdown("Darker cells = longer wait.")
    top10 = f_q["sr_type"].value_counts().head(10).index.tolist()
    hd = (f_q[f_q["sr_type"].isin(top10)]
          .groupby(["sr_type", "income_quintile"])["response_time_days"]
          .median().reset_index())
    hd.columns = ["service_type", "income_quintile", "median_wait"]
    hd["service_label"] = hd["service_type"].str[:30]

    if not hd.empty:
        heat = alt.Chart(hd).mark_rect().encode(
            x=alt.X("income_quintile:N", title="Income Quintile", sort=Q_ORDER),
            y=alt.Y("service_label:N", title="Service Type",
                    sort=alt.EncodingSortField(field="median_wait", op="mean", order="descending")),
            color=alt.Color("median_wait:Q",
                            scale=alt.Scale(scheme="orangered"),
                            title="Median Wait (days)"),
            tooltip=[
                alt.Tooltip("service_type:N", title="Service Type"),
                alt.Tooltip("income_quintile:N", title="Income Quintile"),
                alt.Tooltip("median_wait:Q", title="Median Wait (days)", format=".1f"),
            ],
        ).properties(height=max(340, len(top10) * 36), width=600)

        text = alt.Chart(hd).mark_text(fontSize=11, color="white").encode(
            x=alt.X("income_quintile:N", sort=Q_ORDER),
            y=alt.Y("service_label:N",
                    sort=alt.EncodingSortField(field="median_wait", op="mean", order="descending")),
            text=alt.Text("median_wait:Q", format=".0f"),
        )
        st.altair_chart(heat + text, use_container_width=True)

    # ── Request Volume by Income Quintile ──
    st.divider()
    st.subheader("Request Volume by Income Quintile")
    vol_q = (f_q.groupby("income_quintile").size()
             .reset_index(name="requests"))

    vol_bar = alt.Chart(vol_q).mark_bar().encode(
        x=alt.X("income_quintile:N", title="Income Quintile",
                sort=Q_ORDER, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("requests:Q", title="Number of Requests"),
        color=alt.Color("income_quintile:N", scale=Q_SCALE, title="Income Quintile",
                        legend=None),
        tooltip=[
            alt.Tooltip("income_quintile:N", title="Income Quintile"),
            alt.Tooltip("requests:Q", title="Requests", format=","),
        ],
    ).properties(height=350)
    st.altair_chart(vol_bar, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════
# TAB 4: GEOGRAPHY (map kept in Plotly — Altair lacks mapbox support)
# ═══════════════════════════════════════════════════════════════════════════
with tab4:
    if geojson is None:
        st.warning("GeoJSON not found.")
    else:
        import plotly.express as px

        metric = st.radio(
            "Map layer",
            ["Requests per 1K Residents", "Median Wait (days)",
             "Total Requests", "Poverty Rate (%)", "Median Income ($)"],
            horizontal=True,
        )

        cs = (f.groupby("community_area")
              .agg(total=("sr_number", "size"),
                   median_wait=("response_time_days", "median"))
              .reset_index())
        cs = cs.merge(
            ca_stats[["area_numbe", "community", "population", "median_income",
                       "income_quintile", "poverty_rate"]],
            left_on="community_area", right_on="area_numbe", how="left")
        cs["per_1k"] = (cs["total"] / cs["population"] * 1000).round(1)
        cs["poverty_pct"] = (cs["poverty_rate"] * 100).round(1)

        col_map = {
            "Total Requests": "total",
            "Median Wait (days)": "median_wait",
            "Requests per 1K Residents": "per_1k",
            "Median Income ($)": "median_income",
            "Poverty Rate (%)": "poverty_pct",
        }
        scale_map = {
            "total": "YlOrRd", "median_wait": "OrRd", "per_1k": "YlOrBr",
            "median_income": "Greens", "poverty_pct": "Reds",
        }
        mc = col_map[metric]

        # Only show the selected metric in hover
        hover_data_map = {
            "community_area": False,
            "area_numbe": False,
            "total": False,
            "median_wait": False,
            "per_1k": False,
            "median_income": False,
            "poverty_pct": False,
            "income_quintile": False,
            "population": False,
            "poverty_rate": False,
        }
        # Enable only the selected metric
        fmt_map = {
            "total": ":,",
            "median_wait": ":.1f",
            "per_1k": ":.1f",
            "median_income": ":$,.0f",
            "poverty_pct": ":.1f",
        }
        hover_data_map[mc] = fmt_map[mc]

        label_map = {
            "total": "Requests",
            "median_wait": "Median Wait (days)",
            "per_1k": "Per 1K Residents",
            "median_income": "Median Income",
            "poverty_pct": "Poverty Rate (%)",
            "income_quintile": "Income Quintile",
            "community_area": "Area",
            "area_numbe": "Area",
            "population": "Population",
            "poverty_rate": "Poverty Rate",
        }

        fig = px.choropleth_mapbox(
            cs, geojson=geojson, locations="community_area",
            featureidkey="properties.area_numbe", color=mc,
            color_continuous_scale=scale_map[mc],
            mapbox_style="carto-positron",
            center={"lat": 41.8781, "lon": -87.6298}, zoom=9.8, opacity=0.75,
            hover_name="community",
            hover_data=hover_data_map,
            labels=label_map,
        )
        fig.update_layout(
            template="plotly_white",
            height=580,
            font=dict(size=13, color="#222"),
            showlegend=False,
            margin=dict(l=0, r=0, t=10, b=0),
            plot_bgcolor="#fff", paper_bgcolor="#fff",
        )
        st.plotly_chart(fig, use_container_width=True)

        # Top / Bottom
        st.divider()
        t1, t2 = st.columns(2)
        srt = cs.dropna(subset=[mc]).sort_values(mc, ascending=False)
        cols_show = ["community", mc, "income_quintile"]
        labels_show = ["Neighborhood", metric, "Income Quintile"]
        with t1:
            st.markdown("**Highest**")
            top = srt.head(5)[cols_show].copy()
            top.columns = labels_show
            st.dataframe(top.reset_index(drop=True), use_container_width=True, hide_index=True)
        with t2:
            st.markdown("**Lowest**")
            bot = srt.tail(5)[cols_show].copy()
            bot.columns = labels_show
            st.dataframe(bot.reset_index(drop=True), use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════════════════════════════
# TAB 5: NEIGHBORHOODS
# ═══════════════════════════════════════════════════════════════════════════
with tab5:
    st.subheader("Top 20 Neighborhoods by Volume")
    ns = (f.groupby(["community", "income_quintile"])
          .agg(total=("sr_number", "size"),
               med_wait=("response_time_days", "median"),
               pct30=("response_time_days", lambda x: (x > 30).mean() * 100))
          .reset_index().sort_values("total", ascending=False).head(20))
    ns.columns = ["Neighborhood", "Income Quintile", "Requests",
                   "Median Wait (days)", "% Over 30 Days"]
    ns["Median Wait (days)"] = ns["Median Wait (days)"].round(1)
    ns["% Over 30 Days"] = ns["% Over 30 Days"].round(1)
    st.dataframe(
        ns.reset_index(drop=True), use_container_width=True, height=480,
        column_config={
            "Requests": st.column_config.NumberColumn(format="%d"),
            "Median Wait (days)": st.column_config.NumberColumn(format="%.1f"),
            "% Over 30 Days": st.column_config.ProgressColumn(
                min_value=0, max_value=100, format="%.1f%%"),
        },
    )

    # Neighborhood drill-down
    st.divider()
    st.subheader("Neighborhood Deep Dive")
    communities = sorted(f["community"].dropna().unique())
    if len(communities) > 0:
        pick = st.selectbox("Select neighborhood", communities)
        nbr = f[f["community"] == pick]

        n1, n2, n3 = st.columns(3)
        n1.metric("Requests", f"{len(nbr):,}")
        n2.metric("Median Wait", f"{nbr['response_time_days'].median():.1f} days")
        n3.metric("Completed", f"{(nbr['status'] == 'Completed').mean() * 100:.1f}%")

        nc1, nc2 = st.columns(2)
        with nc1:
            st.markdown(f"**Top services in {pick}**")
            svc_n = (nbr.groupby("sr_type").size()
                     .reset_index(name="requests")
                     .nlargest(8, "requests"))
            svc_n["service"] = svc_n["sr_type"].str[:30]
            svc_chart = alt.Chart(svc_n).mark_bar(color=ORANGE).encode(
                x=alt.X("requests:Q", title="Requests"),
                y=alt.Y("service:N", sort="-x", title=""),
                tooltip=[
                    alt.Tooltip("sr_type:N", title="Service Type"),
                    alt.Tooltip("requests:Q", title="Requests", format=","),
                ],
            ).properties(height=320)
            st.altair_chart(svc_chart, use_container_width=True)

        with nc2:
            st.markdown(f"**Monthly trend — {pick}**")
            nm = (nbr.groupby(["year_month", "period"]).size()
                  .reset_index(name="requests")
                  .sort_values("year_month"))
            trend_chart = alt.Chart(nm).mark_bar().encode(
                x=alt.X("year_month:T", title="Month"),
                y=alt.Y("requests:Q", title="Requests"),
                color=alt.Color("period:N", scale=PERIOD_SCALE, title="Period"),
                tooltip=[
                    alt.Tooltip("year_month:T", title="Month", format="%b %Y"),
                    alt.Tooltip("requests:Q", title="Requests", format=","),
                    alt.Tooltip("period:N", title="Period"),
                ],
            ).properties(height=320)
            st.altair_chart(trend_chart, use_container_width=True)


# ── Footer ────────────────────────────────────────────────────────────────
st.divider()
st.caption(
    "**Data:** Chicago 311 Service Requests · American Community Survey · "
    "Community Area Boundaries — "
    "**PPHA 30538** — Iraj Butt, Fatima Hussain, Faizan Rashid"
)
