# ClearCSV five-minute demo script

## 00:00–00:30 — Problem and scope

Show the ClearCSV header. Say: “ClearCSV helps review messy CSV data without silently changing it. Rules identify verifiable issues, optional AI adds bounded suggestions, and every proposed change requires human review.”

## 00:30–01:10 — Load synthetic data

Click **Try sample**. Show `customers-dirty.csv`, the row and column counts, leading-zero IDs, Unicode names, empty cells, and the original table. Point out the visible limits and that values remain text.

## 01:10–02:00 — Analyze and show coverage

Click **Analyze data**. Show the coverage message: rules check every row; AI reviews only a bounded sample. In fixture mode, point to its explicit fixture warning. In live mode, show the provider warning or successful coverage honestly; do not present fixture output as a live call.

## 02:00–03:15 — Human review

Filter proposals by source or category. Accept a whitespace normalization proposal, then reject another proposal. Show original versus suggested values, source, explanation, and status. Point to a missing-value finding without a fabricated replacement. Show the exact duplicate proposal as an optional row exclusion, not an automatic deletion.

## 03:15–04:00 — Compare and export

Switch from **Original** to **With accepted changes**. Explain that only accepted proposals affect the effective view. Enable spreadsheet-safe export to demonstrate formula-like value protection, then download. Faithful export remains available when logical values must be preserved exactly.

## 04:00–04:40 — Architecture and safeguards

Show the repository tree: React/Vite frontend and FastAPI backend. Explain immutable original bytes, stable IDs, atomic revision-checked review decisions, deterministic rules, validated AI suggestions, bounded payload, in-memory TTL, and no secrets in the frontend.

## 04:40–05:00 — Limits and close

State the 2 MiB, 1,000-row, 30-column limits and single-process volatile-memory scope. Mention that browser E2E and live provider smoke are pending in this environment if they were not run. Never claim the repository was published, the video was recorded, or the challenge form was submitted.

### Provider-error fallback

If the provider fails, show the sanitized AI-unavailable warning and continue with deterministic findings and human review. Do not invent a provider response or silently switch live mode to fixture mode.
