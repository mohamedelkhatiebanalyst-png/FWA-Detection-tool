# Insurance FWA Detection Tool — Technical Workflow

## Project Structure

```
fwa/
├── app.py                        # Home page (upload, config, run)
├── config.py                     # Shared column map, validation, utilities
├── fraud_logic.py                # Orchestrator — calls all layers, merges results
├── requirements.txt
├── layers/
│   ├── __init__.py
│   ├── layer1_utilization.py     # Per-member overuse rules
│   ├── layer2_temporal.py        # Time-window abuse rules
│   ├── layer3_provider.py        # Provider-level billing rules
│   ├── layer4_clinical.py        # Clinical pattern rules
│   └── layer5_claim_type.py      # Claim type & chronic abuse rules
├── pages/
│   ├── 1_Overview.py             # KPIs + suspicious members table + cutoff values
│   ├── 2_Charts.py               # EDA tab + suspicious members tab
│   ├── 3_Export.py               # Excel download
│   └── 4_Member_Lookup.py        # Individual member claim drill-down
└── docs/
    ├── workflow_non_technical.md
    └── workflow_technical.md
```

---

## Technology Stack

| Component | Library / Version |
|---|---|
| UI framework | Streamlit >= 1.35.0 |
| Data processing | Pandas 2.2.3, NumPy 1.26.4 |
| Visualizations | Plotly >= 5.18.0 |
| Excel support | openpyxl >= 3.1.0 |
| Language | Python 3.11 |

---

## Data Flow

```
User uploads CSV / XLSX
        │
        ▼
config.normalize_columns()       ← strip + rename via COLUMN_MAP dict
        │
        ▼
config.validate()                ← enforce all 12 required columns + numeric types
        │
        ▼
detect_fraud(df, **sidebar_params)   ← fraud_logic.py orchestrator
        │
        ├── layer1_utilization.run()
        ├── layer2_temporal.run()
        ├── layer3_provider.run()
        ├── layer4_clinical.run()
        └── layer5_claim_type.run()
                │
                ▼ each returns (DataFrame, thresholds_dict)
                │
        merge all on member_id
                │
                ▼
        compute fraud_score (sum of all bool rule cols)
        assign risk_level, is_suspicious, reason string
                │
                ▼
        st.session_state["df_result"]           ← one row per member
        st.session_state["computed_thresholds"] ← nested dict for UI
        st.session_state["df_claims"]           ← raw normalized claims
```

---

## Column Mapping (`config.py`)

All 12 columns are **required**. The file is rejected at validation if any are missing.

Raw column names are normalized on upload via a case-sensitive dict lookup:

```python
COLUMN_MAP = {
    "Card No"                 → "member_id"
    "Provider Claimed Amount" → "claimed_amt"
    "Accepted Amount"         → "accepted_amt"
    "Rejected Amount"         → "rejected_amt"
    "Provider Name"           → "provider"
    "Provider City"           → "provider_city"
    "Treatment Doctor Name"   → "treatment_doctor"
    "Accident Date"           → "accident_date"
    "ICD Code"                → "icd_code"
    "Claim Form Type"         → "claim_form_type"
    "Chronic"                 → "chronic"
    "Age"                     → "age"
}
```

`REQUIRED_COLUMNS` contains all 12 entries. `REQUIRED_INTERNAL` is the set of internal names derived from it. `validate()` diffs `REQUIRED_INTERNAL` against `df.columns` and returns a descriptive error for any missing column.

All downstream processing uses internal names exclusively.

---

## Layer Architecture

Each layer follows the same contract:

```python
def run(df: pd.DataFrame, enable: bool, **params) -> tuple[pd.DataFrame, dict]:
    # Returns:
    #   result     : one row per member_id, flag columns prefixed l{N}_*
    #   thresholds : {rule_key: (cutoff_value, pct_or_None, unit_string)}
```

Thresholds are computed at runtime from the uploaded data using `pandas.Series.quantile(pct/100)`. Nothing is hardcoded — the system adapts to any population.

---

## Layer 1 — Over-Utilization (`layer1_utilization.py`)

**Aggregation:** per `member_id`

**Output metrics:** `total_claimed`, `total_accepted`, `avg_claimed` (median), `visit_count`, `overbilling_ratio`

| Rule Column | Logic |
|---|---|
| `l1_high_freq` | `visit_count > quantile(visit_freq_pct/100)` |
| `l1_high_cost` | `total_claimed > quantile(total_claimed_pct/100)` |
| `l1_high_avg_cost` | `avg_claimed > quantile(avg_claimed_pct/100)` |

