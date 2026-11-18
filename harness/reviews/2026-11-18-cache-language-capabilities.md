---
base: 1961368
head: f3e2bdabcf32c0a01b071b8b2e406e3f01face17
reviewer: david
p0: closed
p1: closed
p2: closed
verdict: pass
---

# Review: cache-language-capabilities

## Scope

Base `1961368` 到 Head `ae409a6` 的增量限定在语言目录契约、`SystemLanguageCatalog`、注入边界测试、`LanguageChipGrid`/Home 设置接线、Change Record、测试基线与 verification 计数。未命中 Delivery Contract deny。

## Findings

### P0

无阻断项。实现没有把系统探测放在 `capability(_:)` 同步路径；`refreshCapabilities()` 显式触发，重复刷新不会重新探测。

### P1

无阻断项。注入边界测试覆盖缓存、映射、同语言拒绝和禁用语言派生；测试 fake 只替代系统边界，不冒充真机能力结论。

### P2

- 真机系统语言能力已于 2026-11-18 由用户完成人工验收；原“设备资产下载/安装后人工确认”事项关闭。
- 当前只有 Home settings sheet 接入目录派生禁用态；其他入口可在后续 Change 批量接线。

## Verification

- 聚焦 `DuiyiTests/SystemLanguageCatalogTests` 8 个用例通过。
- 完整模拟器单元证据 `20261118T071150Z-unit-tests-pass`：139/139，0 skip。
- 模拟器 UI 证据 `20261118T071256Z-ui-tests-pass`：2 passed + 1 expected skip。
- `verify_claim_chain --all --fresh --strict`：3 PASS / 0 FAIL / 0 UNVERIFIED。
- 真机系统语言能力人工验收：2026-11-18 由用户确认通过。

## Conclusion

P0/P1/P2 已关闭。注入边界与缓存语义可交付；真机语言能力以用户 2026-11-18 人工验收为准。
