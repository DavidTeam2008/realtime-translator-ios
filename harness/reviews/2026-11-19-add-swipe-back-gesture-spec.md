# Spec Review — add-swipe-back-gesture
- Base: 13b8b4d8999a6dc0360461a3fc788e69f11609aa
- Head: 354aeeb0741513a42259d073a3fd041faae741d8
- Axis: spec
- Scope: Duiyi/, DuiyiTests/, DuiyiUITests/
- Spec: openspec/changes/archive/2026-11-19-add-swipe-back-gesture/{proposal.md,design.md,specs/navigation/spec.md,tasks.md}
- Verdict: PASS WITH FINDINGS

## Findings

### [P1] Home edge-swipe "no navigation" is not UI-verified (missing)
- Location: DuiyiUITests/SimultaneousFlowTests.swift:83-98
- Spec line: design.md:27 "**UI 测试**：模块页左边缘右滑后回到首页；首页边缘右滑不产生导航；现有 `nav-home` 路径仍可用。"
- Evidence: The only new UI test is `testSwipeBackFromModule`; it launches, opens `home-module-faceToFace`, swipes, and asserts return. No test ever swipes on the home page. tasks.md:39 nevertheless claims the new test "Covers: R1/S1.1/S1.2/R2/S2.1/S2.2/R3/S3.1/A2".
- Why: S2.1 and design's verification obligation ("首页边缘右滑不产生导航") have no UI-level evidence; the claim in tasks.md is overstated. A regression that lets the root swipe pop/navigate would not be caught.
- Fix: Add a UI test that on the home page performs the same leading-edge right swipe and asserts `home-module-faceToFace` remains hittable / no pushed page appears.

### [P1] History-page swipe-back (S1.2) is implemented but unverified (partial)
- Location: DuiyiUITests/SimultaneousFlowTests.swift:82-120
- Spec line: spec.md:20-24 "#### Scenario: 历史页右滑返回首页 ... **THEN** 应用返回首页"; tasks.md:39 "Covers: R1/S1.1/S1.2/..."
- Evidence: `testSwipeBackFromModule` only enters the face-to-face module. `assertHomeModuleNavigation` exercises history only via the `nav-home` button, never an edge swipe. The root `.simultaneousGesture` (Duiyi/App/RootView.swift:22) is generic, so history and task-detail likely work, but no UI test proves it and the task claim is false for S1.2/task-detail.
- Why: R1 explicitly names 模块、历史、任务详情; an important scenario has zero UI coverage despite being claimed.
- Fix: Add a UI test entering `home-history`, performing the leading-edge swipe, and asserting return to home; optionally cover `taskDetail` (history → row → swipe → back to history).

### [P2] Swipe-back UI assertion can false-pass (partial)
- Location: DuiyiUITests/SimultaneousFlowTests.swift:94-97
- Spec line: tasks.md:37-38 "UI test fails first, then the root gesture returns to home."
- Evidence: The postcondition is `app.buttons["home-module-simultaneous"].waitForExistence(...)`. It does not assert the pushed `nav-home` chrome disappeared or that the home element is hittable. If SwiftUI keeps the root view in the accessibility tree while a destination is pushed, this assertion passes without any pop.
- Why: Weak red/green signal; the test may not actually prove the gesture caused navigation.
- Fix: Assert `nav-home` is gone (e.g. `waitForNonExistence`) and/or that `home-module-faceToFace` is hittable after the swipe.

### [P2] S1.1/S3.1 task-state clauses are unverified (partial)
- Location: DuiyiUITests/SimultaneousFlowTests.swift:83-98
- Spec line: spec.md:16 "**AND** 已有任务保持进行中，不被结束"; spec.md:61 "**AND** 听写停止且任务保持进行中"
- Evidence: Neither the new test nor `assertHomeModuleNavigation` starts dictation or a task; the implementation only calls `coordinator.pop()` (RootView.swift:29-32), relying on existing `onDisappear` stop semantics. Design.md:29 assigns this to 人工复核.
- Why: The clauses are spec requirements; verification is manual-only and not recorded in the automated suite. Behavior is preserved by not touching task code, so risk is low.
- Fix: Either add/extend a device UI test that starts listening, swipes back, and confirms listening stopped + task still in progress, or explicitly record the manual observation in evidence.

## Coverage matrix
| Requirement / Scenario | Implemented? | Verified by test? | Finding |
|---|---|---|---|
| R1 any pushed page (module/history/task-detail) | Yes (generic root gesture) | Partial — module only | P1 (history/task-detail unverified) |
| R2 non-empty path + thresholds only | Yes | Unit + new UI (module) | P1 (home no-nav UI missing) |
| R3 existing 首页/历史/结束/新任务 entries | Yes (untouched) | Partial — nav-home module+history | P2 (end/new-task not asserted) |
| S1.1 module swipe → home | Yes | Yes (`testSwipeBackFromModule`) | P2 (task-not-ended unverified) |
| S1.2 history swipe → home | Yes (generic) | No | P1 |
| S2.1 home edge swipe → unchanged | Yes (`rejectsAtRoot`) | Unit only; no UI | P1 (design requires UI) |
| S2.2 mid-screen/short/vertical → unchanged | Yes (thresholds match design) | Yes (3 unit cases) | — |
| S3.1 nav-home → home, dictation stops, task ongoing | Yes (untouched) | Partial — nav-home yes; dictation/task no | P2 |
| A1 policy accepts eligible swipes only | Yes | Yes (5 unit tests) | — |
| A2 module swipe + existing nav works | Yes | Yes (new + existing UI tests) | — |
| A3 baseline 144 unit + 4 UI, device 148, no assertion changes | Out of code scope (counts verified: 144/4/148; diff additive) | n/a | — |

## Notes
- Thresholds in EdgeSwipeBackPolicy.swift:5-7 exactly match design.md:9-11 (edge 24, horizontal ≥60, vertical < horizontal and ≤80). Gesture mount (`.simultaneousGesture` on NavigationStack), pop call, and animation duration all match design.md:12-13.
- `.simultaneousGesture` + policy gating means non-matching drags are not consumed; no interference with `ListeningControl`'s drag or history row `swipeActions` found.
- No scope creep in Duiyi*/tests: diff is 122 additive lines across 4 files.
- Unit tests do not exercise exact boundary values (x=24, width=60, drift=80), only clearly-inside/outside points; minor.
