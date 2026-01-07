# Clinical Trial Oversight – End‑to‑End Pipeline

This repository implements an end‑to‑end clinical data oversight pipeline built for the Novartis hackathon, transforming multi‑study EDC exports into an interactive oversight dashboard with deterministic rules, risk signals, and AI‑generated CRA summaries.

---

1. Project Overview

This project ingests raw Excel exports from 23 anonymized clinical studies, unifies them into a master subject‑visit dataset, engineers quality and risk metrics, aggregates to site/country/region, and surfaces insights through a Streamlit dashboard and AI‑generated CRA performance reports.

Core components:

- Data ingestion and harmonization from multiple file types per study into a single CPID spine per study.
- Feature engineering for data quality indicators (DQI), missingness, queries, protocol deviations, and signatures at subject level.
- Multi‑level aggregation into site, country, and region metrics and trends.
- Deterministic oversight flags: Patient Clean Status, Blocking Reason, Site Risk Status (Red/Amber/Green), Analysis Readiness.
- Rule‑driven risk signals and playbook‑based actions (for example, safety escalation, query backlog).
- Generative AI layer that produces per‑site narrative summaries and a CRA site performance report.
- Streamlit dashboard exposing subject, site, country, and region level oversight views.

---

2. Repository Structure

Key files and their roles:

- master_dataset_creation.py  
  - Scans study folders and locates relevant Excel files for each study based on filename patterns like “cpid”, “pages”, “inactivated”, “lab”, “sae”, “meddra”, “whodd”,   “edrr”.
  - Normalizes heterogeneous column names to canonical names using a mapping (for example, “site id”, “site number” to SiteID; “subject name”, “patient id” to SubjectID; “form oid” to FormOID).  
  - Builds a CPID spine per study and uses robust left joins to merge other domains on keys like (SiteID, SubjectID).
  - Concatenates all study‑level spines into a single masterdataset.csv.

- master_cra_creation.py  
  - Reads the master CPID file and CRA‑related sheets and constructs a master CRA dataset linking SiteID and CRAName (Action Owner) to detailed query and issue records.

- combined_query_report.ipynb  
  - Combines raw query exports into a unified cumulative_query_report.xlsx at record level with fields such as Study, Region, Country, Site Number, Subject Name, Folder Name, Form, Field OID, Query Status, Action Owner, days‑since‑open and days‑since‑response metrics.

- phase_1.ipynb  
  - Uses the master CPID dataset and cumulative reports (missing pages, query, non‑conformant) to build a subject‑visit‑form master of roughly 57,974 rows and 101 columns.  
  - Derives core subject, site, country, and region‑level metrics (missing visits, missing pages, queries, protocol deviations, verification and signature status, percentages) and writes:
    - dataset_subject.xlsx (subject level)  
    - dataset_site.xlsx (site level)  
    - dataset_country.xlsx (country level)  
    - dataset_region.xlsx (region level)

- phase_2_3.ipynb  
  - Starts from unified subject‑level metrics and adds PatientCleanStatus, BlockingReason, and DQISubjectScore.  
  - Aggregates to site‑level metrics such as CleanPatientRate, AvgDQISite, HighRiskPatientCount, TotalOpenQueries, TotalSafetyQueries, OpenIssuesperPatient, and SiteRiskStatus (Red/Amber/Green).  
  - Produces interim unified subject and site files (for example, interim_unified_subject.xlsx and unified site outputs).

- phase_4.ipynb  
  - Joins site‑level metrics with geographic mapping (SiteID to country to region) to generate unified country and region datasets with trends, counts of red sites, and readiness percentages.

- phase_5.ipynb  
  - Phase 1: Lock down deterministic business logic for critical subjects, critical sites, DQI, risk status, and analysis readiness.  
  - Phase 2: Rule‑driven agentic AI that generates structured risk signals and recommended actions per site.  
  - Phase 3: Generative AI using a large language model (for example, Gemini 2.5 Flash) to generate CRA and CSM site narratives and write:
    - Site_Oversight_Final_Report.xlsx (per‑site metrics, risk signals, AI summaries)  
    - Full_CRA_Site_Performance_Reports.txt (multi‑site CRA‑oriented report)

