---
description: "Safe refactoring workflow: refactor code while keeping all 1682+ tests passing. Runs tests before and after every change."
mode: "agent"
---
# Safe Refactoring

Refactor the specified code while ensuring zero test regressions.

## Rules
1. **Test first**: Run `python -m pytest tests/ -q` BEFORE any change
2. **Small steps**: One logical change at a time
3. **Test after each step**: Run tests after EVERY modification
4. **Rollback on failure**: If tests break, undo and try a different approach
5. **No behavior changes**: Refactoring must not alter external behavior

## Process
1. Run full test suite — record baseline (must be ≥1682 passing)
2. Read the code to refactor completely
3. Plan changes: extract method, rename, simplify, move
4. Apply ONE change
5. Run tests — if any new failures, revert immediately
6. Repeat steps 4-5 until done
7. Run final full suite — confirm same or more tests passing

## What You Can Do
- Extract functions/methods
- Rename for clarity (use `vscode_renameSymbol`)
- Simplify conditionals
- Remove dead code
- Improve type hints

## What You Cannot Do
- Change public API signatures
- Remove or modify tests
- Skip running tests
- Change behavior "just a little"
