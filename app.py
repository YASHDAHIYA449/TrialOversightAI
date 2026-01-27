import streamlit as st
import pandas as pd
import plotly.express as px
import streamlit_antd_components as sac
import numpy as np
from datetime import datetime, timedelta
import os
import re

st.caption("Clinical Trial Oversight Dashboard | Version 2.0 | Jan 2026")
# -------------------------------------------------------
# PAGE CONFIG
# -------------------------------------------------------
st.set_page_config(layout="wide", page_title="Clinical Trial Oversight Dashboard")

# -------------------------------------------------------
# UTILITY FUNCTIONS
# -------------------------------------------------------
def empty_state(df):
    if df.empty:
        st.warning("⚠️ No data found for these filters. Please adjust your selection.")
        st.stop()


def get_clean_ai_summary(site_id):
    file_path = os.path.join("data", "Full_CRA_Site_Performance_Reports.txt")

    if not os.path.exists(file_path):
        return "Summary file not found."

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        sections = content.split("--------------------------------------------------")
        target_id = str(site_id).replace("Site ", "").strip()

        for section in sections:
            if f"Site {target_id}" in section:
                match = re.search(r"AI Summary:\s*(.*)", section, re.DOTALL)
                if match:
                    text = match.group(1).strip()
                    text = text.replace("*", "").replace('"', "")

                    if "Performance" in text:
                        parts = text.split("Performance")
                        text = f"{parts[0].strip()}\nPerformance {parts[1].strip()}"

                    text = re.sub(r"Site ID: Site \d+", "", text).strip()
                    return text

        return "AI Summary not found for this site."
    except Exception as e:
        return f"Error reading summary: {e}"


# -------------------------------------------------------
# DATA LOADING
# -------------------------------------------------------
@st.cache_data
def load_data():
    subject_df = pd.read_excel("data/interim_unified_subject.xlsx")
    site_df = pd.read_excel("data/Site_Oversight_Final_Report.xlsx")
    country_df = pd.read_excel("data/interim_unified_country.xlsx")
    region_df = pd.read_excel("data/interim_unified_region.xlsx")

    mapping = site_df[['Site_ID', 'country', 'region']].drop_duplicates()
    subject_df['Site_ID'] = subject_df['Subject_ID'].str.replace('Subject', 'Site')
    subject_df = subject_df.merge(mapping, on='Site_ID', how='left')

    return subject_df, site_df, country_df, region_df


subj, sites, countries, regions = load_data()

# -------------------------------------------------------
# HORIZONTAL MENU
# -------------------------------------------------------
menu = sac.menu(
    items=[
        sac.MenuItem('Executive Overview', icon='speedometer'),
        sac.MenuItem('Subject Level', icon='person'),
        sac.MenuItem('Site Level', icon='hospital'),
        sac.MenuItem('Country Level', icon='geo-alt'),
        sac.MenuItem('Region Level', icon='map')
    ],
    format_func='title',
    size='md',
    open_all=True
)

if menu == "Subject Level":
    page = "SUBJECT LEVEL"
elif menu == "Site Level":
    page = "SITE LEVEL"
elif menu == "Country Level":
    page = "COUNTRY LEVEL"
elif menu == "Region Level":
    page = "REGION LEVEL"
else:
    page = "EXECUTIVE OVERVIEW"

