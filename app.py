import streamlit as st
import pandas as pd
import plotly.express as px
import os
import re

# Page configuration
st.set_page_config(layout="wide", page_title="Clinical Trial Oversight Dashboard")

# --- UTILITY FUNCTION USING RELATIVE PATHS ---
def get_clean_ai_summary(site_id):
    # Using relative path: looks inside the 'data' folder in your project directory
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
                    # Get raw text and remove asterisks/quotes
                    text = match.group(1).strip()
                    text = text.replace("*", "").replace('"', "")
                    
                    # LOGIC: Find 'Performance' and force a newline before it
                    if "Performance" in text:
                        parts = text.split("Performance")
                        text = f"{parts[0].strip()}\nPerformance {parts[1].strip()}"
                    
                    # Remove potential duplicate headers
                    text = re.sub(r"Site ID: Site \d+", "", text).strip()
                    return text
                    
        return "AI Summary not found for this site."
    except Exception as e:
        return f"Error reading summary: {e}"

# --- DATA LOADING USING RELATIVE PATHS ---
@st.cache_data
def load_data():
    # These paths work as long as the 'data' folder is in the same directory as this script
    subject_df = pd.read_excel("data/interim_unified_subject.xlsx")
    site_df = pd.read_excel("data/Site_Oversight_Final_Report.xlsx")
    country_df = pd.read_excel("data/interim_unified_country.xlsx")
    region_df = pd.read_excel("data/interim_unified_region.xlsx")
    
    mapping = site_df[['Site_ID', 'country', 'region']].drop_duplicates()
    subject_df['Site_ID'] = subject_df['Subject_ID'].str.replace('Subject', 'Site')
    subject_df = subject_df.merge(mapping, on='Site_ID', how='left')
    
    return subject_df, site_df, country_df, region_df

subj, sites, countries, regions = load_data()

# Navigation
page = st.sidebar.selectbox("Go to", ["SUBJECT LEVEL", "SITE LEVEL", "COUNTRY LEVEL", "REGION LEVEL"])

# ---------------------------------------------------------
# 1. SUBJECT LEVEL
# ---------------------------------------------------------
if page == "SUBJECT LEVEL":
    st.title("Patient Performance (Subject Level)")
    
    st.sidebar.header("Filters")
    clean_options = subj['Patient_Clean_Status'].unique()
    clean_filter = st.sidebar.multiselect("Clean Status", options=clean_options, default=clean_options)
    
    block_options = subj['Blocking_Reason'].dropna().unique()
    block_filter = st.sidebar.multiselect("Blocking Reason", options=block_options)
    
    reg_options = subj['region'].dropna().unique()
    reg_filter = st.sidebar.multiselect("Region", options=reg_options, default=reg_options)
    
    cty_options = subj['country'].dropna().unique()
    cty_filter = st.sidebar.multiselect("Country", options=cty_options, default=cty_options)

    filtered_subj = subj[
        (subj['Patient_Clean_Status'].isin(clean_filter)) &
        (subj['region'].isin(reg_filter)) &
        (subj['country'].isin(cty_filter))
    ]
    if block_filter:
        filtered_subj = filtered_subj[filtered_subj['Blocking_Reason'].isin(block_filter)]

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

    st.subheader("Subject Issue Distribution")
    fig = px.bar(
        x=["Total Queries", "Protocol Deviations", "Missing Pages"],
        y=[s_data['Total_Queries'], s_data['Protocol_Deviations'], s_data['Missing_Pages']],
        labels={'x': 'Metric', 'y': 'Count'}, 
        color=["Queries", "Deviations", "Missing"]
    )
    st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------
