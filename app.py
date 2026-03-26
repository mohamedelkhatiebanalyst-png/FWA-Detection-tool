"""
app.py — Home (Upload & Run)
----------------------------
Step 1 : Upload claims file
Step 2 : Column detection
Step 3 : Data preview
Step 4 : Enable/disable detection layers (sidebar)
Step 5 : Run analysis → results stored in session_state for all pages
"""

import io

import streamlit as st
import pandas as pd

from config import normalize_columns, validate, REQUIRED_COLUMNS
from fraud_logic import detect_fraud


def _build_sample_excel() -> bytes:
    sample = pd.DataFrame([
        {
            "Card No": "MEM-001",
            "Provider Claimed Amount": 1200.00,
            "Accepted Amount": 1000.00,
            "Provider Name": "City Medical Center",
            "Provider City": "Riyadh",
            "Treatment Doctor Name": "Dr. Ahmed Ali",
            "Accident Date": "2024-01-15",
            "ICD Code": "J06.9",
            "Claim Form Type": "Doctor Visit",
            "Chronic": "No",
            "Age": 34,
            "Rejected Amount": 200.00,
        },
        {
            "Card No": "MEM-002",
            "Provider Claimed Amount": 3500.00,
            "Accepted Amount": 1200.00,
            "Provider Name": "Al Noor Clinic",
            "Provider City": "Jeddah",
            "Treatment Doctor Name": "Dr. Sara Hassan",
            "Accident Date": "2024-01-16",
            "ICD Code": "E11.9",
            "Claim Form Type": "Hospital Claim Form",
            "Chronic": "Yes",
            "Age": 58,
            "Rejected Amount": 2300.00,
        },
        {
            "Card No": "MEM-003",
            "Provider Claimed Amount": 450.00,
            "Accepted Amount": 450.00,
            "Provider Name": "LabTech Diagnostics",
            "Provider City": "Riyadh",
            "Treatment Doctor Name": "Dr. Khalid Omar",
            "Accident Date": "2024-01-16",
            "ICD Code": "Z00.0",
            "Claim Form Type": "Lab",
            "Chronic": "No",
            "Age": 27,
            "Rejected Amount": 0.00,
        },
    ])
    buf = io.BytesIO()
    sample.to_excel(buf, index=False, engine="openpyxl")
    return buf.getvalue()

st.set_page_config(
    page_title="FWA Detection — Home",
    page_icon="🚨",
    layout="wide",
)

# ---------------------------------------------------------------------------
# SIDEBAR — Detection Layer Guide
# ---------------------------------------------------------------------------
st.sidebar.header("⚙️ Detection Layers")
st.sidebar.caption(
    "Enable or disable layers below. "
    "All thresholds are computed automatically from your uploaded data."
)

# ── Layer 1 — Overuse Detection ──────────────────────────────────────────
with st.sidebar.expander("📈 Overuse Detection", expanded=False):
    enable_utilization = st.checkbox("Enable", value=True, key="en_l1")
    st.markdown(
        "Flags members who use their insurance far more than typical.\n\n"
        "| Rule | Detects |\n"
        "|---|---|\n"
        "| High visit frequency | Visit count in the top 10% of all members |\n"
        "| High total requested | Total claimed amount in the top 10% |\n"
        "| High cost per visit | Average cost per visit in the top 10% |"
    )

# ── Layer 2 — Unusual Claim Timing ───────────────────────────────────────
with st.sidebar.expander("📅 Unusual Claim Timing", expanded=False):
    enable_temporal = st.checkbox("Enable", value=True, key="en_l2")
    st.markdown(
        "Flags suspicious patterns in *when* and *where* claims are submitted.\n\n"
        "| Rule | Detects |\n"
        "|---|---|\n"
        "| Repeated non-doctor claims within 7 days | 3+ non-doctor-visit claims within any 7-day window |\n"
        "| Same-day multi-provider | Same service type at 2+ different providers on the same day |\n"
        "| Multi-city same day | Claims in 2+ different cities on the same day |\n"
        "| High monthly volume | Busiest month is in the top 10% across all members |"
    )