Note: `avg_claimed` uses **median** per member (not mean) to reduce distortion from outlier claims.

---

## Layer 2 — Temporal Abuse (`layer2_temporal.py`)

**Requires:** `accident_date`, `claim_form_type`

The same-day multi-provider rule is type-aware: it groups by `member_id + date + claim_form_type` and counts distinct providers per type. Visiting a doctor and a lab on the same day is normal; visiting two different labs on the same day is flagged.

| Rule Column | Logic |
|---|---|
| `l2_burst_claims` | Rolling window scan on non-doctor-visit claims only: for each member, find max claims in any `burst_window_days`-day window. Flag if `>= burst_min_claims`. O(n²) per member. |
| `l2_same_day_multi_prov` | `max(distinct providers per claim_form_type per day) >= 2` |
| `l2_multi_city_same_day` | `max(distinct provider_city per day) >= 2` — physically implausible same-day travel |
| `l2_high_monthly_velocity` | `max_monthly_claims > quantile(monthly_vel_pct/100)` across all members' busiest months. |

---

## Layer 3 — Provider Billing Abuse (`layer3_provider.py`)

**Aggregation:** per `provider`, then joined back to member level. A member is flagged if **any** provider they visited was flagged.

| Rule Column | Logic |
|---|---|
| `l3_provider_overbilling` | `(sum_claimed / sum_accepted) > overbilling_ratio_threshold` — fixed threshold, not percentile-based. |
| `l3_provider_high_rejection` | `rejection_rate = (claimed - accepted) / claimed` per provider; flag if `> quantile(rejection_rate_pct/100)`. |

**Extra output:** `max_provider_overbilling_ratio` — the worst provider ratio seen by that member (used in charts).

---

## Layer 4 — Clinical Patterns (`layer4_clinical.py`)

**Requires:** `treatment_doctor` (doctor mill rule), `icd_code` (ICD shopping rule)

| Rule Column | Logic |
|---|---|
| `l4_provider_shopping` | `distinct_providers_per_member > quantile(distinct_providers_pct/100)` |
| `l4_doctor_mill` | `max(distinct doctors at same provider) > quantile(doctor_mill_pct/100)` — flags clinics with unusually high doctor rotation |
| `l4_icd_shopping` | `max(distinct providers per ICD code) > quantile(icd_shopping_pct/100)` |

---

## Layer 5 — Claim Type & Chronic Abuse (`layer5_claim_type.py`)

**Requires:** `claim_form_type`, `chronic`, `accident_date`

| Rule Column | Logic |
|---|---|
| `l5_duplicate_service_same_day` | `max(claims per member per claim_form_type per day) >= 2` |
| `l5_inpatient_frequency` | Count rows where `claim_form_type.lower() == "hospital claim form"` per member; flag if `> quantile(inpatient_freq_pct/100)` |
| `l5_claim_type_diversity` | `distinct claim_form_type values per member > quantile(claim_type_diversity_pct/100)` |
| `l5_chronic_high_ratio` | `mean(chronic_bool) per member > quantile(chronic_ratio_pct/100)`. Chronic column is normalized: accepts `True/False`, `1/0`, `"yes"/"no"`, `"y"/"n"` |

---

## Fraud Score Computation (`fraud_logic.py`)

```python
ALL_RULE_COLS = [
    "l1_high_freq", "l1_high_cost", "l1_high_avg_cost",
    "l2_burst_claims", "l2_same_day_multi_prov", "l2_high_monthly_velocity",
    "l3_provider_overbilling", "l3_provider_high_rejection",
    "l4_provider_shopping", "l4_doctor_mill", "l4_icd_shopping",
    "l5_duplicate_service_same_day", "l5_inpatient_frequency",
    "l5_claim_type_diversity", "l5_chronic_high_ratio",
]

fraud_score   = sum(result[col].astype(int) for col in ALL_RULE_COLS)  # max = 16
is_suspicious = fraud_score >= 2

risk_level:
    score 0–1  → "Low"
    score 2–4  → "Medium"
    score 5+   → "High"
```

A plain-text `reason` column is also generated by joining the `RULE_LABELS` values for every triggered rule, separated by ` | `.

---

## Session State Management (`app.py`)

Results are stored in `st.session_state` after the run button is clicked, making them available across all pages without re-running the analysis.

