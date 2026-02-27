---
description: Procedures for maintaining the Shipment QnA Bot logic (IER Framework)
---

# Development Continuity Playbook

Whenever you are tasked with modifying the `shipment_qna_bot` codebase, you MUST follow this IER (Intent-Execution-Result) framework to ensure compatibility.

## 1. PRE-IMPLEMENTATION AUDIT
Before writing any code, verify:
- [x] Is this search or analytics?
- [x] If analytics, check `src/shipment_qna_bot/tools/analytics_metadata.py` for column names.
- [x] If search, check `src/shipment_qna_bot/graph/nodes/retrieve.py` for `_FILTER_FIELDS`.

## 2. THE IER CONSTRAINTS

### INTENT: Classification Guardrails
- Queries with specific Shipment/Container IDs -> **Search Path**.
- Queries requiring aggregations/math -> **Analytics Path**.
- Abrupt topic shifts must trigger a context reset in the `normalizer.py`.

### EXECUTION: Code Generation Rules
- **OData (Search)**: Absolute prohibition of date math (`now()`, `add`).
- **DuckDB (Analytics)**: Must generate valid SQL queries against the `df` view.
- **Date Formatting**: ALWAYS use `strftime(column, '%d-%b-%Y')` for user-facing date columns.
- **Delay Logic**: Default to discharge port (`dp_delayed_dur`).
- **Scope**: RLS is handled automatically by the engine; queries should focus on business logic.

### RESULT: Presentation & Grounding
- All numbers must be grounded in the JSON hits or Pandas dataframes.
- Use markdown tables for multiple-row outputs.

## 3. VERIFICATION PROTOCOL
- Run `PYTHONPATH=src pytest tests/test_duckdb_engine.py` for engine changes.
- Run `PYTHONPATH=src pytest tests/test_integration_live.py` for retrieval changes.

## 4. OPEN RCA TODO (Added 2026-02-19)

### Issue A: Positive feedback closes session and creates context imbalance
- RCA Evidence:
  - `src/shipment_qna_bot/logs/app.log:5988` rewrote user praise (`"NO! you are working very good"`) to `"thank you! how can i assist you further?"`.
  - `src/shipment_qna_bot/logs/app.log:5994` then classified this as `intent=end`.
  - `src/shipment_qna_bot/logs/app.log:5996` cleared session due end intent.
- Probable Cause:
  - Normalizer is over-rewriting non-task feedback into assistant-like "thank you" text.
  - Intent policy treats "thank you" as end (`src/shipment_qna_bot/graph/nodes/intent.py:142`), and route clears session (`src/shipment_qna_bot/api/routes_chat.py:153`).
- TODO Action Plan:
  - Add non-task/feedback guardrail in normalizer to bypass LLM rewrite for short praise/acknowledgment messages.
  - Add intent safety rule: only map to `end` on explicit close phrases (`bye`, `quit`, `end chat`) or very short farewell-only utterances.
  - Add regression test: praise text must not trigger session clear.
  - Add trace metric for `end` classification source (`raw_text` vs `normalized_question`) and confidence.

### Issue B: Bar chart request returns pivot-style table
- RCA Evidence:
  - `src/shipment_qna_bot/logs/app.log:6108` request explicitly asks for "bar chart".
  - `src/shipment_qna_bot/logs/app.log:6122` generated pandas only builds grouped dataframe (`result = df_grouped`).
  - `src/shipment_qna_bot/logs/app.log:6127` final answer rendered markdown table, no chart payload.
- Probable Cause:
  - Analytics node currently returns text/table only; chart extraction is not implemented (`src/shipment_qna_bot/graph/nodes/analytics_planner.py:390`).
  - API can pass `chart_spec` if present (`src/shipment_qna_bot/api/routes_chat.py:180`), but planner never sets it.
- TODO Action Plan:
  - Introduce chart-intent detection in analytics planner for requests containing `bar|line|pie|chart|graph`.
  - Build deterministic `chart_spec` from grouped dataframe output while preserving existing answer/table response structure.
  - Keep matplotlib/seaborn blocked; chart generation should be declarative JSON (not plotting import).
  - Add regression tests:
    - bar-chart request returns non-null `chart_spec`.
    - table still present for backward compatibility.
    - no change to `ChatAnswer` schema contract.

## 5. MILESTONE CHECKLIST (Chart + Security, Added 2026-02-20)

### Non-Negotiable Contract Lock
- [x] Keep `ChatAnswer.answer` unchanged as primary text response.
- [x] Keep existing response envelope keys unchanged (`conversation_id`, `intent`, `answer`, `notices`, `evidence`, `chart`, `table`, `metadata`).
- [x] Preserve frontend request payload shape (`question`, `conversation_id`, `consignee_codes`).
- [x] Do not break general/retrieval rendering behavior while adding chart support.

