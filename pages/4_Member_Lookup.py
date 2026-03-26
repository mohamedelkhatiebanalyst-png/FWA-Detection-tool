"""
pages/4_Member_Lookup.py — Member Drill-Down
---------------------------------------------
Search for a specific member and inspect all their raw claims
alongside their fraud flags and score.
"""

import streamlit as st
import pandas as pd

from config import require_results

st.set_page_config(
    page_title="FWA Detection — Member Lookup",
    page_icon="🔎",
    layout="wide",
)

require_results(st)

df_result = st.session_state["df_result"]
df_claims = st.session_state["df_claims"]

st.title("🔎 Member Lookup")
st.caption("Search for a member to inspect their claims and fraud flags in detail.")
st.divider()

# ---------------------------------------------------------------------------
# SEARCH
# ---------------------------------------------------------------------------
all_members = sorted(df_result["member_id"].astype(str).unique())
selected = st.selectbox(
    "Select or type a Member ID",
    options=[""] + all_members,
    format_func=lambda x: "— choose a member —" if x == "" else x,
)

if not selected:
    st.info("Select a member above to view their details.")
    st.stop()

# ---------------------------------------------------------------------------
# MEMBER SUMMARY
# ---------------------------------------------------------------------------
member_result = df_result[df_result["member_id"].astype(str) == selected].iloc[0]
member_claims = df_claims[df_claims["member_id"].astype(str) == selected].copy()

risk = member_result.get("risk_level", "—")
score = int(member_result.get("fraud_score", 0))
is_susp = bool(member_result.get("is_suspicious", False))

risk_color = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}.get(risk, "⚪")
susp_label = "**Suspicious ⚠️**" if is_susp else "**Not Suspicious ✅**"

st.subheader(f"Member: {selected}")
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Fraud Score",    score)
c2.metric("Risk Level",     f"{risk_color} {risk}")
c3.metric("Status",         "Suspicious" if is_susp else "Not Suspicious")
c4.metric("Total Claimed",  f"{member_result.get('total_claimed', 0):,.2f}")
c5.metric("Total Approved", f"{member_result.get('total_accepted', 0):,.2f}")

st.divider()

# ---------------------------------------------------------------------------
# TRIGGERED FLAGS
# ---------------------------------------------------------------------------
from fraud_logic import RULE_LABELS

triggered = [label for col, label in RULE_LABELS.items() if member_result.get(col, False)]
not_triggered = [label for col, label in RULE_LABELS.items() if not member_result.get(col, False)]

col_flags, col_clear = st.columns(2)

with col_flags:
    st.markdown("**Triggered Rules**")
    if triggered:
        for label in triggered:
            st.markdown(f"🚩 {label}")
    else:
        st.success("No rules triggered.")

with col_clear:
    st.markdown("**Rules Not Triggered**")
    for label in not_triggered:
        st.markdown(f"✅ {label}")

st.divider()

# ---------------------------------------------------------------------------
# RAW CLAIMS TABLE
# ---------------------------------------------------------------------------
st.markdown(f"**All Claims for Member {selected}** ({len(member_claims):,} records)")

display_claim_cols = {
    "accident_date":    "Date",
    "provider":         "Provider",
    "provider_city":    "City",
    "treatment_doctor": "Doctor",
    "claim_form_type":  "Service Type",
    "icd_code":         "ICD Code",
    "claimed_amt":      "Claimed",
    "accepted_amt":     "Approved",
    "chronic":          "Chronic",
}
available = {k: v for k, v in display_claim_cols.items() if k in member_claims.columns}
claims_table = (
    member_claims[list(available.keys())]
    .rename(columns=available)
    .sort_values("Date")
    .reset_index(drop=True)
)
st.dataframe(claims_table, use_container_width=True, hide_index=True)