- interim_unified_subject.xlsx, interim_unified_site.xlsx, interim_unified_country.xlsx, interim_unified_region.xlsx  
  - Staging outputs used as inputs to phase_5 and the dashboard.

- Site_Oversight_Final_Report.xlsx  
  - Final per‑site oversight table used by the dashboard containing SiteID, CleanPatientRate, AvgDQISite, HighRiskPatientCount, TotalOpenQueries, TotalSafetyQueries, SubjectCount, OpenIssuesperPatient, SiteRiskStatus, CRAName, AnalysisReadiness, country, region, CriticalSite, RiskSignals, RecommendedActions, and AI summaries.

- Full_CRA_Site_Performance_Reports.txt  
  - Human‑readable text summaries by site, including risk color, metrics, risk signals, and recommended actions.

- app3.py (Streamlit app)  
  - Reads unified subject, site, country, and region files and exposes four pages: SUBJECT LEVEL, SITE LEVEL, COUNTRY LEVEL, REGION LEVEL.  
  - Integrates the CRA site performance report file to show AI summaries per site.

---

3. Phase‑by‑Phase Workflow

3.1 Phase 0 – Master Dataset Creation (master_dataset_creation.py)

This phase converts raw multi‑file study exports into a single masterdataset.csv.

Steps:

- Study discovery: iterate over all study folders and identify 23 studies (IDs from 1 to 25 with two missing in between).
- File discovery per study: use keyword patterns to locate CPID spine files and other domains such as visit, lab, SAE, pages, inactivated, MedDRA, WHODrug, and EDRR files.
- Column normalization:  
  - Lower‑case and strip column names.  
  - Map multiple variants to standard keys via a mapping dictionary (for example, “site id” and “site number” to SiteID).
- Robust left joins:  
  - Start from CPID as the spine.  
  - For each domain, perform a safe left join using only keys present on both sides and dropping overlapping columns that are not join keys.
- Concatenation: merge all per‑study spines to form a combined master dataset and write masterdataset.csv.

3.2 Phase 1 – Subject, Site, Country, Region Metrics (phase_1.ipynb)

Phase 1 builds the foundational metrics for oversight across levels.

Key steps:

1. Load base master dataset  
   - Read a unified master Excel file to obtain a subject‑visit dataset with study, region, country, SiteID, SubjectID and several EDC‑derived metrics.

2. Ingest cumulative reports  
   - Missing Pages Report  
   - Query Report  
   - Non‑Conformant Report  
   - Validate shapes to understand coverage of missing pages, queries, and non‑conformant records.

3. Derived core subject‑level flags  
   - MissingVisit  
     - Constructed using expected visit schedule information such as visit name, projected date, and days outstanding, setting MissingVisit = 1 when a visit is expected but not present and overdue.  
   - MissingPages  
     - Rebuild subject‑level counts from the Missing Pages report (group by subject, count missing pages, and merge into the master on SubjectID, filling missing values with 0).  
   - UncodedTerms  
     - Uses coding‑required flags from MedDRA and WHODrug tables to count uncoded terms per subject.  
   - Query and safety metrics  
     - TotalQueries: total query count per subject from the cumulative query report.  
     - SafetyQueries: queries flagged as safety.  
   - CRF and signature/verification metrics  
     - ProblematicCRF: pages requiring verification where CRFs are not frozen or unlocked.  
     - ProtocolDeviations: sum of confirmed and proposed deviations per subject.  
     - CRFNotSigned: CRFs overdue for signatures (0–45 days, 45–90 days, beyond 90 days), plus broken and never signed CRFs.  
     - problematicreviews: count of records needing review (non‑null review status or action status).  
     - MissingCRFDays: total days a page is missing per subject.  
     - OpenIssues: maximum total open issues per subject.  
     - Days Outstanding: maximum days outstanding per subject.

