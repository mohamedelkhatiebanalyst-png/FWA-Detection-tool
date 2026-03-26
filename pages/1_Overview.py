"""
pages/1_Overview.py — Overview
-------------------------------
KPI summary cards and detection cutoff values per layer.
"""

import streamlit as st
import pandas as pd

from config import require_results

st.set_page_config(
    page_title="FWA Detection — Overview",
    page_icon="📊",
    layout="wide",
)

require_results(st)

df_result           = st.session_state["df_result"]
computed_thresholds = st.session_state["computed_thresholds"]

# ---------------------------------------------------------------------------
# KPI CARDS
# ---------------------------------------------------------------------------
st.title("📊 Overview")
st.divider()

total_members       = len(df_result)
suspicious_count    = int(df_result["is_suspicious"].sum())
pct_suspicious      = (suspicious_count / total_members * 100) if total_members else 0
high_risk_count     = int((df_result["risk_level"] == "High").sum())
avg_fraud_score     = round(df_result["fraud_score"].mean(), 2)
overbilling_flagged = int(df_result.get("l3_provider_overbilling", pd.Series(False)).sum())

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Total Members",        f"{total_members:,}")
c2.metric("Suspicious Members",   f"{suspicious_count:,}")
c3.metric("% Suspicious",         f"{pct_suspicious:.1f}%")
c4.metric("High Risk Members",    f"{high_risk_count:,}")
c5.metric("Avg Fraud Score",      f"{avg_fraud_score}")
c6.metric("Overbilling Flagged",  f"{overbilling_flagged:,}")

st.divider()

# ---------------------------------------------------------------------------
# SUSPICIOUS MEMBERS TABLE
# ---------------------------------------------------------------------------
st.subheader("Suspicious Members")

suspicious = df_result[df_result["is_suspicious"]].copy()

if suspicious.empty:
    st.info("No suspicious members were detected in this dataset.")
else:
    display_cols = {
        "member_id":    "Member ID",
        "fraud_score":  "Fraud Score",
        "risk_level":   "Risk Level",
        "visit_count":  "Visits",
        "total_claimed":"Total Claimed",
        "total_accepted":"Total Approved",
        "reason":       "Triggered Rules",
    }
    available = {k: v for k, v in display_cols.items() if k in suspicious.columns}
    table = (
        suspicious[list(available.keys())]
        .rename(columns=available)
        .sort_values("Fraud Score", ascending=False)
        .reset_index(drop=True)
    )

    st.dataframe(table, use_container_width=True, hide_index=True)

st.divider()

# ---------------------------------------------------------------------------
# DETECTION CUTOFF VALUES
# ---------------------------------------------------------------------------
st.subheader("Detection Cutoff Values")
st.caption(
    "Cutoff values are computed from your uploaded data and adapt to your population automatically. "
    "Each rule flags members that fall above the cutoff."
)

layer_meta = {
    "utilization": "📈 Overuse Detection",
    "temporal":    "📅 Unusual Claim Timing",
    "provider":    "🏥 Provider Billing Abuse",
    "clinical":    "🔍 Suspicious Visit Patterns",
    "claim_type":  "🏷️ Claim Type & Chronic Patterns",
}
rule_display_labels = {
    "visit_count":                 "How often they visit",
    "total_claimed":               "How much they requested in total",
    "avg_claimed":                 "Typical cost per visit",
    "burst_claims":                "Repeated non-doctor claims within 7 days",
    "same_day_multi_prov":         "Same-day multi-provider (same type)",
    "multi_city_same_day":         "Multi-city visits on same day",
    "monthly_velocity":            "Claims per month volume",
    "provider_overbilling":        "Max allowed markup (requested vs approved)",
    "provider_rejection":          "Provider rejection rate",
    "distinct_providers":          "Different clinics/hospitals visited",
    "doctor_mill":                 "Clinic with unusually high doctor rotation",
    "icd_shopping":                "Same diagnosis at multiple providers",
    "duplicate_service_same_day":  "Duplicate service same day",
    "inpatient_frequency":         "Hospital admission frequency",
    "claim_type_diversity":        "Variety of claim types used",
    "chronic_high_ratio":          "Proportion of chronic claims",
}

for layer_key, layer_name in layer_meta.items():
    layer_thresh = computed_thresholds.get(layer_key, {})
    st.markdown(f"**{layer_name}**")
    if not layer_thresh:
        st.caption("No cutoffs — column not available or layer was disabled.")
        continue
    rows = []
    for rule_key, (value, pct, unit) in layer_thresh.items():
        method = f"Top {100 - pct}% flagged" if pct is not None else "Fixed threshold"
        prefix = "$" if unit == "$" else ""
        rows.append({
            "Rule":         rule_display_labels.get(rule_key, rule_key),
            "Cutoff Value": f"{prefix}{value:,.2f} {unit}".strip(),
            "How it works": method,
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
