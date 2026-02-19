---
description: Procedures for maintaining the Shipment QnA Bot logic (IER Framework)
---

# Development Continuity Playbook

Whenever you are tasked with modifying the `shipment_qna_bot` codebase, you MUST follow this IER (Intent-Execution-Result) framework to ensure compatibility.

## 1. PRE-IMPLEMENTATION AUDIT
Before writing any code, verify:
- [ ] Is this search or analytics?
- [ ] If analytics, check `src/shipment_qna_bot/tools/analytics_metadata.py` for column names.
- [ ] If search, check `src/shipment_qna_bot/graph/nodes/retrieve.py` for `_FILTER_FIELDS`.

## 2. THE IER CONSTRAINTS

### INTENT: Classification Guardrails
- Queries with specific Shipment/Container IDs -> **Search Path**.
- Queries requiring aggregations/math -> **Analytics Path**.
- Abrupt topic shifts must trigger a context reset in the `normalizer.py`.

### EXECUTION: Code Generation Rules
- **OData (Search)**: Absolute prohibition of date math (`now()`, `add`).
- **Pandas (Analytics)**: Must use `result = ...` assignment. No global side effects.
- **Delay Logic**: Default to discharge port (`dp_delayed_dur`).

### RESULT: Presentation & Grounding
- All numbers must be grounded in the JSON hits or Pandas dataframes.
- Use markdown tables for multiple-row outputs.

## 3. VERIFICATION PROTOCOL
- Run `pytest tests/test_pandas_flow.py` for analytics changes.
- Run `pytest tests/test_integration_live.py` for retrieval changes.

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