# ── Layer 3 — Provider Billing Abuse ─────────────────────────────────────
with st.sidebar.expander("🏥 Provider Billing Abuse", expanded=False):
    enable_provider = st.checkbox("Enable", value=True, key="en_l3")
    st.markdown(
        "Flags providers who bill in suspicious ways. "
        "A member is flagged if **any** provider they visited triggered a rule.\n\n"
        "| Rule | Detects |\n"
        "|---|---|\n"
        "| Provider overbilling | Provider requested more than 2× what was approved |\n"
        "| High rejection rate | Provider's rejection rate is in the top 10% |"
    )

# ── Layer 4 — Suspicious Visit Patterns ──────────────────────────────────
with st.sidebar.expander("🔍 Suspicious Visit Patterns", expanded=False):
    enable_clinical = st.checkbox("Enable", value=True, key="en_l4")
    st.markdown(
        "Flags suspicious patterns in *where* and *who* a member visits.\n\n"
        "| Rule | Detects |\n"
        "|---|---|\n"
        "| Provider shopping | Distinct providers visited in the top 10% |\n"
        "| Clinic with high doctor rotation | Many different doctors seen at the same clinic (top 10%) |\n"
        "| ICD shopping | Same diagnosis claimed at many different providers (top 10%) |"
    )

# ── Layer 5 — Claim Type & Chronic Patterns ──────────────────────────────
with st.sidebar.expander("🏷️ Claim Type & Chronic Patterns", expanded=False):
    enable_claim_type = st.checkbox("Enable", value=True, key="en_l5")
    st.markdown(
        "Flags abuse patterns based on service types and chronic benefit usage.\n\n"
        "| Rule | Detects |\n"
        "|---|---|\n"
        "| Duplicate service same day | Same service type submitted 2+ times on the same day |\n"
        "| High inpatient frequency | Hospital admissions count in the top 10% |\n"
        "| High claim type diversity | Number of different service types used in the top 10% |\n"
        "| High chronic ratio | Proportion of chronic-flagged claims in the top 10% |"
    )

# ── Scoring & Threshold Guide ────────────────────────────────────────────
st.sidebar.divider()
with st.sidebar.expander("📊 How Scoring Works", expanded=False):
    st.markdown(
        "Each triggered rule adds **1 point** to a member's Fraud Score.\n\n"
        "| Score | Risk Level |\n"
        "|---|---|\n"
        "| 0 – 1 | 🟢 Low |\n"
        "| 2 – 4 | 🟡 Medium |\n"
        "| 5 + | 🔴 High |\n\n"
        "Members with score **≥ 2** are marked **Suspicious**."
    )

with st.sidebar.expander("📐 How Thresholds Work", expanded=False):
    st.markdown(
        "**Percentile rules** (marked *top 10%*) fire for members above the "
        "90th percentile of that metric — computed from your uploaded data at runtime. "
        "The cutoffs adapt automatically to your population.\n\n"
        "**Fixed rules** (burst window, overbilling ratio, same-day counts) use "
        "hard limits grounded in clinical and actuarial standards.\n\n"
        "See the **📊 Overview** page after running for the exact cutoff values "
        "computed from your file."
    )

# Active rules summary
st.sidebar.divider()
active_rules = (
    (3 if enable_utilization else 0)
    + (4 if enable_temporal   else 0)
    + (2 if enable_provider   else 0)
    + (3 if enable_clinical   else 0)
    + (4 if enable_claim_type else 0)
)
st.sidebar.caption(
    f"**{active_rules} / 16 rules active.** "
    "A member is flagged **suspicious** when score ≥ 2."
)

