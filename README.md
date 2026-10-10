# Clinical Trial Oversight: End-to-End Pipeline

An end-to-end clinical data oversight pipeline built for the Novartis hackathon. It transforms multi-study EDC exports into an interactive oversight dashboard with deterministic rules, risk signals, and AI-generated CRA summaries.

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Repository Structure](#2-repository-structure)
3. [Phase-by-Phase Workflow](#3-phase-by-phase-workflow)
4. [Key Definitions](#4-key-definitions)
5. [Dashboard: How to Run](#5-dashboard-how-to-run)
6. [End-to-End Execution Order](#6-end-to-end-execution-order)
7. [Version 2.0 Features (Jan 2026 Update)](#7-version-20-features-jan-2026-update)

---

## 1. Project Overview

The project ingests raw Excel exports from **23 anonymized clinical studies**, unifies them into a master subject-visit dataset, engineers quality and risk metrics, aggregates to site / country / region level, and surfaces insights through a Streamlit dashboard and AI-generated CRA performance reports.

**Core components**

- Data ingestion and harmonization from multiple file types per study into a single CPID spine per study
- Feature engineering for data quality indicators (DQI), missingness, queries, protocol deviations, and signatures at subject level
- Multi-level aggregation into site, country, and region metrics and trends
- Deterministic oversight flags: Patient Clean Status, Blocking Reason, Site Risk Status (Red/Amber/Green), Analysis Readiness
- Rule-driven risk signals and playbook-based actions (e.g., safety escalation, query backlog)
- Generative AI layer that produces per-site narrative summaries and a CRA site performance report
- Streamlit dashboard exposing subject, site, country, and region level oversight views

---

## 2. Repository Structure

| File | Role |
|:--|:--|
| `master_dataset_creation.py` | Scans study folders, locates relevant Excel files per study using filename patterns (`cpid`, `pages`, `inactivated`, `lab`, `sae`, `meddra`, `whodd`, `edrr`), normalizes heterogeneous column names to canonical names (e.g., "site id" / "site number" → `SiteID`), builds a CPID spine per study, merges other domains with robust left joins on `(SiteID, SubjectID)`, and concatenates all spines into `masterdataset.csv` |
| `master_cra_creation.py` | Reads the master CPID file and CRA-related sheets and builds a master CRA dataset linking `SiteID` and `CRAName` (Action Owner) to detailed query and issue records |
| `combined_query_report.ipynb` | Combines raw query exports into a unified record-level `cumulative_query_report.xlsx` (Study, Region, Country, Site Number, Subject Name, Folder Name, Form, Field OID, Query Status, Action Owner, days-since-open, days-since-response) |
| `phase_1.ipynb` | Builds a subject-visit-form master (~57,974 rows, 101 columns) and derives subject, site, country, and region metrics. Writes `dataset_subject.xlsx`, `dataset_site.xlsx`, `dataset_country.xlsx`, `dataset_region.xlsx` |
| `phase_2_3.ipynb` | Adds `PatientCleanStatus`, `BlockingReason`, and `DQISubjectScore`; aggregates to site-level metrics and `SiteRiskStatus`; produces interim unified subject and site files |
| `phase_4.ipynb` | Joins site metrics with the geographic mapping (SiteID → country → region) to produce unified country and region datasets with trends, red-site counts, and readiness percentages |
| `phase_5.ipynb` | Locks down deterministic business logic, generates risk signals and recommended actions, and produces AI summaries |
| `interim_unified_{subject,site,country,region}.xlsx` | Staging outputs used as inputs to `phase_5` and the dashboard |
| `Site_Oversight_Final_Report.xlsx` | Final per-site oversight table used by the dashboard (metrics, `SiteRiskStatus`, `CRAName`, `AnalysisReadiness`, `CriticalSite`, `RiskSignals`, `RecommendedActions`, AI summaries, country, region) |
| `Full_CRA_Site_Performance_Reports.txt` | Human-readable summaries by site: risk color, metrics, risk signals, and recommended actions |
| `app3.py` | Streamlit app with four pages (SUBJECT, SITE, COUNTRY, REGION LEVEL); integrates the CRA report file to show AI summaries per site |

---

## 3. Phase-by-Phase Workflow

### 3.1 Phase 0: Master Dataset Creation (`master_dataset_creation.py`)

Converts raw multi-file study exports into a single `masterdataset.csv`.

- **Study discovery:** iterates over all study folders and identifies 23 studies (IDs 1 to 25, with two missing in between)
- **File discovery per study:** keyword patterns locate the CPID spine and other domains (visit, lab, SAE, pages, inactivated, MedDRA, WHODrug, EDRR)
- **Column normalization:** lower-cases and strips column names, then maps variants to standard keys via a mapping dictionary
- **Robust left joins:** starts from CPID as the spine; for each domain, joins only on keys present on both sides and drops overlapping non-key columns
- **Concatenation:** merges all per-study spines into the combined master dataset

### 3.2 Phase 1: Subject, Site, Country, Region Metrics (`phase_1.ipynb`)

1. **Load the base master dataset:** a subject-visit dataset with study, region, country, `SiteID`, `SubjectID`, and EDC-derived metrics.
2. **Ingest cumulative reports:** Missing Pages, Query, and Non-Conformant reports, validating shapes to understand coverage.
3. **Derive subject-level flags**

   | Metric | Definition |
   |:--|:--|
   | `MissingVisit` | 1 when a visit is expected (visit name, projected date, days outstanding) but not present and overdue |
   | `MissingPages` | Subject-level counts rebuilt from the Missing Pages report, merged on `SubjectID`, nulls filled with 0 |
   | `UncodedTerms` | Count of uncoded terms per subject, from coding-required flags in MedDRA and WHODrug tables |
   | `TotalQueries` / `SafetyQueries` | Total queries per subject / queries flagged as safety |
   | `ProblematicCRF` | Pages requiring verification where CRFs are not frozen or unlocked |
   | `ProtocolDeviations` | Sum of confirmed and proposed deviations |
   | `CRFNotSigned` | CRFs overdue for signature (0–45, 45–90, 90+ days), plus broken and never-signed CRFs |
   | `problematicreviews` | Records needing review (non-null review or action status) |
   | `MissingCRFDays` | Total days a page is missing per subject |
   | `OpenIssues`, `Days Outstanding` | Maximum total open issues / maximum days outstanding per subject |

4. **Percentage KPIs (subject level)** (each is 0 when the denominator is 0)
   - `missingvisitspct = 100 × MissingVisit / Expected Visits`
   - `missingpagespct = 100 × MissingPages / TotalPagesMissingEntered`
   - `openqueriespct = 100 × OpenQueries / TotalQueries`
   - `crfverificationneededpct = 100 × ProblematicCRF / PagesEntered`
   - `crfsignatureneededpct = 100 × CRFNotSigned / PagesEntered`
5. **Aggregate by `SubjectID`:** sum counts and average percentage columns to one row per subject → `dataset_subject.xlsx`.
6. **Aggregate by site, country, region:** `dataset_site.xlsx`, `dataset_country.xlsx`, `dataset_region.xlsx` (regions such as AMERICA, ASIA, EMEA).

### 3.3 Phase 2–3: Clean Status, Blocking Reason, DQI, Site Metrics (`phase_2_3.ipynb`)

**PatientCleanStatus and BlockingReason**

- Reason columns: `MissingVisit`, `MissingPages`, `OpenQueries`, `SafetyQueries`, `crfverificationneededpct`, `crfsignatureneededpct`, `ProtocolDeviations`
- `PatientCleanStatus` is **Clean** if all reason columns are zero, otherwise **Not Clean**
- `BlockingReason` is a comma-separated list of the non-zero reason columns (e.g., "MissingPages, Open Queries, crfsignatureneededpct, ProtocolDeviations"); `None` for clean subjects

**DQISubjectScore (0–100, with safety cap)**

1. Start at 100.
2. Deduct 5 per missing visit, 1.5 per open query, 1 per unsigned CRF, 1 per unverified page (`problematicreviews`), and 4 per protocol deviation.
3. If `SafetyQueries > 0`: deduct a flat 20 and cap the score at 60.
4. Clamp at a minimum of 0.

| Score | Interpretation |
|:--|:--|
| 90–100 | High-quality subjects with minimal issues |
| 70–89 | Moderate quality with some issues |
| 60–69 | Borderline, near escalation |
| < 60 | High-risk; counted in `HighRiskPatientCount` at site level |

**Site-level aggregation** (group by `SiteID`, after mapping each subject to its site)

- `CleanPatientRate` = 100 × share of subjects with `PatientCleanStatus == "Clean"`
- `AvgDQISite` = mean `DQISubjectScore` at the site
- `HighRiskPatientCount` = subjects with `DQISubjectScore < 60`
- `TotalOpenQueries`, `TotalSafetyQueries` = sums across subjects
- `SubjectCount` = number of subjects at the site
- `OpenIssuesperPatient` = `TotalOpenQueries / SubjectCount`
- `CRAName` is attached by merging with the CRA master data

**SiteRiskStatus (Red / Amber / Green)**

| Status | Rule |
|:--|:--|
| 🔴 Red | `AvgDQISite < 60` or `TotalSafetyQueries > 0` |
| 🟠 Amber | `60 ≤ AvgDQISite < 80` and no safety queries |
| 🟢 Green | `AvgDQISite ≥ 80` and `TotalSafetyQueries == 0` |

### 3.4 Phase 4: Country and Region Trends (`phase_4.ipynb`)

Each `SiteID` is mapped to a country and region (e.g., US → AMERICA, IND → ASIA, FRA → EMEA), then aggregated:

- **Country level:** `AvgDQI`, `TotalRedSites`, `TotalSites`, `ReadySitesCount`, `PctSitesReady` (= 100 × `ReadySitesCount` / `TotalSites`), and `Trend` (Improving / Stable / Worsening, based on DQI and readiness patterns)
- **Region level:** `AvgDQI`, `RedSiteCount`, `TotalSites`, `ReadySitesCount`, `PctSitesReady`, `Trend`

These feed the geographic pages of the dashboard.

### 3.5 Phase 5: Lock-Down Logic, Risk Signals, and AI (`phase_5.ipynb`)

**Deterministic business logic**

- **CriticalSubject:** `DQISubjectScore < 85` or `SafetyQueries > 0` or `OpenQueries > 0`
- **CriticalSite:** `AvgDQISite < 70` or `TotalSafetyQueries > 0` or `TotalOpenQueries > 5`
- **AnalysisReadiness:** a site is **Ready** if `SiteRiskStatus` is Green, `CriticalSite` is False, `CleanPatientRate` is sufficiently high, and open queries are low with zero safety queries; otherwise **Not Ready**. See also the stricter "90-0-80" rule in [Version 2.0](#7-version-20-features-jan-2026-update).

**Risk signals and playbook (rule-driven agentic AI)**

| Signal | Trigger | Recommended action |
|:--|:--|:--|
| `RED_SITE_IMMEDIATE_ACTION` | `SiteRiskStatus == Red` | Immediate CRA outreach and site action plan required |
| `SAFETY_ESCALATION` | `TotalSafetyQueries > 0` | Escalate to the safety team within 24 hours |
| `LOW_DQI` | `AvgDQISite < 70` | Focused data cleaning and monitoring visit required |
| `QUERY_BACKLOG` | `TotalOpenQueries > 20` | Query aging review and resolution plan |

Signals are stored per site in `RiskSignals`, and the matching steps in `RecommendedActions`. A simplified dashboard tag is derived from risk status: Red → "Immediate Action Required", Amber → "Monitor Closely", otherwise "On Track".

**Generative AI summaries**

1. **Priority selection:** Red and Amber sites are summarized.
2. **Prompt templates:** a *CRA prompt* (operational: visit planning, follow-up, remediation) and a *CSM prompt* (study oversight: trends, escalations, readiness).
3. **Batch generation:** sites are sent in batches (e.g., 5 per call) as structured lines of metrics and risk signals to an LLM (e.g., Gemini 2.5 Flash); responses are parsed back to the correct `SiteID`.
4. **Single-site extraction:** each site's text segment is extracted from the batched output; simple cases like "Site on track." are kept as-is for low-risk Green sites.
5. **Export:** `Site_Oversight_Final_Report.xlsx` (metrics, signals, actions, AI summaries) and `Full_CRA_Site_Performance_Reports.txt` (multi-site CRA report).

---

## 4. Key Definitions

- **DQI (Data Quality Index):** a 0–100 per-subject score built from missing visits, missing pages, queries, signatures, verifications, and protocol deviations, with a safety cap. The cap ensures safety-impacted subjects can never score as high-quality even if other metrics look good.
- **Patient Clean Status / Blocking Reason:** transparent explanation of why a subject is not analysis-ready.
- **Site Risk Status:** Red / Amber / Green from site-level DQI and safety query burden; used in filters, charts, and risk signals.
- **Analysis Readiness:** a site-level gate showing whether data at the site is fit for analysis and lock. Not Ready sites are flagged in the dashboard and in country/region readiness statistics.
- **Country and region trends:** `AvgDQI`, red-site counts, and readiness percentages that back the COUNTRY LEVEL and REGION LEVEL pages.

---

## 5. Dashboard: How to Run

The Streamlit dashboard in `app3.py` expects the final unified files and the CRA report in a specified directory.

**Prerequisites**

- Python 3.9 or newer
- Libraries: `streamlit`, `pandas`, `plotly-express`

```bash
pip install streamlit pandas plotly-express
```

**File layout**

Place the following in the folder referenced in `app3.py` (e.g., `C/dashboard/`), adjusting the paths in `app3.py` if your directory differs:

| Expected by the app | Source file |
|:--|:--|
| `unifiedsubject.xlsx` | `interim_unified_subject.xlsx` (from Phase 2–3 or Phase 5) |
| `OversightFinalReport.xlsx` | `Site_Oversight_Final_Report.xlsx` (renamed or copied) |
| `unifiedcountry.xlsx` | `interim_unified_country.xlsx` |
| `unifiedregion.xlsx` | `interim_unified_region.xlsx` |
| `CRASitePerformanceReports.txt` | `Full_CRA_Site_Performance_Reports.txt` (renamed) |

**Run**

```bash
streamlit run app3.py
```

Open the local URL that Streamlit prints (e.g., `http://localhost:8501`).

**Dashboard pages**

| Page | Contents |
|:--|:--|
| **SUBJECT LEVEL** | Filters: Clean Status, Blocking Reason, Region, Country. Metric cards for a selected subject (DQI score, missing visits / pages %, open queries %, verification and signature needed %, total and safety queries). Patient status text. Issue distribution bar chart (Total Queries, Protocol Deviations, Missing Pages) |
| **SITE LEVEL** | Filters: Risk Status, Country, Region, Ready Status. Site overview (Subject Count, Avg DQI, Total Open Queries). Location status (region, country, risk level, critical flag, risk signals). Recommended Actions panel. AI Insight Summary from the CRA report. Risk distribution pie chart |
| **COUNTRY LEVEL** | Filters: Region, Trend. Table of country, TotalSites, AvgDQI, PctSitesReady, TotalRedSites, Trend. Scatter plot of AvgDQI vs PctSitesReady (bubble size = TotalSites, color = Trend) |
| **REGION LEVEL** | Filter: Trend. Expanders with metrics per region (TotalSites, AvgDQI, ready site %, RedSiteCount). Bar chart of TotalSites by region, colored by Trend |

---

## 6. End-to-End Execution Order

1. Run `master_dataset_creation.py` to produce `masterdataset.csv` from the raw study files.
2. Run `master_cra_creation.py` to build the CRA master dataset.
3. Run `combined_query_report.ipynb` to generate `cumulative_query_report.xlsx` from the raw query exports.
4. Run `phase_1.ipynb` to compute subject, site, country, and region metrics (`dataset_subject.xlsx`, `dataset_site.xlsx`, `dataset_country.xlsx`, `dataset_region.xlsx`).
5. Run `phase_2_3.ipynb` to add Patient Clean Status, Blocking Reason, and DQI Subject Score, and aggregate to site metrics with Site Risk Status and CRA Name (interim subject and site datasets).
6. Run `phase_4.ipynb` to derive `interim_unified_country.xlsx` and `interim_unified_region.xlsx` with geographic trends and readiness metrics.
7. Run `phase_5.ipynb` to lock down Critical Subject, Critical Site, and Analysis Readiness, generate Risk Signals and Recommended Actions, create AI summaries, and export `Site_Oversight_Final_Report.xlsx` and `Full_CRA_Site_Performance_Reports.txt`.
8. Place the exported unified files and the CRA report where `app3.py` expects them, then run `streamlit run app3.py`.

---

## 7. Version 2.0 Features (Jan 2026 Update)

The latest release evolves TrialOversightAI from a diagnostic tool into an active trial management platform with an enhanced tech stack and executive-level features.

### 1. Executive Intelligence Layer

- **Global Executive Overview:** a top-tier entry point giving a bird's-eye view of trial health across 23 studies
- **Risk Concentration Heatmap:** a relative intensity algorithm that identifies geographic hotspots in AMERICA, ASIA, and EMEA without volume bias
- **Normalized Performance Metrics:** global DQI and high-risk site percentages calculated in real time to guide resource allocation

### 2. Operational Actionability

- **Interactive Command Center:** active buttons to *Send Alerts to CRAs* and *Schedule Monitoring Visits*, moving the dashboard from passive reporting to active intervention
- **Trial Progress Timeline:** Gantt charts that visualize site-level progression from Start-Up to Close-Out
- **Empty-State Handling:** robust error-trapping and "No Data Found" alerts during complex filtering

### 3. Enhanced Quality & AI Logic

- **"90-0-80" Readiness Rule:** a stricter, multi-factor gate for Analysis Readiness requiring >90% clean patients, zero safety queries, and >80 site DQI
- **Visualized Safety-Cap:** explicit UI flagging for subjects whose DQI is capped at 60 due to safety overrides
- **Persona-Aware Narratives:** the Gemini 2.5 Flash layer better distinguishes tactical CRA needs from strategic CSM oversight requirements

### 4. Modern UI/UX Architecture

- **Streamlit Ant-Design (SAC) integration:** an icon-based navigation menu replaces the standard sidebar selectors
- **Responsive multi-tier hub:** optimized drill-down performance, from global trends to subject-level Blocking Reasons in seconds
