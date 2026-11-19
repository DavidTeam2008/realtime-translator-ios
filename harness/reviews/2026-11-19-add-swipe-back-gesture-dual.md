---
base: 13b8b4d8999a6dc0360461a3fc788e69f11609aa
head: 354aeeb0741513a42259d073a3fd041faae741d8
reviewer: claude-code / code-review (standards + spec, two parallel fresh contexts)
p0: 0
p1: 2
p2: 8
verdict: PASS_WITH_FINDINGS
gates: PARTIAL
---

# Dual Review — add-swipe-back-gesture

- Range: `13b8b4d8999a6dc0360461a3fc788e69f11609aa...354aeeb0741513a42259d073a3fd041faae741d8`
- Code scope: `Duiyi/`, `DuiyiTests/`, `DuiyiUITests/` (docs/openspec/harness changes excluded from judgement)
- Raw axes: [standards](2026-11-19-add-swipe-back-gesture-standards.md) · [spec](2026-11-19-add-swipe-back-gesture-spec.md) · [gates](2026-11-19-add-swipe-back-gesture-gates.md)

**Verdict: PASS WITH FINDINGS.** No P0. The implementation faithfully matches the design (thresholds, mount point, pop call, animation) and no documented hard standard is broken. Two P1 verification gaps: the spec's own UI-verification obligations for S2.1 and S1.2 are not covered, while `tasks.md` claims they are. Gates are PARTIAL: the test-baseline gate passes, but Xcode is not installed on this host, so the focused unit/UI tests could not execute, and `make verify-static` is blocked by unrelated uncommitted worktree changes.

## Standards axis

Verdict: PASS WITH FINDINGS — 0 P0 / 0 P1 / 6 P2.

Key findings:

1. **P2 — Weak UI assertion** (`DuiyiUITests/SimultaneousFlowTests.swift:94`). `waitForExistence` on `home-module-simultaneous` may pass without proving the pushed page was dismissed. (The recorded red run did fail at this assertion, so the signal worked for this change; still worth strengthening.)
2. **P2 — Coordinate-based gesture synthesis** (`SimultaneousFlowTests.swift:90-92`) vs. `DuiyiUITests/AGENTS.md §3` ("不用…坐标定位"). Element lookup still uses identifiers and an edge-origin swipe has no identifier-based expression, so this is a judgement call; extract a named helper with rationale.
3. **P2 — `maximumVerticalDrift` guard not isolated** (`Duiyi/Features/Shared/EdgeSwipeBackPolicy.swift:18`). Both rejection cases already fail the earlier `abs(height) < width` guard, so removing line 18 would not turn a test red. Add a `120x90` reject and `120x80` accept.
4. **P2 — Unnecessary `@MainActor`** on the pure-logic suite (`DuiyiTests/EdgeSwipeBackPolicyTests.swift:5`); peer pure-policy suites are unannotated.
5. **P2 — Duplicated `shouldPop` call shape** across six cases (Duplicated Code smell); extract a helper.
6. **P2 — Root `.simultaneousGesture` may coexist with the system interactive pop** (`Duiyi/App/RootView.swift:22-34`). If the native pop ever re-enables, a depth-2 stack (history → task detail) could double-pop; only depth 1 is tested. Verify on device.

Cleared: dependency/import rules (only `CoreGraphics` in Features), task/speech/translation contracts untouched, test framework and naming conventions, baseline/docs counts (+5 unit, +1 UI, device 148), existing assertions unchanged, thin `RootView`, thresholds centralized in `Shared/`.

## Spec axis

Verdict: PASS WITH FINDINGS — 0 P0 / 2 P1 / 2 P2.

Key findings:

1. **P1 — S2.1 home edge-swipe "no navigation" not UI-verified (missing).** `design.md:27` requires "首页边缘右滑不产生导航"; `tasks.md:39` claims the new UI test covers S2.1, but `testSwipeBackFromModule` never swipes on home. The policy unit test `rejectsAtRoot` covers the decision, not the mounted gesture.
2. **P1 — S1.2 history-page swipe-back unverified (partial).** R1 names 模块、历史、任务详情; `tasks.md:39` claims S1.2 coverage, but the only new UI test enters face-to-face. The root gesture is generic so history likely works, but no UI evidence proves it.
3. **P2 — Swipe-back UI assertion can false-pass (partial).** Does not assert `nav-home` disappeared or that home is hittable.
4. **P2 — S1.1/S3.1 task-state clauses unverified (partial).** "已有任务保持进行中" / "听写停止" are not asserted; design assigns this to manual review only.