st.sidebar.divider()
st.sidebar.subheader("📋 Required Columns")
st.sidebar.markdown(
    """
    | CSV Column | Used As |
    |---|---|
    | `Card No` | Member ID |
    | `Provider Claimed Amount` | Requested cost |
    | `Accepted Amount` | Approved cost |
    | `Provider Name` | Provider |
    | `Provider City` | Multi-city same-day detection |
    | `Treatment Doctor Name` | Doctor mill detection |
    | `Accident Date` | Timing abuse detection |
    | `ICD Code` | Diagnosis shopping detection |
    | `Claim Form Type` | Service type abuse detection |
    | `Chronic` | Chronic benefit abuse detection |
    | `Age` | Age-based scatter plot analysis |
    | `Rejected Amount` | Requested vs rejected scatter analysis |
    """
)

# ---------------------------------------------------------------------------
# MAIN PAGE
# ---------------------------------------------------------------------------
st.title("🚨 Insurance FWA Detection Tool")
st.markdown(
    "Upload your claims file, enable or disable detection layers in the sidebar, "
    "then run the analysis. Results are available across all pages."
)

# ---------------------------------------------------------------------------
# TOOL DESCRIPTION
# ---------------------------------------------------------------------------
with st.expander("ℹ️ About This Tool", expanded=False):
    st.markdown(
        """
        ### What Is This Tool?
        This tool automatically scans health insurance claims data and surfaces members and providers
        whose behaviour is statistically consistent with **Fraud, Waste, or Abuse (FWA)**.
        It is designed for claims investigators and compliance teams — no programming knowledge required.

        ---

        ### How It Works
        Every uploaded claim is passed through **5 independent detection layers**.
        Each layer applies a set of rules; every rule that fires adds **1 point** to the member's
        **Fraud Score** (maximum 16). Members who accumulate 2 or more points are flagged as suspicious.

        | Score | Risk Level | Action |
        |---|---|---|
        | 0 – 1 | 🟢 Low | No action needed |
        | 2 – 4 | 🟡 Medium | Queue for routine review |
        | 5 + | 🔴 High | Escalate for immediate investigation |

        ---

        ### Detection Layers & Flags

        | Layer | Focus | Rules Included |
        |---|---|---|
        | 📈 **Overuse Detection** | Per-member utilisation | High visit frequency · High total requested amount · High average cost per visit |
        | 📅 **Unusual Claim Timing** | When & where claims are filed | Repeated non-doctor claims within 7 days · Same service type at 2+ providers same day · Claims in 2+ cities same day · Abnormally high monthly volume |
        | 🏥 **Provider Billing Abuse** | How providers bill | Provider requested >2× what was approved · Provider rejection rate in top 10% |
        | 🔍 **Suspicious Visit Patterns** | Who & where a member goes | Visiting too many different providers · Clinic with high doctor rotation · Same diagnosis at many different providers |
        | 🏷️ **Claim Type & Chronic Patterns** | Service type behaviour | Duplicate service same day · High inpatient admission frequency · Wide variety of service types · Abnormally high chronic claim proportion |

        ---

        ### What This Tool Does NOT Do
        - It does **not** confirm fraud — it identifies cases that warrant human review.
        - It does **not** connect to any external system — all processing happens locally with your uploaded file.
        - It does **not** store your data — nothing is saved after the browser session ends.
        """
    )

st.divider()