4. Percentage KPIs (subject level)  
   - missingvisitspct = 100 × MissingVisit / Expected Visits (if Expected Visits > 0, else 0).  
   - missingpagespct = 100 × MissingPages / TotalPagesMissingEntered (if denominator > 0, else 0).  
   - openqueriespct = 100 × OpenQueries / TotalQueries (if denominator > 0, else 0).  
   - crfverificationneededpct = 100 × ProblematicCRF / PagesEntered (if denominator > 0, else 0).  
   - crfsignatureneededpct = 100 × CRFNotSigned / PagesEntered (if denominator > 0, else 0).

5. Aggregation by SubjectID  
   - Group subject‑level records by SubjectID, summing counts and averaging percentage columns to produce a clean subject‑level dataset (one row per subject).  
   - Save this as dataset_subject.xlsx.

6. Aggregation by Site, Country, Region  
   - Group by SiteID to create dataset_site.xlsx with aggregated counts and averaged percentage KPIs per site.  
   - Group by country to create dataset_country.xlsx with similar metrics per country.  
   - Group by region (for example, AMERICA, ASIA, EMEA) to create dataset_region.xlsx.

3.3 Phase 2–3 – Patient Clean Status, Blocking Reason, DQI, Site Metrics (phase_2_3.ipynb)

This phase adds cleanliness and scoring logic at subject level and aggregates to site‑level oversight metrics.

3.3.1 PatientCleanStatus and BlockingReason

1. Base columns  
   - Uses a unified subject dataset containing subject‑level counts and percentages for missing visits, missing pages, open queries, safety queries, protocol deviations, CRF signature and verification status, and other counts derived in Phase 1.

2. Clean / Not Clean logic  
   - Define a set of reason columns such as MissingVisit, MissingPages, OpenQueries, SafetyQueries, crfverificationneededpct, crfsignatureneededpct, and ProtocolDeviations.  
   - PatientCleanStatus:  
     - Clean if all reason columns are zero (no missing data, no open or safety queries, no pending verification or signatures, and no protocol deviations).  
     - Not Clean otherwise.
   - BlockingReason:  
     - For each subject, collect all reason columns with values greater than zero and join their names into a comma‑separated string (for example, “MissingPages, Open Queries, crfsignatureneededpct, ProtocolDeviations”).  
     - For clean subjects, set BlockingReason to None.

3.3.2 DQISubjectScore (DQI with Safety Cap Logic)

DQISubjectScore is a 0–100 data quality index defined per subject.

1. Base score  
   - Initialize score = 100 for each subject.

2. Scalar deductions per subject  
   - Missing visits: 5 points per missing visit.  
   - Open queries: 1.5 points per open query.  
   - Unsigned CRFs: 1 point per unsigned CRF (CRFNotSigned).  
   - Unverified pages: 1 point per problematic review record (problematicreviews).  
   - Protocol deviations: 4 points per protocol deviation.

3. Safety cap logic  
   - If SafetyQueries > 0:  
     - Apply a flat deduction of 20 points.  
     - Cap the score at 60 (score = min(score, 60)).

4. Final bounding  
   - Ensure the score is not negative by taking max(0, score).  
   - Store the result as DQISubjectScore in the unified subject dataset.

Interpretation:

- 90–100: high‑quality subjects with minimal issues.  
- 70–89: moderate quality with some issues.  
- 60–69: borderline subjects near escalation.  
- Below 60: high‑risk subjects included in HighRiskPatientCount at site level.

3.3.3 Site‑Level Aggregation and Traffic Lights

1. Subject–site linkage  
   - Build a mapping from SubjectID to SiteID using the Phase 1 dataset and merge it into the subject‑level dataset to attach each subject to a site.

2. Site metrics (group by SiteID)  
   For each site:

   - CleanPatientRate = 100 × proportion of subjects with PatientCleanStatus == “Clean”.
   - AvgDQISite = mean DQISubjectScore across all subjects at that site.
   - HighRiskPatientCount = count of subjects with DQISubjectScore < 60.
   - TotalOpenQueries = sum of open queries across subjects at the site.
   - TotalSafetyQueries = sum of safety queries across subjects at the site.
   - SubjectCount = number of subjects at the site.
   - OpenIssuesperPatient = TotalOpenQueries / SubjectCount.

3. SiteRiskStatus (Red / Amber / Green)

Rules:

- Red: AvgDQISite < 60 or TotalSafetyQueries > 0.  
- Amber: 60 ≤ AvgDQISite < 80 and no safety queries.  
- Green: AvgDQISite ≥ 80 and TotalSafetyQueries == 0.

4. CRA performance linkage  
   - Merge site‑level metrics with CRA master data to attach CRAName per site, enabling CRA‑focused reporting.

The resulting site metrics serve as inputs to later phases and to the dashboard.

---

4. Phase 4 – Country and Region‑Level Trends (phase_4.ipynb)

Phase 4 aggregates site metrics to country and region levels and derives trend indicators.

1. Mapping SiteID to country and region  
   - Using Phase 1 data and mapping logic, each SiteID is associated with a country and region (for example, US in AMERICA, IND in ASIA, FRA in EMEA).

2. Country‑level aggregations  
   - For each country:  
     - AvgDQI: mean DQISite across sites in the country.  
     - TotalRedSites: count of sites with SiteRiskStatus == Red.  
     - TotalSites: total site count.  
     - ReadySitesCount: number of sites marked AnalysisReadiness == Ready.  
     - PctSitesReady: 100 × ReadySitesCount / TotalSites.  
     - Trend: categorical indicator (for example, Improving, Stable, Worsening) based on DQI and readiness patterns.

3. Region‑level aggregations  
   - For each region (for example, AMERICA, ASIA, EMEA):  
     - AvgDQI, RedSiteCount, TotalSites, ReadySitesCount, PctSitesReady, Trend.

These country and region metrics feed the geographic insights pages in the dashboard.

---

5. Phase 5 – Lock‑Down Logic, Risk Signals, and AI (phase_5.ipynb)

Phase 5 finalizes deterministic rules, generates risk signals and operational recommendations, and uses generative AI for narrative oversight.

5.1 Lock Down Deterministic Business Logic

1. CriticalSubject  
   - A subject is considered CriticalSubject if at least one of:  
     - DQISubjectScore < 85  
     - SafetyQueries > 0  
     - OpenQueries > 0

2. CriticalSite  
   - A site is CriticalSite if any of:  
     - AvgDQISite < 70  
     - TotalSafetyQueries > 0  
     - TotalOpenQueries > 5

3. AnalysisReadiness  

A site is Ready if:

- SiteRiskStatus is Green.  
- CriticalSite is False.  
- CleanPatientRate is sufficiently high (for example, around or above 70–80 percent).  
- TotalOpenQueries is low and TotalSafetyQueries == 0.

Otherwise the site is Not Ready.

AnalysisReadiness is stored in the final site oversight file and used both in the dashboard and in aggregated country and region readiness metrics.

5.2 Risk Signals and Playbook (Rule‑Driven Agentic AI)

Risk signals provide a structured, machine‑interpretable summary of site risk state.

1. Risk signal extraction  

Given a site row, risk signals are built as:

- RED_SITE_IMMEDIATE_ACTION if SiteRiskStatus == Red.  
- SAFETY_ESCALATION if TotalSafetyQueries > 0.  
- LOW_DQI if AvgDQISite < 70.  
- QUERY_BACKLOG if TotalOpenQueries > 20.

These signals are stored in a RiskSignals field as a list per site.

2. Action playbook  

Signals are mapped to recommended actions:

- RED_SITE_IMMEDIATE_ACTION → Immediate CRA outreach and site action plan required.  
- SAFETY_ESCALATION → Escalate to safety team within 24 hours.  
- LOW_DQI → Focused data cleaning and monitoring visit required.  
- QUERY_BACKLOG → Query aging review and resolution plan.

For each site, RecommendedActions contains the set of recommended operational steps based on its signals.

3. Dashboard tag  

A simplified tag for UI display:

- If SiteRiskStatus is Red, tag like “Immediate Action Required”.  
- If Amber, tag like “Monitor Closely”.  
- Otherwise, “On Track”.

This tag is used for quick visual interpretation and in AI prompts.

5.3 Generative AI Summaries

1. Priority site selection  
   - Filter to Red and Amber sites to focus AI summarization on locations that need attention.

2. Prompt templates  

Two main prompt styles:

