"""
pages/2_Charts.py — Charts & EDA
----------------------------------
Tab 1 — Dataset EDA        : distribution, correlation, co-occurrence heatmap,
                              time series, claim type analysis
Tab 2 — Suspicious Members : risk level, top fraud scores, rules fired, overbilling
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

from config import require_results
from fraud_logic import RULE_LABELS

st.set_page_config(
    page_title="FWA Detection — Charts & EDA",
    page_icon="📈",
    layout="wide",
)

require_results(st)

df_result = st.session_state["df_result"]
df_claims = st.session_state["df_claims"]

PALETTE = {
    "red":    "#e05c5c",
    "blue":   "#5c8ae0",
    "orange": "#e0a85c",
    "green":  "#7dc87d",
    "purple": "#9b72cf",
}

# ---------------------------------------------------------------------------
# DATASET OVERVIEW — metrics always visible above tabs
# ---------------------------------------------------------------------------
st.title("📈 Charts & EDA")
st.subheader("Dataset Overview")

m1, m2, m3, m4 = st.columns(4)
m1.metric("Median Requested / Member", f"{df_result['total_claimed'].median():,.2f}")
m2.metric("Median Approved / Member",  f"{df_result['total_accepted'].median():,.2f}")
m3.metric("Total Requested",           f"{df_claims['claimed_amt'].sum():,.0f}")
m4.metric("Total Approved",            f"{df_claims['accepted_amt'].sum():,.0f}")

st.divider()

# Pre-compute dated claims used by both tabs
df_dated = df_claims.copy()
df_dated["accident_date"] = pd.to_datetime(df_dated["accident_date"], errors="coerce")
df_dated = df_dated.dropna(subset=["accident_date"])

# ---------------------------------------------------------------------------
# TABS
# ---------------------------------------------------------------------------
tab_eda, tab_suspicious = st.tabs(["📊 Dataset EDA", "🚨 Suspicious Members"])

# ===========================================================================
# TAB 1 — DATASET EDA
# ===========================================================================
with tab_eda:

    # ── 1. Data Distribution ─────────────────────────────────────────────
    st.markdown("**1. Data Distribution**")
    dist_options = {
        "Claimed Amount per Claim":  ("df_claims", "claimed_amt"),
        "Approved Amount per Claim": ("df_claims", "accepted_amt"),
        "Total Claimed per Member":  ("df_result", "total_claimed"),
        "Total Approved per Member": ("df_result", "total_accepted"),
        "Visit Count per Member":    ("df_result", "visit_count"),
        "Fraud Score":               ("df_result", "fraud_score"),
    }
    selected_dist = st.selectbox("Select metric", list(dist_options.keys()), key="dist_select")
    src_name, dist_col = dist_options[selected_dist]
    dist_df = df_claims if src_name == "df_claims" else df_result
    fig_dist = px.histogram(
        dist_df, x=dist_col, nbins=40,
        color_discrete_sequence=[PALETTE["blue"]],
        labels={dist_col: selected_dist},
    )
    fig_dist.update_layout(
        xaxis_title=selected_dist, yaxis_title="Count",
        bargap=0.05, margin=dict(t=20),
    )
    st.plotly_chart(fig_dist, use_container_width=True)

    st.divider()

    # ── 2. Correlation Matrix ─────────────────────────────────────────────
    st.markdown("**2. Correlation Matrix — Member Metrics**")
    corr_cols = [c for c in [
        "total_claimed", "total_accepted", "visit_count", "distinct_providers",
        "avg_claimed", "overbilling_ratio", "fraud_score",
    ] if c in df_result.columns]
    corr_labels = {
        "total_claimed":      "Total Claimed",
        "total_accepted":     "Total Approved",
        "visit_count":        "Visit Count",
        "distinct_providers": "Providers Visited",
        "avg_claimed":        "Avg Cost/Visit",
        "overbilling_ratio":  "Claim/Approval Ratio",
        "fraud_score":        "Fraud Score",
    }
    corr_matrix = df_result[corr_cols].corr()
    corr_matrix.index   = [corr_labels.get(c, c) for c in corr_matrix.index]
    corr_matrix.columns = [corr_labels.get(c, c) for c in corr_matrix.columns]
    fig_corr = go.Figure(go.Heatmap(
        z=corr_matrix.values,
        x=list(corr_matrix.columns),
        y=list(corr_matrix.index),
        colorscale="RdBu",
        zmid=0,
        text=np.round(corr_matrix.values, 2),
        texttemplate="%{text}",
        hovertemplate="%{y} × %{x}: %{z:.2f}<extra></extra>",
    ))
    fig_corr.update_layout(
        margin=dict(t=20, l=160, b=120),
        height=450,
        xaxis_tickangle=-35,
    )
    st.plotly_chart(fig_corr, use_container_width=True)

    st.divider()

    # ── 3. Rule Co-occurrence Heatmap ─────────────────────────────────────
    st.markdown("**3. Rule Co-occurrence Heatmap**")
    st.caption("How often pairs of rules fire together on the same member. Darker = more co-occurrence.")
    rule_cols = [c for c in RULE_LABELS if c in df_result.columns]
    rule_flags = df_result[rule_cols].astype(int)
    cooc = rule_flags.T.dot(rule_flags)
    short_labels = [RULE_LABELS[c] for c in rule_cols]
    fig_cooc = go.Figure(go.Heatmap(
        z=cooc.values,
        x=short_labels,
        y=short_labels,
        colorscale="YlOrRd",
        hovertemplate="%{y} + %{x}: %{z} members<extra></extra>",
    ))
    fig_cooc.update_layout(
        margin=dict(t=20, l=260, b=200),
        height=550,
        xaxis_tickangle=-45,
    )
    st.plotly_chart(fig_cooc, use_container_width=True)

    st.divider()

    # ── 4. Time Series — Monthly Requested vs Approved ───────────────────
    st.markdown("**4. Requested vs Approved Amount Over Time**")

    df_dated["year_month"] = df_dated["accident_date"].dt.to_period("M")
    monthly_ts = (
        df_dated.groupby("year_month")
        .agg(Requested=("claimed_amt", "sum"), Approved=("accepted_amt", "sum"))
        .reset_index()
    )
    # Convert period to timestamp for proper datetime x-axis (always starts at the 1st of the month)
    monthly_ts["date"] = monthly_ts["year_month"].dt.to_timestamp()
    monthly_ts = monthly_ts.sort_values("date")

    fig_ts = go.Figure()
    fig_ts.add_trace(go.Scatter(
        x=monthly_ts["date"], y=monthly_ts["Requested"],
        mode="lines+markers", name="Requested",
        line=dict(color=PALETTE["orange"], width=2),
        marker=dict(size=5),
    ))
    fig_ts.add_trace(go.Scatter(
        x=monthly_ts["date"], y=monthly_ts["Approved"],
        mode="lines+markers", name="Approved",
        line=dict(color=PALETTE["blue"], width=2),
        marker=dict(size=5),
    ))
    fig_ts.update_layout(
        xaxis=dict(
            title="Month",
            tickformat="%b %Y",
            dtick="M1",
            tickangle=-35,
        ),
        yaxis_title="Amount",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(t=40, b=60),
        hovermode="x unified",
    )
    st.plotly_chart(fig_ts, use_container_width=True)

    st.divider()

    # ── 5. Claim Type vs Requested Amount ────────────────────────────────
    st.markdown("**5. Claim Type vs Requested Amount**")
    ct_agg = (
        df_claims.groupby("claim_form_type")
        .agg(
            Total_Requested=("claimed_amt", "sum"),
            Total_Approved=("accepted_amt", "sum"),
        )
        .reset_index()
        .sort_values("Total_Requested", ascending=False)
    )
    ct_left, ct_right = st.columns(2)

    with ct_left:
        fig_ct_bar = go.Figure()
        fig_ct_bar.add_trace(go.Bar(
            name="Requested", x=ct_agg["claim_form_type"], y=ct_agg["Total_Requested"],
            marker_color=PALETTE["orange"],
        ))
        fig_ct_bar.add_trace(go.Bar(
            name="Approved", x=ct_agg["claim_form_type"], y=ct_agg["Total_Approved"],
            marker_color=PALETTE["blue"],
        ))
        fig_ct_bar.update_layout(
            barmode="group",
            xaxis_title="Claim Type",
            yaxis_title="Total Amount",
            xaxis_tickangle=-30,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(t=40, b=80),
        )
        st.plotly_chart(fig_ct_bar, use_container_width=True)

    with ct_right:
        fig_ct_box = px.box(
            df_claims,
            x="claim_form_type",
            y="claimed_amt",
            color_discrete_sequence=[PALETTE["purple"]],
            labels={"claim_form_type": "Claim Type", "claimed_amt": "Claimed Amount"},
        )
        fig_ct_box.update_layout(
            xaxis_tickangle=-30,
            margin=dict(t=20, b=80),
        )
        st.plotly_chart(fig_ct_box, use_container_width=True)

    st.divider()

    # ── 6. Scatter Plots ──────────────────────────────────────────────────
    st.markdown("**6. Scatter Plots**")

    # Build scatter base — start from df_result then merge in derived columns
    scatter_base = df_result.copy()

    if "rejected_amt" in df_claims.columns:
        member_rejected = (
            df_claims.groupby("member_id")["rejected_amt"]
            .sum()
            .reset_index(name="total_rejected")
        )
        scatter_base = scatter_base.merge(member_rejected, on="member_id", how="left")

    has_age = "age" in df_claims.columns
    if has_age:
        member_age = (
            df_claims.groupby("member_id")["age"]
            .first()
            .reset_index()
        )
        scatter_base = scatter_base.merge(member_age, on="member_id", how="left")

    scatter_options = {
        "Visit Count vs Total Claimed":       ("visit_count",        "total_claimed",   "Visit Count",        "Total Claimed"),
        "Total Claimed vs Fraud Score":       ("total_claimed",      "fraud_score",     "Total Claimed",      "Fraud Score"),
        "Distinct Providers vs Fraud Score":  ("distinct_providers", "fraud_score",     "Providers Visited",  "Fraud Score"),
        "Total Requested vs Total Rejected":  ("total_claimed",      "total_rejected",  "Total Requested",    "Total Rejected"),
    }
    if has_age:
        scatter_options["Age vs Total Claimed"]  = ("age", "total_claimed",  "Age", "Total Claimed")
        scatter_options["Age vs Fraud Score"]    = ("age", "fraud_score",    "Age", "Fraud Score")
        scatter_options["Age vs Visit Count"]    = ("age", "visit_count",    "Age", "Visit Count")

    selected_scatter = st.selectbox("Select scatter plot", list(scatter_options.keys()), key="scatter_select")
    x_col, y_col, x_label, y_label = scatter_options[selected_scatter]

    if x_col in scatter_base.columns and y_col in scatter_base.columns:
        fig_scatter = px.scatter(
            scatter_base,
            x=x_col,
            y=y_col,
            color="risk_level",
            color_discrete_map={
                "High":   PALETTE["red"],
                "Medium": PALETTE["orange"],
                "Low":    PALETTE["green"],
            },
            hover_data=["member_id"],
            labels={x_col: x_label, y_col: y_label, "risk_level": "Risk Level"},
            opacity=0.7,
        )
        # Add reference line for Total Requested vs Total Rejected
        if x_col == "total_claimed" and y_col == "total_rejected":
            max_val = max(scatter_base[x_col].max(), scatter_base[y_col].max())
            fig_scatter.add_shape(
                type="line", x0=0, y0=0, x1=max_val, y1=max_val,
                line=dict(color="grey", dash="dash", width=1),
            )
            fig_scatter.add_annotation(
                x=max_val * 0.85, y=max_val * 0.9,
                text="Rejected = Requested", showarrow=False,
                font=dict(color="grey", size=11),
            )
        fig_scatter.update_layout(margin=dict(t=20))
        st.plotly_chart(fig_scatter, use_container_width=True)
    else:
        st.info(f"Column not available in the current dataset.")

# ===========================================================================
# TAB 2 — SUSPICIOUS MEMBERS
# ===========================================================================
with tab_suspicious:

    suspicious = df_result[df_result["is_suspicious"]]

    if suspicious.empty:
        st.info("No suspicious members were detected. All charts in this section require at least one flagged member.")
    else:
        row1_left, row1_right = st.columns(2)

        # ── Risk Level Pie ────────────────────────────────────────────────
        with row1_left:
            st.markdown("**Members by Risk Level**")
            risk_counts = df_result["risk_level"].value_counts().reindex(
                ["High", "Medium", "Low"], fill_value=0
            ).reset_index()
            risk_counts.columns = ["Risk Level", "Count"]
            fig_pie = px.pie(
                risk_counts,
                names="Risk Level",
                values="Count",
                color="Risk Level",
                color_discrete_map={
                    "High":   PALETTE["red"],
                    "Medium": PALETTE["orange"],
                    "Low":    PALETTE["green"],
                },
                hole=0.35,
            )
            fig_pie.update_traces(textposition="inside", textinfo="percent+label")
            fig_pie.update_layout(showlegend=True, margin=dict(t=20, b=20))
            st.plotly_chart(fig_pie, use_container_width=True)

        # ── Top 10 by Fraud Score ─────────────────────────────────────────
        with row1_right:
            st.markdown("**Top 10 Members by Fraud Score**")
            top_flagged = (
                suspicious
                .sort_values("fraud_score", ascending=False)
                .head(10)[["member_id", "fraud_score"]]
                .sort_values("fraud_score", ascending=True)
            )
            fig_top = px.bar(
                top_flagged,
                x="fraud_score", y="member_id",
                orientation="h",
                color_discrete_sequence=[PALETTE["red"]],
                labels={"fraud_score": "Fraud Score", "member_id": "Member ID"},
            )
            fig_top.update_layout(yaxis_type="category", margin=dict(t=20))
            st.plotly_chart(fig_top, use_container_width=True)

        row2_left, row2_right = st.columns(2)

        # ── Rules Fired ───────────────────────────────────────────────────
        with row2_left:
            st.markdown("**Which Rules Are Flagging the Most Members**")
            rule_fire = (
                pd.DataFrame({
                    "Rule": list(RULE_LABELS.values()),
                    "Members Flagged": [
                        int(df_result[col].sum()) if col in df_result.columns else 0
                        for col in RULE_LABELS
                    ],
                })
                .sort_values("Members Flagged", ascending=True)
            )
            fig_rules = px.bar(
                rule_fire,
                x="Members Flagged", y="Rule",
                orientation="h",
                color_discrete_sequence=[PALETTE["green"]],
            )
            fig_rules.update_layout(yaxis_type="category", margin=dict(t=20))
            st.plotly_chart(fig_rules, use_container_width=True)

        # ── Top 10 Providers by Overbilling ──────────────────────────────
        with row2_right:
            st.markdown("**Top 10 Providers by Overbilling Ratio**")
            prov_agg = (
                df_claims.groupby("provider")
                .agg(claimed=("claimed_amt", "sum"), accepted=("accepted_amt", "sum"))
                .reset_index()
            )
            prov_agg = prov_agg[prov_agg["accepted"] > 0].copy()
            prov_agg["overbilling_ratio"] = prov_agg["claimed"] / prov_agg["accepted"]
            top_overbill = (
                prov_agg.sort_values("overbilling_ratio", ascending=False)
                .head(10)
                .sort_values("overbilling_ratio", ascending=True)
            )
            if not top_overbill.empty:
                fig_ob = px.bar(
                    top_overbill,
                    x="overbilling_ratio", y="provider",
                    orientation="h",
                    color_discrete_sequence=[PALETTE["orange"]],
                    labels={"overbilling_ratio": "Overbilling Ratio", "provider": "Provider"},
                )
                fig_ob.update_layout(yaxis_type="category", margin=dict(t=20))
                st.plotly_chart(fig_ob, use_container_width=True)
            else:
                st.info("No overbilling data.")