# =======================================================
# EXECUTIVE OVERVIEW
# =======================================================
if page == "EXECUTIVE OVERVIEW":
    st.title("🌍 Global Clinical Trial Executive Overview")

    total_sites = sites.shape[0]
    total_subjects = subj.shape[0]
    red_sites = sites[sites["Site_Risk_Status"].str.lower().isin(["red", "high risk"])].shape[0]
    global_dqi = sites["Avg_DQI_Site"].mean()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🏥 Total Sites", total_sites)
    c2.metric("🧍 Total Subjects", total_subjects)
    c3.metric("🚨 High Risk Sites", red_sites)
    st.caption(f"High Risk Sites represent {red_sites/total_sites*100:.1f}% of all sites globally.")
    c4.metric("📊 Global DQI", f"{global_dqi:.1f}%")

    st.subheader("🔥 Risk Concentration Heatmap (Normalized by Risk Category)")

    heat_df = sites.groupby(["region", "Site_Risk_Status"]).size().unstack(fill_value=0)

    # Enforce correct order
    risk_order = ["Green", "Amber", "Red"]
    heat_df = heat_df.reindex(columns=risk_order, fill_value=0)

    # Normalize column-wise
    heat_norm = heat_df.copy()
    for col in heat_norm.columns:
        if heat_norm[col].max() != 0:
            heat_norm[col] = heat_norm[col] / heat_norm[col].max()

    fig = px.imshow(
        heat_norm,
        aspect="auto",
        color_continuous_scale=[
            [0, "#e8f5e9"],
            [0.5, "#ffeb3b"],
            [1, "#d32f2f"]
        ],
        title="Risk Distribution Heatmap (Relative Intensity per Risk Type)"
    )

    # Add numeric annotations manually
    for i, region in enumerate(heat_df.index):
        for j, risk in enumerate(heat_df.columns):
            fig.add_annotation(
                x=j,
                y=i,
                text=str(heat_df.iloc[i, j]),
                showarrow=False,
                font=dict(color="black", size=12)
            )

    fig.update_layout(
        xaxis=dict(
            tickmode="array",
            tickvals=list(range(len(heat_df.columns))),
            ticktext=heat_df.columns,
            title="Site Risk Status"
        ),
        yaxis=dict(
            tickmode="array",
            tickvals=list(range(len(heat_df.index))),
            ticktext=heat_df.index,
            title="Region"
        ),
        height=450,
        font=dict(size=14)
    )

    st.plotly_chart(fig, use_container_width=True)


# =======================================================
# SUBJECT LEVEL
# =======================================================
elif page == "SUBJECT LEVEL":
    st.title("Patient Performance (Subject Level)")

    st.sidebar.header("Filters")
    clean_filter = st.sidebar.multiselect(
        "Clean Status",
        options=subj['Patient_Clean_Status'].unique(),
        default=subj['Patient_Clean_Status'].unique()
    )

    block_filter = st.sidebar.multiselect(
        "Blocking Reason",
        options=subj['Blocking_Reason'].dropna().unique()
    )

    reg_filter = st.sidebar.multiselect(
        "Region",
        options=subj['region'].dropna().unique(),
        default=subj['region'].dropna().unique()
    )

    cty_filter = st.sidebar.multiselect(
        "Country",
        options=subj['country'].dropna().unique(),
        default=subj['country'].dropna().unique()
    )

    filtered_subj = subj[
        (subj['Patient_Clean_Status'].isin(clean_filter)) &
        (subj['region'].isin(reg_filter)) &
        (subj['country'].isin(cty_filter))
    ]

    if block_filter:
        filtered_subj = filtered_subj[filtered_subj['Blocking_Reason'].isin(block_filter)]

    empty_state(filtered_subj)

    selected_subject = st.selectbox("Select Subject ID", filtered_subj['Subject_ID'].unique())
    s_data = filtered_subj[filtered_subj['Subject_ID'] == selected_subject].iloc[0]

    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("Patient Overview")
        metrics = {
            "DQI Score": f"{s_data['DQI_Subject_Score']:.1f}%",
            "Missing Visits": f"{s_data['missing_visits_pct']:.1f}%",
            "Missing Pages": f"{s_data['missing_pages_pct']:.1f}%",
            "Open Queries": f"{s_data['open_queries_pct']:.1f}%",
            "Verification Needed": f"{s_data['crf_verification_needed_pct']:.1f}%",
            "Signature Needed": f"{s_data['crf_signature_needed_pct']:.1f}%",
            "Total Queries": s_data['Total_Queries'],
            "Safety Queries": s_data['Safety_Queries']
        }
        cols = st.columns(4)
        for i, (k, v) in enumerate(metrics.items()):
            cols[i % 4].metric(k, v)

    with col2:
        st.subheader("Patient Status")
        st.write(f"**Clean Status:** {s_data['Patient_Clean_Status']}")
        st.write(f"**Blocking Reason:** {s_data['Blocking_Reason']}")

