---
name: device-verify
description: 对译 Duiyi 真机验收入口：用 harness/tools/device-test.sh（强制先预热再单元/UI）跑真机，处理 exit 2（锁屏/未连接）、exit 74 与 automation 超时、Enable UI Automation 密码弹窗；成功后写 harness/evidence/ 并回填计划，无法操作设备时写"未验证 + 手动步骤"。
whenToUse: 语音/翻译/TTS/音频/SwiftData 留存等必须真机验证的改动；UI 真机验收；模拟器结果不足以判定时。
---

# device-verify · 真机验收

模拟器不能替代真机。不能实际操作设备时，结论只有一个：未验证。

## 入口（唯一推荐）

- `make device-test`：预热 + 单元 + UI（全套）。
- `make device-test-ui`：预热 + UI。
- `make device-test-one TEST=DuiyiUITests/...`：预热 + 单用例。
- 换设备：`APM_DEVICE=<CoreDevice ID> make device-test`；本机 ID 只写 `AGENTS.local.md`，不入库。
- 不要直接敲 xcodebuild 跑 UI：预热是脚本的强制步骤，跳过会复现 exit 74。

## 前置

- 设备已连接并信任本机、已解锁、Developer Mode 开启。
- `mobilebuildmcp` 在 PATH（`make doctor` 会提示）。
- 免费证书安装的 App 未超上限（10 个）。
- iOS 15+ 首次 UI 测试需在设备上输入一次锁屏密码（Enable UI Automation 弹窗）。
- 设备 OS 比 Xcode SDK 新时可能缺 DeviceSupport：用 USB 连接 + 保持解锁让 Xcode 准备。

## 失败处理（按证据强度）

- exit 2：设备锁屏 / 连不上 / 缺 mobilebuildmcp / 模式用法错 → 先修环境，不重跑全套。
- exit 74 或 "Timed out while enabling automation mode"：确认预热已跑；仍失败检查手机密码弹窗；再失败换 USB + 解锁重试。
- 预热失败：先修环境（解锁、信任、Developer Mode、证书数量），不要继续跑 UI。
- 同一环境失败最多重试 1 次；仍失败写"未验证"+ 手动步骤，不反复跑。
- 失败先定位；不要为变绿改测试断言或放宽 skip（模拟器语音 skip 是预期）。

## 成功后的证据

1. 确认计数符合预期（真机 skip 应为 0；基线数字只在 `references/verification.md`，此处不复制）。
2. Phase 1 起真机脚本自动写 `harness/evidence/`；若未自动写，用 `python3 tools/evidence.py write ...` 生成（`make evidence` 只列出），记录命令 / 设备 / 计数 / 耗时。
3. `make verify-claim` 确证 PASS；把 evidence id + 环境回填计划"验证证据"表并更新"未验证项"。
4. 只有拿到证据后，才允许在交付里写"真机已验证"。

## 不能操作设备时

在交付与计划里写：未验证（无设备访问）+ 手动步骤。示例：
`make doctor && make device-test`，在真机解锁后执行；异常按上方失败处理。
