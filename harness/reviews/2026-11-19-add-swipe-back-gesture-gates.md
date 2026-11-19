# Gate Run — add-swipe-back-gesture
- Base: 13b8b4d8999a6dc0360461a3fc788e69f11609aa
- Head: 354aeeb0741513a42259d073a3fd041faae741d8
- Environment: macOS 27.0.1 (build 26A434), Darwin 27.0.0; Xcode NOT installed — `xcode-select -p` = `/Library/Developer/CommandLineTools`, `xcodebuild`/`simctl` unavailable (Command Line Tools only); intended simulator destination `platform=iOS Simulator,name=iPhone 17 Pro Max,OS=26.4.1`. Note: worktree had uncommitted, unrelated changes during the run (concurrent `review-independence` / `review-guard` work): `M Makefile`, `M harness/config.json`, `M tools/delivery_check.py`, plus untracked `harness/plans/2026-11-19-review-independence.md`, `tools/review_guard.py`, `tools/review_guard_fixtures.py`.
- Overall: PARTIAL

## Gate results
| # | Command | Exit | Result | Evidence / notes |
|---|---|---|---|---|
| 1 | python3 tools/check-test-baseline.py | 0 | PASS | unit 144/144 (17 files), UI 4/4 (2 files); verification.md counts consistent (144 unit + 4 UI, device 148); XCTSkip 1 == whitelist 1. |
| 2 | make test-one TEST=DuiyiTests/EdgeSwipeBackPolicyTests | 2 | NOT RUN | BLOCKED: `xcode-select: error: tool 'xcodebuild' requires Xcode...`. Test file exists at HEAD with 5 `@Test` cases. No tests executed. |
| 3 | make verify-static | 2 | FAIL | Fails at `check-plan-strict` (uncommitted worktree-hygiene violations from another in-flight plan), NOT code. All code checks before it PASS (check-arch R1–R6 0 violations, test baseline, docs). |
| 4 | make test-ui | 2 | NOT RUN | BLOCKED: same `xcode-select`/xcodebuild error. No tests executed. |

## Raw output (trimmed)

### Gate 1 — python3 tools/check-test-baseline.py (exit 0)
```
check-test-baseline · 测试基线下限
[OK] unit：@Test 144 ≥ floor 144（17 个文件）
[OK] ui：func test 4 ≥ floor 4（2 个文件）
[OK] references/verification.md 计数一致：144 单元 + 4 UI
[OK] references/verification.md 真机计数一致：148
[OK] XCTSkip：1 次 == 白名单 1
[PASS] 测试基线通过（只增不减 + 文档计数 + skip 白名单）
```
Documented-count cross-check: `references/verification.md` states "144 单元 + 4 UI", device 148; `harness/test-baseline.json` has `unit.floor=144` (17 files), `ui.floor=4` (2 files), `device.floor=148`, `xctSkipOccurrences=1`, `expectedSkipped.simulator=1`. Consistent.

### Gate 2 — make test-one TEST=DuiyiTests/EdgeSwipeBackPolicyTests (exit 2)
```
xcodebuild test -project Duiyi.xcodeproj -scheme Duiyi -destination 'platform=iOS Simulator,name=iPhone 17 Pro Max,OS=26.4.1' -derivedDataPath /tmp/duiyi-build -only-testing:DuiyiTests/EdgeSwipeBackPolicyTests
xcode-select: error: tool 'xcodebuild' requires Xcode, but active developer directory '/Library/Developer/CommandLineTools' is a command line tools instance
make: *** [test-one] Error 1
```
No "Test Suite"/"Executed" summary was produced — zero tests ran. `DuiyiTests/EdgeSwipeBackPolicyTests.swift` is present at HEAD (5 `@Test`).

### Gate 3 — make verify-static (exit 2)
```
python3 tools/check-arch.py
check-arch · 架构铁律 R1–R6（扫描 82 个 Swift 文件，0.05s）
[PASS] R1–R6 全部通过：0 违规
python3 tools/check-test-baseline.py
[PASS] 测试基线通过（只增不减 + 文档计数 + skip 白名单）
[OK] check_docs 通过（扫描 67 篇文档）
[OK] check_agents 通过（7 个指令文件）
...
结论：PASS（2 个计划，0 error / 51 warn）        # check-plan --lenient-uncommitted
[OK] scorecard 新鲜：harness/reviews/2026-11-19-scorecard.md（0 天前，之后 4 个提交）
python3 tools/check_plan.py check --strict
检查 harness/plans/*.md（跳过 _template.md）：
[FAIL]  harness/plans/2026-11-19-review-independence.md  status=active
       [FAIL] 计划声明未提交但 git 无改动：无（基线后按批次声明/提交）
       [FAIL] git 有未提交改动但计划未声明：harness/config.json
       [FAIL] git 有未提交改动但计划未声明：harness/plans/2026-11-19-review-independence.md
       [FAIL] git 有未提交改动但计划未声明：tools/delivery_check.py
       [FAIL] git 有未提交改动但计划未声明：tools/review_guard.py
       [FAIL] git 有未提交改动但计划未声明：tools/review_guard_fixtures.py
       [WARN] 验证证据表中没有可解析且 verdict=PASS 的 evidence id（完成前补一条真实证据）
...
结论：FAIL（2 个计划，6 error / 46 warn）
make: *** [check-plan-strict] Error 1
```
First concrete failure: `[FAIL] harness/plans/2026-11-19-review-independence.md status=active` → undeclared uncommitted changes. This is worktree hygiene from a different, concurrently in-progress task; it is not caused by the swipe-back diff (all reviewed files are committed at HEAD). Gate stops before `check-evidence`, `check-host`, `evidence-chain-check`, `kit-check`, and `bash -n` syntax checks, so those were not exercised.

### Gate 4 — make test-ui (exit 2)
```
xcodebuild test -project Duiyi.xcodeproj -scheme Duiyi -destination 'platform=iOS Simulator,name=iPhone 17 Pro Max,OS=26.4.1' -derivedDataPath /tmp/duiyi-build -only-testing:DuiyiUITests
xcode-select: error: tool 'xcodebuild' requires Xcode, but active developer directory '/Library/Developer/CommandLineTools' is a command line tools instance
make: *** [test-ui] Error 1
```
No UI tests executed. Reported as NOT RUN (environment-blocked), not a pass.
