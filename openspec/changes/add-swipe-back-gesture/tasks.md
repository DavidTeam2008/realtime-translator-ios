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

### Task 1: Add red unit tests and implement edge-swipe policy

- [x] Task 1: policy unit tests fail first, then the pure policy makes them pass.

**Files:** `DuiyiTests/EdgeSwipeBackPolicyTests.swift`, `Duiyi/Features/Shared/EdgeSwipeBackPolicy.swift`

1. Add the acceptance/rejection matrix tests before the policy type exists.
   - Expected: focused unit test command fails because `EdgeSwipeBackPolicy` is missing.
   - Covers: R1/S1.1/A1
2. Add the pure policy with the documented thresholds.
   - Expected: focused unit test command passes.
   - Covers: R1/S1.1/A1

### Task 2: Add red UI test and implement root edge gesture

- [x] Task 2: UI test fails first, then the root gesture returns to home.

**Files:** `DuiyiUITests/SimultaneousFlowTests.swift`, `Duiyi/App/RootView.swift`

1. Add a UI test that enters the face-to-face module and performs a leading-edge right swipe.
   - Expected: UI test fails against the current app because no back gesture exists.
   - Covers: R1/S1.1/S1.2/R2/S2.1/S2.2/R3/S3.1/A2
2. Attach the simultaneous leading-edge drag gesture and pop once when the policy allows.
   - Expected: UI test passes; existing `nav-home` navigation test still passes.
   - Covers: R1/S1.1/R2/S2.1/R3/S3.1/A2

### Task 3: Update baseline and verification counts

- [x] Task 3: baseline check fails first, then baseline/docs match the new totals.

**Files:** `harness/test-baseline.json`, `references/verification.md`

1. Run `make check-tests` after adding tests but before updating the baseline.
   - Expected: baseline check fails because the documented counts are stale.
   - Covers: A3
2. Raise unit/UI floors and update documented counts only by the tests actually added.
   - Expected: `make check-tests` passes with 144 unit + 4 UI and device 148.
   - Covers: A3
