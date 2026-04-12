---
description: "Step-by-step workflow for implementing a new feature: design, implement, test, integrate."
mode: "agent"
---
# New Feature Implementation

You're implementing a new feature for PDF Editor Pro. Follow this workflow strictly:

## Step 1 — Design
1. Read related existing code to understand the current architecture
2. Identify which modules are affected (core/, ui/, or both)
3. Plan the data model (Enum + dataclass) and factory functions
4. List all files to create or modify

## Step 2 — Implement Core
1. Create/modify `core/` modules first
2. Use `create_*()` factory functions
3. Add `to_dict()` / `from_dict()` to new dataclasses
4. Add `logger = logging.getLogger(__name__)` to every new module
5. Google-style docstrings in Spanish

## Step 3 — Implement UI
1. Create/modify `ui/` components
2. Apply dark theme stylesheet
3. All user text in Spanish
4. Signals → slots with `_on_<event>()` naming

## Step 4 — Write Tests
1. Create `tests/<category>/test_<module>.py` for each new module
2. Minimum 10 tests: happy path, edge cases, error cases
3. Run: `python -m pytest tests/ -q`
4. Fix any failures — do not proceed with failures

## Step 5 — Integrate
1. Wire feature into main window / menu
2. Run full test suite: `python -m pytest tests/ -q`
3. Verify no regressions (all 1682+ tests must pass)
