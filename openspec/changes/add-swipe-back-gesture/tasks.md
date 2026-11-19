# Delivery Contract

- Change: add-swipe-back-gesture
- Level: L2
- Owner: david
- Base: 13b8b4d8999a6dc0360461a3fc788e69f11609aa
- Scope allow: openspec/changes/add-swipe-back-gesture/, Duiyi/App/RootView.swift, Duiyi/Features/Shared/, DuiyiTests/, DuiyiUITests/, harness/receipts/, harness/evidence/, harness/reviews/, harness/records/, harness/plans/, harness/test-baseline.json, references/verification.md, docs/04-roadmap.md
- Scope deny: openspec/specs/, Duiyi.xcodeproj/, .env, "*.p12", "*.mobileprovision", .githooks/, .github/workflows/, AGENTS.local.md
- Acceptance: A1=edge-swipe policy accepts eligible leading-edge right swipes only (unit-tests-pass); A2=module page swipe-back returns to home and existing nav still works (ui-tests-pass); A3=test baseline and verification counts updated with no existing assertion changes (review)
- Verify: make delivery-check CHANGE=add-swipe-back-gesture; make verify-static; make release-check
- Evidence: unit-tests-pass (required); ui-tests-pass (required); review (required)
- Review: required; path=harness/reviews/2026-11-19-add-swipe-back-gesture.md; covers Base..Head; P0/P1 closed
- Archive gate: all tasks checked + Harness PASS + required review closed + provenance/validate receipts fresh
- CI: not applicable (static CI is not asserted as delivery evidence)

## Tasks

### Task 1: Add red unit tests for edge-swipe policy

- [ ] Task 1: policy tests fail before implementation.

**Files:** `DuiyiTests/EdgeSwipeBackPolicyTests.swift`

1. Add acceptance and rejection matrix tests for the not-yet-existing `EdgeSwipeBackPolicy`.
   - Expected: focused unit test command fails because the policy type does not exist.
   - Covers: R1/S1.1/A1

### Task 2: Add red UI test for swipe-back navigation

- [ ] Task 2: UI test fails before the gesture is implemented.

**Files:** `DuiyiUITests/SimultaneousFlowTests.swift`

1. Add a UI test that enters a module page and performs a leading-edge right swipe.
2. Assert the app returns to home; keep the existing navigation test intact.
   - Expected: UI test fails against the current app because the edge swipe does not navigate.
   - Covers: R1/S1.1/R3/S3.1/A2

### Task 3: Implement policy and root gesture

- [ ] Task 3: production behavior passes the policy and UI tests.

**Files:** `Duiyi/Features/Shared/EdgeSwipeBackPolicy.swift`, `Duiyi/App/RootView.swift`

1. Add the pure policy with the documented thresholds.
2. Attach a simultaneous leading-edge drag gesture to the navigation stack and pop once when eligible.
3. Preserve existing button navigation and task lifecycle behavior.
   - Expected: unit and UI tests pass; manual simulator swipe returns one level.
   - Covers: R1/S1.1/S1.2/R2/S2.1/S2.2/A1/A2

### Task 4: Update test baseline and verification counts

- [ ] Task 4: baseline and docs match the new test totals.

**Files:** `harness/test-baseline.json`, `references/verification.md`

1. Raise unit/UI floors and update documented counts only by the tests actually added.
2. Run baseline and docs checks.
   - Expected: `make check-tests` and `make check-docs` pass with the new counts.
   - Covers: A3