Correctly matched to design: edge width 24pt, horizontal ≥ 60pt, `abs(height) < width` and `≤ 80pt`; `.simultaneousGesture` on `RootView`'s `NavigationStack`; `coordinator.pop()` inside `withAnimation(.easeInOut(duration: 0.2))`; non-matching gestures not consumed. No scope creep in `Duiyi*/` (122 additive lines, 4 files). A1/A2/A3 satisfied at the code/test-count level.

## Normalized P0/P1/P2 findings

| ID | Severity | Axis | Finding | Location | Type | Action |
|---|---|---|---|---|---|---|
| SPEC-1 | P1 | Spec | S2.1 / design verification "首页边缘右滑不产生导航" has no UI test; `tasks.md` claims coverage | `DuiyiUITests/SimultaneousFlowTests.swift:83-98`; `design.md:27`; `tasks.md:39` | missing verification | Add home-page edge-swipe UI test asserting no navigation |
| SPEC-2 | P1 | Spec | S1.2 history (and task-detail) swipe-back unverified; `tasks.md` claims S1.2 coverage | `DuiyiUITests/SimultaneousFlowTests.swift:82-120`; `spec.md:20-24`; `tasks.md:39` | partial verification | Add history swipe test; optionally task-detail depth-2 case |
| STD-1 / SPEC-3 | P2 | Standards + Spec | UI test can false-pass: only asserts `home-module-simultaneous` exists, not that the pushed page was dismissed | `DuiyiUITests/SimultaneousFlowTests.swift:94` | test robustness | Assert `nav-home` no longer exists and/or home is hittable |
| SPEC-4 | P2 | Spec | S1.1/S3.1 "task remains in progress" / "dictation stops" unverified | `spec.md:16`, `spec.md:61`; `DuiyiUITests/SimultaneousFlowTests.swift:83-98` | partial verification | Add device test or record manual observation in evidence |
| STD-2 | P2 | Standards | Coordinate-based gesture synthesis vs. `DuiyiUITests/AGENTS.md §3` | `DuiyiUITests/SimultaneousFlowTests.swift:90-92` | judgement call | Extract named helper with rationale comment |
| STD-3 | P2 | Standards | `maximumVerticalDrift` guard never exercised in isolation | `Duiyi/Features/Shared/EdgeSwipeBackPolicy.swift:18`; tests `:57-69` | coverage gap | Add `120x90` reject and `120x80` accept cases |
| STD-4 | P2 | Standards | `@MainActor` on pure-logic test suite | `DuiyiTests/EdgeSwipeBackPolicyTests.swift:5` | convention | Remove annotation |
| STD-5 | P2 | Standards | Duplicated `shouldPop` invocation shape across six cases | `DuiyiTests/EdgeSwipeBackPolicyTests.swift:11-66` | Duplicated Code smell | Extract a private helper |
| STD-6 | P2 | Standards | Root simultaneous gesture may coexist with native interactive pop; depth-2 double-pop untested | `Duiyi/App/RootView.swift:22-34` | robustness risk | Verify depth-2 pop on device; add UI case if needed |

Counts: **P0 = 0, P1 = 2, P2 = 8** raw findings (7 distinct; STD-1 and SPEC-3 are the same underlying issue reported by both axes).

## Gate summary

Raw: [gates](2026-11-19-add-swipe-back-gesture-gates.md). Overall: **PARTIAL**.

| Gate | Exit | Result |
|---|---|---|
| `python3 tools/check-test-baseline.py` | 0 | PASS — 144 unit / 4 UI / device 148; skip whitelist consistent |
| `make test-one TEST=DuiyiTests/EdgeSwipeBackPolicyTests` | 2 | NOT RUN — Xcode not installed (`xcodebuild` unavailable); zero tests executed |
| `make verify-static` | 2 | FAIL — blocked at `check-plan-strict` by unrelated uncommitted worktree changes; code checks before it PASS (arch R1–R6, baseline, docs, agents) |
| `make test-ui` | 2 | NOT RUN — same Xcode-unavailable blocker |

Consequence: the new policy unit tests and UI test have **not** been re-verified on this host during this review. The repository's recorded evidence (`task-2-red`/`task-2-green`, `20261119T052843Z-ui-tests-pass`) shows they passed previously, but that is delivery evidence, not an independent gate run here.

## Notes

- The gate runner observed unrelated uncommitted changes during the review (`Makefile`, `harness/config.json`, `tools/delivery_check.py`, untracked `harness/plans/2026-11-19-review-independence.md`, `tools/review_guard.py`, `tools/review_guard_fixtures.py`). I did not create or revert them; the reviewed code is committed at HEAD.
- No source files were edited and nothing was committed by this review.