- CRA prompt: oriented toward operational site‑level actions for CRAs (visit planning, follow‑up, remediation).  
- CSM prompt: oriented toward higher‑level study oversight for clinical study managers (trends, escalations, readiness narrative).

3. Batch generation  

- Sites are processed in batches (for example, 5 sites per call), with structured lines describing per‑site metrics and risk signals, which are passed to the language model to generate text summaries.  
- The model response is parsed to associate each summary back to the correct SiteID.

4. Single‑site summary extraction  

- For each site, a function extracts only that site’s text segment from the batched AI summary and stores it as an individual narrative.  
- Simple cases like “Site on track.” are retained as is for low‑risk Green sites.

5. Export  

Final outputs:

- Site_Oversight_Final_Report.xlsx with deterministic metrics, risk signals, recommended actions, and AI summaries per site.  
- Full_CRA_Site_Performance_Reports.txt containing formatted multi‑site CRA reports, including metrics, signals, actions, and AI narrative paragraphs.

---

6. Derived Metrics and Concepts

6.1 DQI (Data Quality Index)

Definition: DQISubjectScore is a 0–100 score that quantifies per‑subject data quality using missing visits, missing pages, queries, signatures, verifications, and protocol deviations, with an additional safety cap.

Components:

- Base score: 100 points.  
- Deductions:  
  - 5 points per missing visit.  
  - 1.5 points per open query.  
  - 1 point per unsigned CRF.  
  - 1 point per unverified page.  
  - 4 points per protocol deviation.
- Safety cap: if SafetyQueries > 0, apply a 20‑point deduction and cap the score at 60.  
- Final: clamp at 0 minimum.

This design ensures safety‑impacted subjects cannot be scored as high‑quality even if other metrics appear good.

6.2 Patient Clean Status and Blocking Reason

PatientCleanStatus:

- Clean: no missing visits or pages, no open or safety queries, no protocol deviations, no pending signature or verification.
- Not Clean: at least one of these issues present.

BlockingReason:

- For Not Clean subjects, a comma‑separated list of the specific non‑zero blocking metrics such as MissingPages, Open Queries, crfsignatureneededpct, or ProtocolDeviations.  
- For Clean subjects, stored as None.

This provides a transparent explanation of why a subject is not analysis‑ready.

6.3 Site Risk Status (Red, Amber, Green)

Derived from site‑level DQI and safety query burden:

- Red: AvgDQISite < 60 or any safety queries.  
- Amber: 60 ≤ AvgDQISite < 80 and no safety queries.  
- Green: AvgDQISite ≥ 80 and no safety queries.

This classification is used in filters, charts, and risk signals.

6.4 Analysis Readiness

Analysis readiness is a site‑level gate indicating if data at the site is fit for analysis and lock.

Conditions to be Ready typically include:

- Green SiteRiskStatus.  
- CriticalSite flag is False.  
- Adequate CleanPatientRate (a high fraction of clean subjects).  
- Low query burden and zero safety queries.

Sites not meeting these thresholds are marked Not Ready and appear as such in the dashboard and in country/region readiness statistics.

6.5 Country and Region Trends

Country level (interim_unified_country):

- AvgDQI: average of AvgDQISite across sites in the country.  
- TotalRedSites and TotalSites.  
- ReadySitesCount and PctSitesReady.  
- Trend label, often based on the balance of ready versus red sites and progression of readiness.

Region level (interim_unified_region):

- AvgDQI, RedSiteCount, TotalSites, ReadySitesCount, PctSitesReady, Trend per region.

These metrics back the geographic visuals and trend filters in the COUNTRY LEVEL and REGION LEVEL dashboard pages.

6.6 Risk Signals and Risk‑Based Actions

Risk signals summarize site risk state:

- RED_SITE_IMMEDIATE_ACTION when SiteRiskStatus is Red.  
- SAFETY_ESCALATION when TotalSafetyQueries > 0.  
- LOW_DQI when AvgDQISite < 70.  
- QUERY_BACKLOG when TotalOpenQueries > 20.

The action playbook maps these signals to specific next steps:

