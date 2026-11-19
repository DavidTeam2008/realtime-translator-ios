# Standards Review — add-swipe-back-gesture
- Base: 13b8b4d8999a6dc0360461a3fc788e69f11609aa
- Head: 354aeeb0741513a42259d073a3fd041faae741d8
- Axis: standards
- Scope: Duiyi/, DuiyiTests/, DuiyiUITests/
- Verdict: PASS WITH FINDINGS

## Findings

### [P2] Swipe-back UI test can pass without the gesture succeeding
- Location: DuiyiUITests/SimultaneousFlowTests.swift:94
- Standard: Test-robustness risk (DuiyiUITests/AGENTS.md §3 requires identifier-based assertion; no rule against strengthening)
- Evidence: `XCTAssertTrue(app.buttons["home-module-simultaneous"].waitForExistence(timeout: timeout), "edge swipe did not return to home")`
- Why: `NavigationStack` can keep the root view in the accessibility hierarchy behind the pushed page; `waitForExistence` alone may already be true before the swipe, producing a false green. It also does not prove the module page was dismissed.
- Fix: assert the pushed page disappears (`nav-home` no longer exists) or that the home button is `isHittable`, e.g. wait on `NSPredicate(format: "exists == false")` for `nav-home`.

### [P2] Coordinate-based gesture synthesis vs. "no coordinate positioning"
- Location: DuiyiUITests/SimultaneousFlowTests.swift:90-92
- Standard: DuiyiUITests/AGENTS.md §3 — "只用 accessibilityIdentifier…不用中文文案或坐标定位"
- Evidence: `app.coordinate(withNormalizedOffset: CGVector(dx: 0.01, dy: 0.5))` … `start.press(forDuration: 0.05, thenDragTo: end)`
- Why: literal tension with the standard. Element lookup still uses identifiers, and an edge-origin gesture cannot be expressed through any identifier, so this is a judgement call rather than an element-lookup breach. The fractions still encode layout and can silently stop matching the policy after layout changes.
- Fix: keep, but extract a named helper (e.g. `swipeBackFromLeadingEdge(in: app)`) with a comment stating why coordinates are unavoidable, and derive the x fraction from a documented edge assumption.

### [P2] `maximumVerticalDrift` guard is not isolated by any test
- Location: Duiyi/Features/Shared/EdgeSwipeBackPolicy.swift:18 (tests at DuiyiTests/EdgeSwipeBackPolicyTests.swift:57-69)
- Standard: Smell baseline: none — coverage gap against DuiyiTests/AGENTS.md §1 (one behavior per case, inputs → expected)
- Evidence: `guard abs(translation.height) <= maximumVerticalDrift else { return false }`; both rejection cases (`60x79`, `120x120`) already fail the earlier `abs(height) < width` guard, so line 18 is never exercised alone.
- Why: a regression in the drift cap (or its removal) would not turn any test red.
- Fix: add a case where horizontal dominance holds but drift exceeds 80 (e.g. `width: 120, height: 90` → reject) and a boundary accept (`120x80`).

### [P2] Unnecessary `@MainActor` on a pure-logic test suite
- Location: DuiyiTests/EdgeSwipeBackPolicyTests.swift:5
- Standard: DuiyiTests/AGENTS.md §1 — `@MainActor` is for VM/Store tests; repo pure-policy suites (`AudioSessionPolicyTests`, `LanguageRouterTests`, `SpokenTextTests`) are not annotated
- Evidence: `@MainActor` immediately above `struct EdgeSwipeBackPolicyTests`
- Why: inconsistent with the established convention; adds isolation with no requirement.
- Fix: remove `@MainActor`.

### [P2] Duplicated shouldPop invocation shape across test cases
- Location: DuiyiTests/EdgeSwipeBackPolicyTests.swift:11-66
- Standard: Smell baseline: Duplicated Code
- Evidence: the same `EdgeSwipeBackPolicy.shouldPop(hasPreviousPage: true, startLocation: CGPoint(x: 12, y: startY), translation: …)` shape repeats six times.
- Why: noise obscures which input each case varies.
- Fix: add a private helper such as `shouldPop(startX: 12, translation: CGSize(...), hasPreviousPage: true)` and keep one explicit call for the root case.

### [P2] Root `simultaneousGesture` may coexist with the system interactive pop
- Location: Duiyi/App/RootView.swift:22-34
- Standard: Robustness risk (not a documented-standard breach)
- Evidence: `.simultaneousGesture(DragGesture(minimumDistance: 10, coordinateSpace: .local) … coordinator.pop())`
- Why: the design relies on the hidden navigation bar disabling the native pop gesture. If an OS version keeps it enabled, one edge swipe could pop twice on a depth-2 stack (history → task detail). The new UI test only exercises depth 1, where a second pop is a no-op.
- Fix: verify on device that a depth-2 stack pops exactly one level; add a UI case for task detail if the behavior is not guaranteed.

## Notes
- Checked and cleared: dependency rules (new file imports only `CoreGraphics`; no SwiftUI/Speech/AVFoundation/SwiftData in Features); translation/audio/persistence contracts not touched; no new UI entry, so no new accessibility identifier was required.
- Test conventions: Swift Testing with English `@Test` sentences and `#expect`; XCTest UI suite uses `XCTestCase`, inherited `continueAfterFailure = false`, and `-duiyi.onboardingComplete YES`.
- Test baseline synchronized: `harness/test-baseline.json` unit 139→144 (+5 `@Test`), UI 3→4, device 142→148; `references/verification.md` updated in the same change. Existing assertions untouched (contracts §6).
- RootView stays thin; thresholds live in the shared policy rather than duplicated layout constants.
- Not applicable: startup/performance (gesture callback is off the launch path); speech/translation/TTS verification matrix.
- `make check`/`make test` were not run by this reviewer; evidence artifacts exist under `harness/evidence/`.
