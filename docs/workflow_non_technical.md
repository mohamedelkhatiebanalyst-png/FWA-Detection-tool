# Insurance FWA Detection Tool — Non-Technical Workflow

## What Is This Tool?

This tool helps insurance companies identify members and providers who may be committing **Fraud, Waste, or Abuse (FWA)** in their health insurance claims. Instead of manually reviewing thousands of claims, the tool automatically scans your data and highlights the cases most worth investigating.

---

## Who Is It For?

- Claims reviewers and investigators
- Insurance operations teams
- Compliance and audit departments

No programming knowledge is required to use it.

---

## Step-by-Step User Workflow

### Step 1 — Prepare Your Data File

Before using the tool, you need a claims data file in **CSV or Excel format**.

The file must contain **all** of the following columns (exact names matter):

| Column Name | What It Represents |
|---|---|
| Card No | The member's insurance ID |
| Provider Claimed Amount | How much the provider requested |
| Accepted Amount | How much was actually approved |
| Rejected Amount | How much was rejected by the insurer |
| Provider Name | The clinic or hospital name |
| Provider City | The city where the provider is located |
| Treatment Doctor Name | The doctor who provided the treatment |
| Accident Date | The date the service was provided |
| ICD Code | The diagnosis code for the claim |
| Claim Form Type | The type of service (e.g., doctor visit, lab, x-ray, dental, optical, physiotherapy, hospital admission) |
| Chronic | Whether the claim is for a chronic condition (yes/no) |
| Age | The member's age |

All columns are required. If any column is missing, the tool will stop and tell you exactly what to fix before you can proceed.

---

### Step 2 — Upload Your File

Open the tool in your browser and drag or click to upload your CSV or Excel file.

The tool will immediately:
- Check every required column and show a green checkmark if found or a red X if missing
- Show a preview of the first 10 rows of your data

If any column is missing, you must fix the file and re-upload before the analysis can run.

---

### Step 3 — Review Detection Layers (Sidebar)

On the left side of the screen, you will see **5 detection layers**. Each one can be switched on or off using a checkbox. The sidebar also shows a description of every rule inside each layer, so you always know exactly what is being checked.

Each layer and its rules are fixed and clearly defined — thresholds are computed automatically from your data. There are no manual settings to misconfigure.

#### 📈 Overuse Detection
Flags members who use their insurance far more than typical.
- Member visits providers far more often than the typical member
- Member's total requested amount is unusually high
- Member's average cost per visit is unusually high

#### 📅 Unusual Claim Timing
Flags suspicious patterns in *when* and *where* claims are submitted.
- 3 or more non-doctor-visit claims submitted within any 7-day window
- Same service type (e.g., lab) at two different providers on the same day
- Claims appearing in two or more different cities on the same day
- Abnormally high number of claims in a single month

#### 🏥 Provider Billing Abuse
Flags providers (clinics, hospitals) who bill in suspicious ways.
- Provider requested more than twice what was approved
- Provider's claims are rejected at an unusually high rate

#### 🔍 Suspicious Visit Patterns
Flags suspicious patterns in *where* and *who* a member visits.
- Visiting an unusually high number of different clinics or hospitals
- A clinic where an unusually high number of different doctors are treating patients
- Claiming the same diagnosis at many different providers

#### 🏷️ Claim Type & Chronic Patterns
Flags abuse related to the type of service claimed and chronic benefit usage.
- Submitting the same type of service (e.g., lab test) twice on the same day
- An unusually high number of hospital (inpatient) admissions
- Using a suspiciously wide variety of service types
- An abnormally high proportion of claims marked as "chronic"

---

### Step 4 — Run the Analysis

Click the **"Run FWA Analysis"** button. The tool will scan all claims and apply all the active detection rules. This takes a few seconds.

When done, three navigation buttons will appear to take you to the results.

---

### Step 5 — Review Results (Three Pages)

#### 📊 Overview Page
A summary dashboard showing:
- Total number of members analyzed
- How many were flagged as suspicious
- What percentage are suspicious
- How many are at high risk
- The average fraud score across all members
- The exact cutoff values the tool used for each rule (so you understand what triggered a flag)

#### 📈 Charts & EDA Page
Two tabs of visual charts:
- **Dataset EDA tab** — data distribution, correlation matrix, rule co-occurrence heatmap, monthly time series, claim type analysis, and scatter plots (including age vs requested amount)
- **Suspicious Members tab** — breakdown by risk level, top fraud scores, which rules are firing most, top overbilling providers

#### 📥 Export Page
Download your results as a formatted Excel file:
- **Suspicious members only** — a focused list of flagged cases to investigate
- **Full results** — all members with their scores and which rules they triggered

#### 🔎 Member Lookup Page
Search for any member by ID and inspect all their raw claims alongside their fraud flags — useful for understanding exactly why a member was flagged.

---

## How Is a Member Flagged?

Each detection rule produces one point toward a member's **Fraud Score**. The tool has 16 rules in total.

| Fraud Score | Risk Level |
|---|---|
| 0 – 1 | Low |
| 2 – 4 | Medium |
| 5 or more | High |

A member is marked **Suspicious** if their score is **2 or higher**.

The score reflects how many independent warning signs were triggered, not just one rule — this reduces false positives.

---

## What the Tool Does NOT Do

- It does **not** confirm fraud — it identifies cases that warrant human review.
- It does **not** access any external system — all processing happens locally with your uploaded file.
- It does **not** store your data — once you close the browser, nothing is saved.

---

## Typical Use Case

1. An investigator uploads the monthly claims extract every week or month.
2. They adjust the detection sensitivity based on the team's workload (stricter = fewer, higher-priority cases).
3. They export the suspicious members list and assign cases to the investigation team.
4. High-risk members (score 5+) are escalated for immediate review.
5. Medium-risk members (score 2–4) are queued for routine review.