# ---------------------------------------------------------------------------
# SECTION 1 — FILE UPLOAD
# ---------------------------------------------------------------------------
st.subheader("1. Upload Claims Data")
st.download_button(
    label="📥 Download Sample File",
    data=_build_sample_excel(),
    file_name="sample_claims.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)
uploaded_file = st.file_uploader("Choose a CSV or Excel file", type=["csv", "xlsx"])

if uploaded_file is not None:

    try:
        df_raw = (
            pd.read_excel(uploaded_file)
            if uploaded_file.name.endswith(".xlsx")
            else pd.read_csv(uploaded_file)
        )
    except Exception as e:
        st.error(f"Failed to read file: {e}")
        st.stop()

    df = normalize_columns(df_raw)

    # -----------------------------------------------------------------------
    # SECTION 2 — COLUMN DETECTION
    # -----------------------------------------------------------------------
    st.subheader("2. Column Detection")
    mapped_cols  = set(df.columns)
    raw_col_list = list(df_raw.columns.str.strip())

    all_required_present = True
    col_a, col_b = st.columns(2)
    items = list(REQUIRED_COLUMNS.items())
    mid   = (len(items) + 1) // 2
    for container, chunk in [(col_a, items[:mid]), (col_b, items[mid:])]:
        with container:
            for display_name, internal in chunk:
                found = internal in mapped_cols
                if not found:
                    all_required_present = False
                st.markdown(f"{'✅' if found else '❌'} &nbsp; `{display_name}`")

    with st.expander(f"All columns in your file ({len(raw_col_list)} total)"):
        st.write(raw_col_list)

    if not all_required_present:
        st.error("Some required columns are missing. Please fix your file before continuing.")
        st.stop()

    st.divider()

    errors = validate(df)
    if errors:
        for err in errors:
            st.error(err)
        st.stop()

    df["claimed_amt"]  = pd.to_numeric(df["claimed_amt"],  errors="coerce").fillna(0)
    df["accepted_amt"] = pd.to_numeric(df["accepted_amt"], errors="coerce").fillna(0)

    # -----------------------------------------------------------------------
    # SECTION 3 — DATA PREVIEW
    # -----------------------------------------------------------------------
    st.subheader("3. Data Preview")
    st.dataframe(df_raw.head(10), use_container_width=True)
    p1, p2, p3 = st.columns(3)
    p1.caption(f"Total claims: **{len(df):,}**")
    p2.caption(f"Unique members: **{df['member_id'].nunique():,}**")
    p3.caption(f"Unique providers: **{df['provider'].nunique():,}**")
    st.divider()

    # -----------------------------------------------------------------------
    # SECTION 4 — RUN ANALYSIS
    # -----------------------------------------------------------------------
    st.subheader("4. Run Analysis")

    # Clear stale results when a new file is uploaded
    if st.session_state.get("_processed_file") != uploaded_file.name:
        for k in ["df_result", "computed_thresholds", "df_claims"]:
            st.session_state.pop(k, None)

    if st.button("🔍 Run FWA Analysis", type="primary", use_container_width=True):
        with st.spinner("Running 5-layer FWA analysis..."):
            _result, _thresholds = detect_fraud(
                df,
                enable_utilization=enable_utilization,
                enable_temporal=enable_temporal,
                enable_provider=enable_provider,
                enable_clinical=enable_clinical,
                enable_claim_type=enable_claim_type,
            )
        st.session_state["df_result"]           = _result
        st.session_state["computed_thresholds"] = _thresholds
        st.session_state["df_claims"]           = df.copy()
        st.session_state["_processed_file"]     = uploaded_file.name
        st.success("✅ Analysis complete!")
        nav1, nav2, nav3 = st.columns(3)
        nav1.page_link("pages/1_Overview.py", label="📊 Go to Overview",     icon="📊")
        nav2.page_link("pages/2_Charts.py",   label="📈 Go to Charts & EDA", icon="📈")
        nav3.page_link("pages/3_Export.py",   label="📥 Go to Export",       icon="📥")

    elif "df_result" in st.session_state and st.session_state.get("_processed_file") == uploaded_file.name:
        n_suspicious = int(st.session_state["df_result"]["is_suspicious"].sum())
        st.info(f"Analysis already run — **{n_suspicious} suspicious members** found. Re-run or navigate using the buttons.")
        nav1, nav2, nav3 = st.columns(3)
        nav1.page_link("pages/1_Overview.py", label="📊 Overview",     icon="📊")
        nav2.page_link("pages/2_Charts.py",   label="📈 Charts & EDA", icon="📈")
        nav3.page_link("pages/3_Export.py",   label="📥 Export",       icon="📥")

else:
    st.info(
        "Upload a CSV or Excel file to get started. "
        "See the **📋 Required Columns** section in the sidebar for expected column names."
    )