| Key | Type | Content |
|---|---|---|
| `df_result` | DataFrame | One row per member — all metrics, rule flags, score, risk level |
| `computed_thresholds` | dict | Nested `{layer: {rule: (value, pct, unit)}}` — used by Overview page |
| `df_claims` | DataFrame | Normalized raw claims — used by Charts page for dataset-level metrics |
| `_processed_file` | str | Filename of the last processed upload — used to detect new uploads and clear stale results |

---

## Multipage Architecture (Streamlit)

The app uses Streamlit's native multipage structure. Each `pages/N_Name.py` file is auto-discovered and shown in the sidebar navigation.

All results pages call `config.require_results(st)` at the top:

```python
def require_results(st_module) -> bool:
    if "df_result" not in st_module.session_state:
        st_module.warning("No analysis results found...")
        st_module.stop()
        return False
    return True
```

This prevents errors if a user navigates to a results page before running the analysis.

---

## Threshold Display (Overview Page)

The `computed_thresholds` dict follows this structure:

```python
{
    "utilization": {
        "visit_count":   (12.0, 90, "visits"),   # (value, pct, unit)
        "total_claimed": (5400.0, 90, "$"),
        "avg_claimed":   (320.0, 90, "$"),
    },
    "temporal": { ... },
    "provider": { ... },
    "clinical": { ... },
    "claim_type": { ... },
}
```

Rules with `pct=None` used a fixed threshold (e.g., overbilling ratio, burst min claims). The Overview page renders these as `"Fixed threshold"` vs `"Top X% flagged"`.

---

## Charts Page — Key Data Sources

**Tab 1 — Dataset EDA**

| Chart | Source DataFrame | Key Columns |
|---|---|---|
| Data distribution histogram | `df_claims` / `df_result` | selectable metric |
| Correlation matrix heatmap | `df_result` | numeric member metrics |
| Rule co-occurrence heatmap | `df_result` | all `l{N}_*` bool columns |
| Monthly time series | `df_claims` | `accident_date`, `claimed_amt`, `accepted_amt` |
| Claim type grouped bar + box plot | `df_claims` | `claim_form_type`, `claimed_amt`, `accepted_amt` |
| Scatter plots | `df_result` + derived | selectable axis pairs including `age`, `rejected_amt` |

**Tab 2 — Suspicious Members**

| Chart | Source DataFrame | Key Columns |
|---|---|---|
| Risk level donut pie | `df_result` | `risk_level` |
| Top 10 by fraud score | `df_result` (suspicious only) | `member_id`, `fraud_score` |
| Rules fired bar | `df_result` | all `l{N}_*` bool columns |
| Top 10 providers by overbilling | `df_claims` | `provider`, `claimed_amt`, `accepted_amt` |

---

## Export Page

Two `st.download_button` widgets generate Excel files in-memory using `openpyxl` via `pd.ExcelWriter`. Before export, all internal column names are renamed to human-readable labels via `EXPORT_COLUMNS` dict in `3_Export.py`. The workbook includes a frozen header row, bold grey header styling, auto-fitted column widths, and color-coded Risk Level cells (red / yellow / green).

No files are written to disk.

---

## Running the App

```bash
cd fwa
.venv\Scripts\activate       # Windows
streamlit run app.py
```

Default port: `http://localhost:8501`

---

## Sidebar Design

The sidebar contains no adjustable sliders. Each layer has a single enable/disable checkbox and a guide table explaining every rule it contains. This is intentional:

- End users are claims investigators, not data scientists — threshold numbers have no meaning to them without knowing the underlying distribution
- The 90th percentile default is a sound actuarial starting point for all percentile-based rules
- Misconfiguration risk (e.g., dragging all thresholds to 50%) is eliminated
- The Overview page already provides full transparency by showing the exact computed cutoffs after analysis

If sensitivity adjustment is ever needed for a specific deployment, it is a configuration change inside the relevant layer file's `DEFAULT_*` constants — a one-line change per rule, traceable in version control.

---

## Adding a New Detection Rule — Checklist

1. **Add rule logic** in the appropriate layer file. Return a bool column prefixed `l{N}_`.
2. **Add the rule to `RULE_LABELS`** in `fraud_logic.py` — this registers it in the scoring system.
3. **Add threshold to the layer's `thresholds` dict** in the format `(value, pct_or_None, unit)`.
4. **Add display label** to `rule_display_labels` in `pages/1_Overview.py`.
5. **Add the rule description** to its layer's guide table in the sidebar section of `app.py`.
6. **Update the active rule count** for that layer in the `active_rules` expression in `app.py`.
