# Developer Continuity: Shipment Q&A Bot

## Architecture Overview
The bot is built using **LangGraph** with a stateful workflow.
**Flow:** `Normalizer` -> `Extractor` -> `Intent` -> `Router` -> (`Planner` / `AnalyticsPlanner` / `Clarification`) -> `Retrieve` -> `Answer` -> `Judge`.

## Key Systems

### 1. Ready Reference System (The "Brain")
*   **Location:** `docs/ready_ref.md`
*   **Purpose:** Acts as the Single Source of Truth for business logic and column definitions.
*   **Usage:** The `AnalyticsPlanner` injects this file into the LLM's system prompt.
*   **Extensibility:** To teach the bot about a new column or a new type of query (e.g. "What is a 'Cold' container?"), **edit this file**. Do NOT hardcode logic in Python.

### 2. Clarification Workflow (The "Voice")
*   **Node:** `src/shipment_qna_bot/graph/nodes/clarification.py`
*   **Trigger:** The `Intent` node detects ambiguous queries (e.g. "Show me dates") as `clarification`.
*   **Behavior:** The node uses conversation history to ask a polite, context-aware follow-up question.

### 3. Dynamic Answering (The "Presentation")
*   **Node:** `src/shipment_qna_bot/graph/nodes/answer.py`
*   **Logic:**
    *   It does **not** use hardcoded column filtering anymore.
    *   It provides a **Unified Context** containing all relevant columns (status, both dates, priority flags, etc.).
    *   It injects `ready_ref.md` into the *Answer* prompt so the LLM knows which dates to prioritize based on the user's intent.

## Development Workflows

### Adding New Columns
1.  Ensure the column is in `ANALYTICS_METADATA` (`analytics_metadata.py`).
2.  Add the column to the table in `docs/ready_ref.md`.
3.  (Optional) Add a "Reference Scenario" in `docs/ready_ref.md` if the column has special logic (e.g. "delayed" means > 3 days).

### Debugging
*   **Ambiguous Queries:** Check `intent.py` logs. If it classifies as `clarification`, the bot will ask a question.
*   **Wrong Data:** Check `ready_ref.md`. The bot likely followed an instruction there.
*   **Missing Data in Answer:** Check `answer.py` -> `priority_fields` list. Ensure the field is being passed to the context.

## Branch Strategy
*   Current Development: `vec_pd_dev`