- Immediate CRA outreach and site action plan for RED_SITE_IMMEDIATE_ACTION.  
- Escalation to safety team within 24 hours for SAFETY_ESCALATION.  
- Focused data cleaning and monitoring visit for LOW_DQI.  
- Query aging review and resolution plan for QUERY_BACKLOG.

These are combined into RecommendedActions, which are used both in the dashboard and in CRA reports.

---

7. Dashboard – How to Run

The Streamlit dashboard in app3.py expects final unified files and the CRA report in a specified directory.

7.1 Prerequisites

- Python 3.9 or newer.  
- Libraries: streamlit, pandas, plotly‑express.

Example installation:

```bash```
pip install streamlit pandas plotly-express

7.2 File Layout for Dashboard

Place the following in a folder referenced in app3.py (for example, C/dashboard/):

- unifiedsubject.xlsx → interim_unified_subject.xlsx exported from Phase 2–3 or Phase 5.

- OversightFinalReport.xlsx → Site_Oversight_Final_Report.xlsx (renamed or copied).

- unifiedcountry.xlsx → interim_unified_country.xlsx.

- unifiedregion.xlsx → interim_unified_region.xlsx.

- CRASitePerformanceReports.txt → Full_CRA_Site_Performance_Reports.txt (renamed).

If your directory differs, adjust the paths in app3.py accordingly.

7.3 Running the Dashboard

Run:

bash
streamlit run app3.py
Open the local URL that Streamlit prints (for example, http://localhost:8501).

7.4 Dashboard Pages

7.4.1 SUBJECT LEVEL

- Filters: Clean Status (PatientCleanStatus), Blocking Reason, Region, Country.

- Metrics cards for a selected subject: DQI Score, missing visits percentage, missing pages percentage, open queries percentage, verification needed percentage, signature needed percentage, total queries, safety queries.

- Patient Status text shows Clean Status and Blocking Reason.

- Subject Issue Distribution bar chart compares Total Queries, Protocol Deviations, and Missing Pages.

7.4.2 SITE LEVEL

- Filters: Risk Status (SiteRiskStatus), Country, Region, Ready Status (AnalysisReadiness).

- Site Overview metrics: Subject Count, Avg DQI, Total Open Queries.

- Location Status: Region and Country, Risk Level, Critical Site flag, Risk Signals.

- Recommended Actions panel filled from the playbook.

- AI Insight Summary text from the CRA performance report file.

- Risk distribution pie chart of SiteRiskStatus across filtered sites.

7.4.3 COUNTRY LEVEL

- Filters: Region, Trend.

- Table: country, TotalSites, AvgDQI, PctSitesReady, TotalRedSites, Trend.

- Scatter plot: AvgDQI vs PctSitesReady, bubble size by TotalSites, color by Trend.

7.4.4 REGION LEVEL

- Filters: Trend.

- Expanders with metrics per region: TotalSites, AvgDQI, Ready site percentage, RedSiteCount.

- Bar chart of TotalSites by region, colored by Trend.

8. End‑to‑End Execution Order

- Run master_dataset_creation.py to produce masterdataset.csv from raw study files.

- Run master_cra_creation.py to build the CRA master dataset.

- Run combined_query_report.ipynb to generate cumulative_query_report.xlsx from raw query exports.

- Run phase_1.ipynb to compute subject, site, country, and region metrics and write dataset_subject.xlsx, dataset_site.xlsx, dataset_country.xlsx, and dataset_region.xlsx.

- Run phase_2_3.ipynb to add PatientCleanStatus, BlockingReason, DQISubjectScore and aggregate to site metrics with SiteRiskStatus and CRAName, producing interim subject and site unified datasets.

- Run phase_4.ipynb to derive interim_unified_country.xlsx and interim_unified_region.xlsx with geographic trends and readiness metrics.

- Run phase_5.ipynb to lock down CriticalSubject, CriticalSite, AnalysisReadiness, generate RiskSignals and RecommendedActions, create AI summaries, and export Site_Oversight_Final_Report.xlsx and - Full_CRA_Site_Performance_Reports.txt.

- Place the exported unified files and CRA report where app3.py expects them and run streamlit run app3.py to launch the dashboard.

This flow covers the complete pipeline from raw EDC exports to interactive oversight and AI‑augmented CRA reporting.