# 2. SITE LEVEL
# ---------------------------------------------------------
elif page == "SITE LEVEL":
    st.title("Site Operational Oversight")
    
    st.sidebar.header("Filters")
    risk_options = sites['Site_Risk_Status'].unique()
    risk_filter = st.sidebar.multiselect("Risk Status", options=risk_options, default=risk_options)
    
    cty_options = sites['country'].unique()
    cty_filter = st.sidebar.multiselect("Country", options=cty_options, default=cty_options)
    
    reg_options = sites['region'].unique()
    reg_filter = st.sidebar.multiselect("Region", options=reg_options, default=reg_options)
    
    ready_options = sites['Analysis_Readiness'].unique()
    ready_filter = st.sidebar.multiselect("Ready Status", options=ready_options, default=ready_options)

    filtered_sites = sites[
        (sites['Site_Risk_Status'].isin(risk_filter)) &
        (sites['country'].isin(cty_filter)) &
        (sites['region'].isin(reg_filter)) &
        (sites['Analysis_Readiness'].isin(ready_filter))
    ]

    selected_site = st.selectbox("Select Site ID", filtered_sites['Site_ID'].unique())
    site_data = filtered_sites[filtered_sites['Site_ID'] == selected_site].iloc[0]

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Site Overview")
        st.metric("Subject Count", site_data['Subject_Count'])
        st.metric("Avg DQI", f"{site_data['Avg_DQI_Site']:.1f}%")
        st.metric("Open Queries", site_data['Total_Open_Queries'])
        
    with col2:
        st.subheader("Location & Status")
        st.write(f"**Region/Country:** {site_data['region']} / {site_data['country']}")
        st.write(f"**Risk Level:** {site_data['Site_Risk_Status']}")
        st.write(f"**Critical Site:** {site_data['Critical_Site']}")
        st.write(f"**Risk Signals:** {site_data['Risk_Signals']}")

    st.subheader("AI Insight Summary")
    clean_summary = get_clean_ai_summary(selected_site)
    st.text(clean_summary)
    
    st.markdown("---")
    st.warning(f"**Recommended Actions:** {site_data['Recommended_Actions']}")

    fig = px.pie(filtered_sites, names='Site_Risk_Status', title="Risk Distribution Across Filtered Sites")
    st.plotly_chart(fig)

# ---------------------------------------------------------
# 3. COUNTRY LEVEL
# ---------------------------------------------------------
elif page == "COUNTRY LEVEL":
    st.title("Geographic Insights: Country Level")
    
    st.sidebar.header("Filters")
    trend_options = countries['Trend'].unique()
    trend_filter = st.sidebar.multiselect("Trend", options=trend_options, default=trend_options)

    filtered_cty = countries[countries['Trend'].isin(trend_filter)]
    
    st.dataframe(filtered_cty[['country', 'Total_Sites', 'Avg_DQI', 'Pct_Sites_Ready', 'Total_Red_Sites', 'Trend']])

    fig = px.scatter(filtered_cty, x="Avg_DQI", y="Pct_Sites_Ready", size="Total_Sites", color="Trend", hover_name="country")
    st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------
# 4. REGION LEVEL
# ---------------------------------------------------------
else:
    st.title("Executive Summary: Region Level")
    
    st.sidebar.header("Filters")
    trend_options = regions['Trend'].unique()
    trend_filter = st.sidebar.multiselect("Trend", options=trend_options, default=trend_options)

    filtered_reg = regions[regions['Trend'].isin(trend_filter)]
    
    for index, row in filtered_reg.iterrows():
        with st.expander(f"REGION: {row['region']} ({row['Trend']})"):
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Sites", row['Total_Sites'])
            c2.metric("Avg DQI", f"{row['Avg_DQI']:.1f}%")
            c3.metric("Ready Sites (%)", f"{row['Pct_Sites_Ready']:.1f}%")
            st.write(f"**Red Sites Count:** {row['Red_Site_Count']}")

    fig = px.bar(filtered_reg, x="region", y="Total_Sites", color="Trend", barmode="group", title="Site Volume by Region")
    st.plotly_chart(fig, use_container_width=True)