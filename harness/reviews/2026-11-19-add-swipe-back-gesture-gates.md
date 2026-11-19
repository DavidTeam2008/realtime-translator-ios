# Gate Run — add-swipe-back-gesture

- Base: 13b8b4d8999a6dc0360461a3fc788e69f11609aa
- Head: 9f622266f58ce4d87dcc4d0076cd191fc50b320a
- Gate runner: gate-runner-lead（独立于 reviewer 的另一个进程）
- Environment: macOS / Xcode 27.1 / iPhone 17 Pro Max iOS 26.4.1
- Overall: PASS

| command | exit | result |
| --- | --- | --- |
| python3 tools/check-test-baseline.py | 0 | PASS |
| make test-one TEST=DuiyiTests/EdgeSwipeBackPolicyTests | 0 | PASS |
| make test-one TEST=DuiyiUITests/SimultaneousFlowTests/testSwipeBackFromModule | 0 | PASS |
| make test-one TEST=DuiyiUITests/SimultaneousFlowTests/testHomeEdgeSwipeDoesNotNavigate | 0 | PASS |
| make test-one TEST=DuiyiUITests/SimultaneousFlowTests/testHistorySwipeBack | 0 | PASS |
| make verify-static | 0 | PASS |
| make evidence-unit WRITE=1 | 0 | PASS：144 passed / 0 failed / 0 skipped |
| make evidence-ui WRITE=1 | 0 | PASS：5 passed / 0 failed / 1 skipped（6 tests） |
| make review-guard-fixtures | 0 | PASS：dual-context 正例 + 5 负例 |

- Gate 1 计数：144 单元 + 6 UI；真机 150；skip 白名单 1。
- 证据：unit `20261119T115317Z-unit-tests-pass`；UI `20261119T115531Z-ui-tests-pass`。
- 说明：gate-runner 与 reviewer 是不同进程；本报告记录命令/退出码，不替代 review 结论。
