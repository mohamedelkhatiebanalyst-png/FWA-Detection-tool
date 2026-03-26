# Insurance FWA Detection Tool

A Streamlit web application that automatically scans health insurance claims data and flags members and providers exhibiting patterns consistent with **Fraud, Waste, or Abuse (FWA)**.

Built for claims investigators and compliance teams — no programming knowledge required to operate.

---

## Features

- **5-layer detection engine** covering over-utilization, temporal abuse, provider billing abuse, suspicious visit patterns, and claim type abuse
- **16 independent detection rules** — each contributes one point to a member's fraud score
- **Risk classification** — Low / Medium / High based on fraud score
- **Provider-level analysis** — overbilling and rejection rate flagging with member-level propagation
- **Member drill-down** — inspect all raw claims for any individual member
- **Clean Excel export** — human-readable column names, color-coded risk levels, frozen header
- **No data storage** — all processing is in-memory; nothing is saved after the browser session ends

---

## Detection Layers

| Layer | Focus | Rules |
|---|---|---|
| 1 — Overuse Detection | Per-member utilization | High visit frequency, high total claimed, high avg cost |
| 2 — Unusual Claim Timing | Time-window patterns | Repeated non-doctor claims in 7 days, same-day multi-provider, multi-city same day, high monthly volume |
| 3 — Provider Billing Abuse | Provider-level billing | Overbilling ratio > 2×, high rejection rate |
| 4 — Suspicious Visit Patterns | Provider & diagnosis diversity | Provider shopping, high doctor rotation at clinic, diagnosis shopping |
| 5 — Claim Type & Chronic | Service type patterns | Duplicate service same day, high inpatient frequency, high claim type variety, high chronic ratio |

---

## Fraud Scoring

Each triggered rule adds 1 point to a member's **Fraud Score** (max 16).

| Score | Risk Level | Suspicious |
|---|---|---|
| 0 – 1 | Low | No |
| 2 – 4 | Medium | Yes |
| 5 + | High | Yes |

All percentile-based thresholds are computed at runtime from the uploaded data — nothing is hardcoded. The Overview page shows the exact cutoff values used after every run.

---

## Required Input Columns

The uploaded CSV or Excel file must contain exactly these columns:

| Column Name | Description |
|---|---|
| `Card No` | Member insurance ID |
| `Provider Claimed Amount` | Amount requested by provider |
| `Accepted Amount` | Amount approved |
| `Provider Name` | Clinic or hospital name |
| `Provider City` | City of the provider |
| `Treatment Doctor Name` | Treating doctor |
| `Accident Date` | Date of service |
| `ICD Code` | Diagnosis code |
| `Claim Form Type` | Service type (e.g. Doctor Visit, Lab, Hospital Claim Form) |
| `Chronic` | Whether the claim is chronic (Yes / No) |
| `Age` | Member's age |
| `Rejected Amount` | Amount rejected by the insurer |

A sample file can be downloaded directly from the app's home page.

---

## Tech Stack

| Component | Library |
|---|---|
| UI | Streamlit >= 1.35.0 |
| Data processing | Pandas 2.2.3, NumPy 1.26.4 |
| Visualizations | Plotly >= 5.18.0 |
| Excel export | openpyxl >= 3.1.0 |
| Language | Python 3.11 |

---

## Installation & Running

```bash
# Clone the repository
git clone https://github.com/your-username/fwa-detection.git
cd fwa-detection

# Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # macOS / Linux

# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run app.py
```

Open your browser at `http://localhost:8501`.

---

## Project Structure

```
fwa/
├── app.py                      # Home page — upload, configure, run
├── config.py                   # Column map, validation, shared utilities
├── fraud_logic.py              # Orchestrator — calls all layers, merges results
├── requirements.txt
├── layers/
│   ├── layer1_utilization.py   # Per-member overuse rules
│   ├── layer2_temporal.py      # Time-window abuse rules
│   ├── layer3_provider.py      # Provider-level billing rules
│   ├── layer4_clinical.py      # Clinical pattern rules
│   └── layer5_claim_type.py    # Claim type & chronic abuse rules
├── pages/
│   ├── 1_Overview.py           # KPIs + suspicious members table + cutoff values
│   ├── 2_Charts.py             # EDA + suspicious member charts
│   ├── 3_Export.py             # Excel download
│   └── 4_Member_Lookup.py      # Individual member claim drill-down
└── docs/
    ├── workflow_non_technical.md
    └── workflow_technical.md
```

---

## Disclaimer

This tool identifies cases that **warrant human review** — it does not confirm fraud. All flagged members should be investigated by a qualified claims reviewer before any action is taken.
