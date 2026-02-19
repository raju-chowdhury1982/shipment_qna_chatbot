# Shipment QnA Agent Workflow Runbook

This document is the operational workflow reference for future updates and safe rollout.

## 1. Goal

- Keep production behavior stable.
- Make schema/date policy changes in one controlled process.
- Add optional capabilities (for example weather impact) as plug-and-play modules.

## 2. Runtime Graph Workflow

- Entry flow:
  - `normalizer` -> `extractor` -> `intent` -> `router`
- Retrieval path:
  - `planner` -> `retrieve` -> `answer` -> `judge`
- Analytics path:
  - `analytics_planner` -> `judge`
- Static/clarification path:
  - `static_info` -> end
  - `clarification` -> end
- Retry loop:
  - `judge` routes back to `planner` or `analytics_planner` until satisfied or retry limit.

Primary wiring file: `src/shipment_qna_bot/graph/builder.py`

## 3. Date Column Policy (DP/FD)

- DP ETA window and overdue logic: use `best_eta_dp_date` as default.
- DP actual-arrival check: use `ata_dp_date` (fallback only when explicitly needed).
- FD ETA logic: use `best_eta_fd_date` as default.
- Sorting priority (latest first):
  - `best_eta_dp_date` -> `best_eta_fd_date` -> `ata_dp_date` -> `derived_ata_dp_date` -> `eta_dp_date` -> `eta_fd_date`
- Date formatting is always after sorting.

Reference: `docs/ready_ref.md`

## 4. Schema Change Workflow (Index + Ingestion)

Use this flow whenever index fields are renamed/added/removed.

1. Update index schema in `src/scripts/create_index.py`.
2. Update payload mapping in `src/scripts/reindex_data.py`.
3. Verify no removed field is still sent in payload.
4. Recreate index (same name) using `create_index.py`:
   - The script deletes existing index first, then creates a new one.
5. Re-ingest or reconcile-upsert:
   - Full load: `src/scripts/ingest_all.py`
   - CDC/missing-only: `src/scripts/reconcile_index.py`
6. Validate:
   - Index doc count vs source row count.
   - No schema mismatch upload errors.
   - Key scenarios in `docs/ready_ref.md`.

## 5. CDC Reconcile Behavior

`reconcile_index.py` uploads:

- Missing docs in index.
- Changed docs based on manifest hash comparison.

It does not blindly re-embed everything if manifest and index are healthy.

Key outputs:

- `data/reports/reconcile_report.json`
- `data/reports/upload_candidates.txt`
- `data/reports/changed_by_cdc.txt`
- dead-letter file when failures occur

## 6. Known Failure Pattern And Fix

Symptom:

- Upload fails with: field/property does not exist in index schema.

Root cause:

- Payload contains a column not present in the recreated index (for example stale `revised_eta`).

Fix:

1. Remove/rename stale field in `reindex_data.py` mapping.
2. Recreate index from updated `create_index.py`.
3. Re-run reconcile/upload.

## 7. Query Calibration Rules (Operational)

For "not yet arrived at DP":

- `ata_dp_date.isna()`

For "failed/missed ETA at DP":

- `(ata_dp_date.isna()) & (best_eta_dp_date <= today)`

Location filter guidance:

- Use `str.contains(..., na=False, case=False, regex=True)` on `discharge_port` or `final_destination` as needed.

## 8. Optional Weather Impact Extension (Plug-And-Play)

Design target: add weather impact without degrading current baseline behavior.

Required structure:

- Separate tool file:
  - `src/shipment_qna_bot/tools/weather_impact_tool.py`
- Separate node file:
  - `src/shipment_qna_bot/graph/nodes/weather_impact.py`
- Conditional graph wiring:
  - `retrieve` -> `weather_impact` -> `answer` only for weather-impact intent

Safety guardrails:

1. Feature flag default OFF.
2. Strict intent gating (weather questions only).
3. Hard timeout and graceful fallback.
4. Cache weather lookups by location/date window.
5. Use structured shipment fields, not free-text route parsing.

## 9. Change Control Checklist

Before merge:

1. Confirm branch and changed files.
2. Run targeted compile/tests for touched modules.
3. Validate at least one retrieval and one analytics scenario.
4. Re-run delayed/not-arrived DP scenario from `docs/ready_ref.md`.
5. Confirm no deprecated field names remain in payload or prompts.
6. Document any new columns and fallback rules in `docs/ready_ref.md`.

After deploy:

1. Monitor upload failures and dead-letter volume.
2. Track response latency and retry-rate changes.
3. Roll back by disabling feature flags if optional modules regress.