# =======================================================
# SITE LEVEL
# =======================================================
elif page == "SITE LEVEL":
    st.title("Site Operational Oversight")

    st.sidebar.header("Filters")
    risk_filter = st.sidebar.multiselect(
        "Risk Status",
        options=sites['Site_Risk_Status'].unique(),
        default=sites['Site_Risk_Status'].unique()
    )

    cty_filter = st.sidebar.multiselect(
        "Country",
        options=sites['country'].unique(),
        default=sites['country'].unique()
    )

    reg_filter = st.sidebar.multiselect(
        "Region",
        options=sites['region'].unique(),
        default=sites['region'].unique()
    )

    ready_filter = st.sidebar.multiselect(
        "Ready Status",
        options=sites['Analysis_Readiness'].unique(),
        default=sites['Analysis_Readiness'].unique()
    )

    filtered_sites = sites[
        (sites['Site_Risk_Status'].isin(risk_filter)) &
        (sites['country'].isin(cty_filter)) &
        (sites['region'].isin(reg_filter)) &
        (sites['Analysis_Readiness'].isin(ready_filter))
    ]

    empty_state(filtered_sites)

    selected_site = st.selectbox("Select Site ID", filtered_sites['Site_ID'].unique())
    site_data = filtered_sites[filtered_sites['Site_ID'] == selected_site].iloc[0]

    st.subheader("AI Risk Intelligence")

    risk = site_data["Site_Risk_Status"]
    if risk == "High Risk":
        st.error("🚨 CRITICAL RISK SITE")
    elif risk == "Medium Risk":
        st.warning("⚠️ MODERATE RISK SITE")
    else:
        st.success("✅ HEALTHY SITE")

    clean_summary = get_clean_ai_summary(selected_site)

    st.markdown("### 🧠 AI Insight Summary")
    st.info(clean_summary)

    st.markdown("### 📌 Recommended Actions")
    st.warning(site_data["Recommended_Actions"])

    colA, colB = st.columns(2)
    with colA:
        if st.button("📨 Send Alert to CRA"):
            st.toast("Mock Alert Sent to CRA!", icon="🚀")
    with colB:
        if st.button("📅 Schedule Monitoring Visit"):
            st.toast("Mock Visit Scheduled!", icon="📅")

    st.markdown("## 🗓 Trial Progress Timeline")

    gantt_data = pd.DataFrame({
        "Phase": ["Start-Up", "Enrollment", "Monitoring", "Close-Out"],
        "Start": [
            datetime.today() - timedelta(days=180),
            datetime.today() - timedelta(days=120),
            datetime.today() - timedelta(days=60),
            datetime.today() + timedelta(days=30),
        ],
        "Finish": [
            datetime.today() - timedelta(days=120),
            datetime.today() - timedelta(days=60),
            datetime.today() + timedelta(days=30),
            datetime.today() + timedelta(days=90),
        ]
    })

    fig = px.timeline(gantt_data, x_start="Start", x_end="Finish", y="Phase")
    fig.update_yaxes(autorange="reversed")
    st.plotly_chart(fig, use_container_width=True)

# =======================================================
# COUNTRY LEVEL
# =======================================================
elif page == "COUNTRY LEVEL":
    st.title("Geographic Insights: Country Level")

    trend_filter = st.sidebar.multiselect(
        "Trend",
        options=countries['Trend'].unique(),
        default=countries['Trend'].unique()
    )

    filtered_cty = countries[countries['Trend'].isin(trend_filter)]
    empty_state(filtered_cty)

    st.dataframe(filtered_cty)

    fig = px.scatter(
        filtered_cty,
        x="Avg_DQI",
        y="Pct_Sites_Ready",
        size="Total_Sites",
        color="Trend",
        hover_name="country"
    )
    st.plotly_chart(fig, use_container_width=True)

# =======================================================
# REGION LEVEL
# =======================================================
elif page == "REGION LEVEL":
    st.title("Executive Summary: Region Level")

    trend_filter = st.sidebar.multiselect(
        "Trend",
        options=regions['Trend'].unique(),
        default=regions['Trend'].unique()
    )

    filtered_reg = regions[regions['Trend'].isin(trend_filter)]
    empty_state(filtered_reg)

    for _, row in filtered_reg.iterrows():
        with st.expander(f"REGION: {row['region']} ({row['Trend']})"):
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Sites", row['Total_Sites'])
            c2.metric("Avg DQI", f"{row['Avg_DQI']:.1f}%")
            c3.metric("Ready Sites (%)", f"{row['Pct_Sites_Ready']:.1f}%")
            st.write(f"**Red Sites Count:** {row['Red_Site_Count']}")

    fig = px.bar(
        filtered_reg,
        x="region",
        y="Total_Sites",
        color="Trend",
        barmode="group",
        title="Site Volume by Region"
    )
    st.plotly_chart(fig, use_container_width=True)