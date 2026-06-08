# 🛒 Enterprise Retail Data Engineering & BI Pipeline

![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)
![Pandas](https://img.shields.io/badge/Pandas-2.x-150458?logo=pandas)
![Matplotlib](https://img.shields.io/badge/Matplotlib-3.x-11557c)
![Status](https://img.shields.io/badge/Status-Complete-brightgreen)
![License](https://img.shields.io/badge/License-MIT-yellow)

> A production-grade, end-to-end data engineering project simulating a real corporate retail analytics pipeline — from raw messy data generation, through enterprise-grade cleaning, to C-suite executive BI dashboards.

---

## 📌 Project Overview

This project replicates the exact data quality challenges faced by Fortune 500 retail companies every day. It covers three complete engineering stages:

| Stage | Script | What It Does |
|-------|--------|-------------|
| **1. Raw Data Simulation** | `01_generate_raw_data.py` | Samples 55,000 rows from Kaggle dataset and injects 7 real-world enterprise data quality issues |
| **2. Cleaning Pipeline** | `02_cleaning_pipeline.py` | Detects and repairs all 7 issues, adds 9 clean columns, exports audit-ready CSV |
| **3. BI Dashboard** | `03_bi_dashboard_generator.py` | Generates 9 executive-grade PNG charts for C-suite strategic reporting |

---

## 🎯 The 7 Enterprise Data Issues Simulated

| # | Issue | Rows Affected | Real-World Cause |
|---|-------|--------------|-----------------|
| 1 | **Currency Anomalies** | ~1,650 rows | ERP system exporting INR values without currency conversion |
| 2 | **Negative / Zero Quantities** | ~1,100 rows | Unhandled customer returns and system bugs |
| 3 | **String Corruptions** | ~5,500 rows | Web form URL-encoding not decoded at ingestion |
| 4 | **Double-Click Duplicates** | 250 rows | Payment gateway double-submit on slow connections |
| 5 | **Location Inconsistencies** | All UK rows | Multiple data entry standards across regional offices |
| 6 | **Future Timestamps** | 150 rows | Server clock synchronization failures |
| 7 | **CustomerID Pollutants** | ~2,750 rows | NULL handling inconsistency across legacy systems |

---

## 📊 Executive BI Dashboards Generated

| Asset | Chart Type | Business Question Answered |
|-------|-----------|--------------------------|
| `asset_01` | KPI Command Center | What is our total revenue, churn risk, and VIP status? |
| `asset_02` | RFM Scatter Plot | Which customers are about to defect? |
| `asset_03` | Horizontal Bar | Who are the top 10 VIPs we must win back immediately? |
| `asset_04` | Revenue Matrix | Where exactly are we losing money by payment method? |
| `asset_05` | Trend Line | How fast are we acquiring new customers month-on-month? |
| `asset_06` | 2×2 Quadrant | How do we segment customers for targeted campaigns? |
| `asset_07` | Stacked Bar | How is revenue shifting across customer segments? |
| `asset_08` | Dual-Axis Combo | What is the true cost of cancellations and errors? |
| `asset_09` | Donut Chart | What is our Premium vs General product revenue mix? |

---

## 🗂️ Project Structure

```
retail_project/
│
├── README.md                          # You are here
├── requirements.txt                   # Python dependencies
├── .gitignore                         # Git ignore rules
├── config.py                          # Central configuration
│
├── scripts/
│   ├── 01_generate_raw_data.py        # Stage 1 — Data simulation
│   ├── 02_cleaning_pipeline.py        # Stage 2 — Data cleaning
│   ├── 03_bi_dashboard_generator.py   # Stage 3 — BI visualization
│   └── 04_kpi_dashboard.py            # Standalone KPI PNG generator
│
├── data/
│   ├── raw/
│   │   └── enterprise_retail_raw.csv  # Dirty dataset (55,250 rows)
│   └── processed/
│       └── enterprise_retail_clean.csv # Clean dataset (17 columns)
│
└── outputs/
    ├── asset_01_executive_kpi_dashboard.png
    ├── asset_02_defection_landscape.png
    ├── asset_03_top10_churn_accounts.png
    ├── asset_04_revenue_leak_matrix.png
    ├── asset_05_cac_efficiency_trend.png
    ├── asset_06_vip_winback_matrix.png
    ├── asset_07_segment_revenue_ledger.png
    ├── asset_08_revenue_friction_dual_axis.png
    └── asset_09_premium_inventory_donut.png
```

---

## ⚙️ Tech Stack

- **Python 3.12**
- **Pandas** — data manipulation and pipeline logic
- **NumPy** — numerical operations and random data generation
- **Matplotlib** — all chart rendering and export
- **Seaborn** — supplementary styling
- **datetime** — timestamp parsing and correction

---

## 🚀 How to Run

### Prerequisites
- Python 3.10 or higher
- Download the [Online Retail Dataset from Kaggle](https://www.kaggle.com/datasets/vijayuv/onlineretail)

### Setup

```bash
# 1. Clone the repository
git clone https://github.com/YOUR_USERNAME/enterprise-retail-pipeline.git
cd enterprise-retail-pipeline

# 2. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate          # Mac / Linux
venv\Scripts\activate             # Windows

# 3. Install dependencies
pip install -r requirements.txt
```

### Run the Pipeline (in order)

```bash
# Stage 1 — Generate dirty raw dataset
python3 scripts/01_generate_raw_data.py --input "OnlineRetail.csv"

# Stage 2 — Clean the data
python3 scripts/02_cleaning_pipeline.py

# Stage 3 — Generate BI dashboards
python3 scripts/03_bi_dashboard_generator.py

# Bonus — Standalone KPI PNG
python3 scripts/04_kpi_dashboard.py
```

---

## 📈 Sample Outputs

> All 9 executive charts are saved as 300 DPI PNG files in the `/outputs` folder.
> Preview them directly on GitHub without running any code.

---

## 🧠 Key Engineering Concepts Demonstrated

- **Modular pipeline architecture** — each stage is independently runnable
- **Config-driven design** — all paths and constants centralized in `config.py`
- **Defensive data handling** — graceful fallbacks for missing columns
- **RFM Analysis** — Recency, Frequency, Monetary customer segmentation
- **Data Quality Auditing** — row-level flagging without destroying raw data
- **Publication-quality visualization** — 300 DPI, corporate design system

---

## 👤 Author

**Manish** — Aspiring Data Engineer  
📧 Connect on [LinkedIn](https://www.linkedin.com/in/manishkumar-businessanalyst)  
⭐ If this project helped you, please give it a star!

---

## 📄 License

This project is licensed under the MIT License.  
Dataset credit: [UCI Online Retail Dataset via Kaggle](https://www.kaggle.com/datasets/vijayuv/onlineretail)
