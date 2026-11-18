---
base: 1961368
head: f3e2bdabcf32c0a01b071b8b2e406e3f01face17
reviewer: david
p0: closed
p1: closed
p2: scheduled
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

- 真机系统语言能力未验证；需要设备实际下载/安装语言资产后人工确认。已列入 Change Record 未验证项，负责人 david，到期 2026-12-31。
- 当前只有 Home settings sheet 接入目录派生禁用态；其他入口可在后续 Change 批量接线。

## Verification

- 聚焦 `DuiyiTests/SystemLanguageCatalogTests` 8 个用例通过。
- 完整模拟器单元证据 `20261118T071150Z-unit-tests-pass`：139/139，0 skip。
- 模拟器 UI 证据 `20261118T071256Z-ui-tests-pass`：2 passed + 1 expected skip。
- `verify_claim_chain --all --fresh --strict`：3 PASS / 0 FAIL / 0 UNVERIFIED。

## Conclusion

P0/P1 已关闭，P2 有负责人与到期日。在“注入边界与缓存语义”范围内可交付；不得据此声称真机语言能力已验证。
