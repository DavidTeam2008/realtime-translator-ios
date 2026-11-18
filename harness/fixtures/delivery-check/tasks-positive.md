# Delivery Contract

- Change: fixture-native
- Level: L2
- Owner: david
- Base: 5ad38d1
- Scope allow: Makefile, tools/, harness/, harness-kit/, docs/, references/, Duiyi/Services/AGENTS.md
- Scope deny: openspec/specs/, Duiyi/Features/
- Acceptance: A1=schema fixture only (review)
- Verify: make delivery-check-fixtures
- Evidence: review (optional)
- Review: not required
- Archive gate: all_tasks
- CI: not applicable

## Tasks

### Task 1: fixture task

- [x] Task 1: structure fixture is complete.

**Files:** `harness/fixtures/delivery-check/tasks-positive.md`

1. `Expected`: delivery-check parses the contract and task checkbox.
