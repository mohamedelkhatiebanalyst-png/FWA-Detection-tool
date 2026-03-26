"""
config.py
---------
Shared column mapping, constants, and utility functions used across all pages.
"""

import pandas as pd

# ---------------------------------------------------------------------------
# COLUMN MAPPING
# ---------------------------------------------------------------------------
COLUMN_MAP: dict[str, str] = {
    "Card No":                 "member_id",
    "Provider Claimed Amount": "claimed_amt",
    "Provider Claimed Amt":    "claimed_amt",
    "Accepted Amount":         "accepted_amt",
    "Accepted Amt":            "accepted_amt",
    "Provider Name":           "provider",
    "Provider City":           "provider_city",
    "provider city":           "provider_city",
    "Treatment Doctor Name":   "treatment_doctor",
    "treatment doctor name":   "treatment_doctor",
    "Accident Date":           "accident_date",
    "accident date":           "accident_date",
    "ICD Code":                "icd_code",
    "icd code":                "icd_code",
    "Claim Form Type":         "claim_form_type",
    "claim form type":         "claim_form_type",
    "Chronic":                 "chronic",
    "chronic":                 "chronic",
    "Age":                     "age",
    "age":                     "age",
    "Rejected Amount":         "rejected_amt",
    "rejected amount":         "rejected_amt",
}

REQUIRED_COLUMNS: dict[str, str] = {
    "Card No":                 "member_id",
    "Provider Claimed Amount": "claimed_amt",
    "Accepted Amount":         "accepted_amt",
    "Provider Name":           "provider",
    "Provider City":           "provider_city",
    "Treatment Doctor Name":   "treatment_doctor",
    "Accident Date":           "accident_date",
    "ICD Code":                "icd_code",
    "Claim Form Type":         "claim_form_type",
    "Chronic":                 "chronic",
    "Age":                     "age",
    "Rejected Amount":         "rejected_amt",
}

REQUIRED_INTERNAL: set[str] = set(REQUIRED_COLUMNS.values())


# ---------------------------------------------------------------------------
# UTILITIES
# ---------------------------------------------------------------------------

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = df.columns.str.strip()
    return df.rename(columns=COLUMN_MAP)


def validate(df: pd.DataFrame) -> list[str]:
    errors = []
    if df.empty:
        errors.append("The uploaded file is empty.")
        return errors
    missing = REQUIRED_INTERNAL - set(df.columns)
    if missing:
        reverse = {v: k for k, v in COLUMN_MAP.items()}
        missing_names = [reverse.get(c, c) for c in sorted(missing)]
        errors.append(f"Missing required columns: **{', '.join(missing_names)}**")
    if "claimed_amt" in df.columns:
        if not pd.to_numeric(df["claimed_amt"], errors="coerce").notna().all():
            errors.append("`Provider Claimed Amount` contains non-numeric values.")
    if "accepted_amt" in df.columns:
        if not pd.to_numeric(df["accepted_amt"], errors="coerce").notna().all():
            errors.append("`Accepted Amount` contains non-numeric values.")
    return errors


def require_results(st_module) -> bool:
    """Call at the top of each results page. Stops the page if no analysis has been run."""
    if "df_result" not in st_module.session_state:
        st_module.warning(
            "No analysis results found. "
            "Please go to **Home** to upload your data and run the analysis first."
        )
        st_module.stop()
        return False
    return True