### M0: Baseline + Rollback Anchor
- [ ] Create and record git tag before implementation (`milestone/pre-chart-security-hardening`).
- [ ] Capture baseline metrics from logs: p95 latency, token/cost outliers, analytics failure rate.
- [ ] Store a short baseline report under `docs/` for comparison after rollout.
- Expected impact: Safe rollback path and measurable progress tracking.

### M1: Frontend Chart Rendering (No Contract Change)
- [ ] Add `data.chart` rendering path in `src/shipment_qna_bot/static/index.html`.
- [ ] Keep existing table rendering as fallback when `chart` is null.
- [ ] Maintain current loader/table UX and avoid layout regression.
- [ ] Add lightweight telemetry logs for "chart requested vs chart rendered".
- Expected impact: User-visible charts without changing backend API contracts.

### M2: Deterministic ChartSpec from Analytics
- [ ] Implement chart-intent detection in `src/shipment_qna_bot/graph/nodes/analytics_planner.py`.
- [ ] Generate declarative `chart_spec` only (no matplotlib/seaborn imports).
- [ ] Keep `table_spec` present for backward compatibility.
- [ ] Add guardrails so invalid chart data falls back to table/text only.
- Expected impact: Bar/line/pie requests return renderable chart payload consistently.

### M3: Identity + Scope Hardening (Fail-Closed)
- [x] Remove unsafe fallback that accepts payload scope when identity is missing in `src/shipment_qna_bot/security/scope.py`.
- [x] Enforce deny-by-default when identity or registry mapping is absent (except explicit controlled dev override).
- [x] Add explicit warning/notice for unauthorized scope attempts.
- [x] Add regression tests in `tests/test_rls.py` for missing-identity denial path.
- Expected impact: Prevents unauthorized data access by payload spoofing.

### M4: Frontend/HTTP Security Hardening
- [x] Sanitize markdown-rendered HTML before DOM insertion in `src/shipment_qna_bot/static/index.html`.
- [x] Add secure session/cookie settings in `src/shipment_qna_bot/api/main.py` (HTTPS, httponly, samesite in non-local env).
- [x] Add CORS/TrustedHost/HTTPS redirect policy by environment.
- [x] Add response security headers (CSP, X-Content-Type-Options, frame protections).
- Expected impact: Reduces XSS/session abuse risk significantly.

### M5: Analytics Execution Hardening
- [x] Replace unrestricted `exec` path in `src/shipment_qna_bot/tools/pandas_engine.py` with constrained execution strategy.
- [x] Restrict builtins and disallow filesystem/network/process access from generated code.
- [x] Add execution timeout/row limits and explicit abort messages.
- [x] Add tests for malicious payload attempts (imports, dunder abuse, file/system access).
- Expected impact: Mitigates high-risk remote code execution vector.

## 6. ANALYTICS PERFORMANCE & RESOURCE GUARDRAILS (Updated 2026-02-27)

### DuckDB Direct-Query Strategy
- **Zero-Load Architecture**: Data is NOT loaded into memory. Queries run directly against Parquet files via `read_parquet`.
- **View-Based RLS**: The engine creates a temporary view `df` that is already filtered by `consignee_codes` using `list_has_any`.
- **Memory Efficiency**: Vectorized execution engine ensures low RAM overhead even with multiple concurrent users.

### Resilient Schema Discovery
- **Requirement**: Never assume a column in `ANALYTICS_METADATA` exists in the parquet file.
- **Implementation**: `DuckDBAnalyticsEngine` uses a `LIMIT 5` query to discover available schema before generation.
- **Impact**: Prevents SQL errors due to missing columns while providing a data sample for LLM context.

### Graph Flow Optimization
- **Bypass Rule**: Analytics queries skip `judge` and `answer` nodes. Flow: `planner` -> `END`.
- **Retry Policy**: Default `max_retries` is capped at **1** to prevent infinite loops and cost spikes.

### Test Isolation
- **Suffix Rule**: All test-mode cache files must use the `.test.parquet` suffix (enforced in `BlobAnalyticsManager`).
- **Safety**: Prevents mock/test data from being accidentally loaded in production environments.

## 7. MILESTONE CHECKLIST (Analytics Optimization, Added 2026-02-27)

### M8: Memory & Latency Lockdown (Complete)
- [x] Implement in-memory singleton cache for daily master dataset.
- [x] Implement schema-aware resilient column pruning.
- [x] Refactor graph to bypass `judge` for analytics path.
- [x] Reduce graph `max_retries` from 2 to 1.
- [x] Isolate test/production cache files via filename suffixes.
- [x] Enforce `black` and `isort` formatting across `src/`.
- Expected impact: Reduced OOM errors and p95 latency for analytics queries.
