---
id: 2026-11-18-cache-language-capabilities
status: done
level: L2
owner: david
updated: 2026-11-18
submitted: ae409a6
tasksSource: openspec
change: cache-language-capabilities
base: 1961368
tasks: openspec/changes/archive/2026-11-18-cache-language-capabilities/tasks.md
scope:
  allow:
    - openspec/changes/cache-language-capabilities/
    - harness/records/2026-11-18-cache-language-capabilities.md
    - Duiyi/Domain/LanguageCatalog.swift
    - Duiyi/Services/
    - Duiyi/App/AppEnvironment.swift
    - Duiyi/Features/Shared/LanguageChipGrid.swift
    - Duiyi/Features/Home/HomeSettingsSheet.swift
    - DuiyiTests/
    - references/verification.md
    - harness/test-baseline.json
    - harness/reviews/2026-11-18-cache-language-capabilities.md
  deny:
    - Duiyi.xcodeproj/
    - Duiyi/Features/Speech/
    - Duiyi/Features/Translation/
    - .env
    - "*.p12"
    - "*.mobileprovision"
acceptance:
  - 以 tasks.md Delivery Contract 与 `make delivery-check CHANGE=cache-language-capabilities` 结果为准
verify:
  - tools/openspec validate cache-language-capabilities --type change --strict --json
  - make delivery-check CHANGE=cache-language-capabilities
  - make release-check
---

# cache-language-capabilities · Change Record

> 任务状态唯一来源：`openspec/changes/cache-language-capabilities/tasks.md`；本记录只保存指针与交付事实。

## 目标与非目标

- 目标：语言目录改为缓存型系统实查，并让选择网格禁用目录报告的不可用语言。
- 非目标：不下载语言资产，不改语音/翻译引擎，不改持久化。

## 验收

- [ ] 以 `tasks.md` Delivery Contract 和 `delivery-check` 结果为准；本记录不复制任务状态。

## 改动范围

- 允许：见 front matter `scope.allow`。
- 禁止：见 front matter `scope.deny` 与 Delivery Contract。

## 进度

- 指针：任务勾选与 `complete/total` 只从 `tasks` 读取；本记录不维护独立进度。

## 验证证据

| 命令 | 结果 | 环境 | 证据ID |
| --- | --- | --- | --- |
| `XCODEBUILD_BUILD_ARGS='OTHER_SWIFT_FLAGS=-disable-sandbox CODE_SIGNING_ALLOWED=NO' make evidence-unit WRITE=1` | PASS：139/139、0 skip | 本机模拟器 | `20261118T071150Z-unit-tests-pass` |
| 同上 `make evidence-ui WRITE=1` | PASS：2 passed + 1 expected skip | 本机模拟器 | `20261118T071256Z-ui-tests-pass` |
| `make delivery-check CHANGE=cache-language-capabilities` | PASS：4/4 tasks、fresh/strict evidence、review Base..Head | 本机；OpenSpec 2.1.0；toolchain v0.2.0 | —（过程记录） |

## 未验证项

- 真机语言能力实查：单元测试只覆盖注入边界，不能证明设备实际可用资产。

## 未验证豁免

| 项目 | 理由 | 负责人 | 到期日 |
| --- | --- | --- | --- |
| 真机语言能力实查 | 需要设备下载/安装资产；注入边界测试只证明映射与缓存语义 | david | 2026-12-31 |

## 未提交改动

- 无未提交改动。

## 下一步

1. 按 `tasks.md` Task 1 先写红测试；不使用 stock executing-plans/SDD ledger。
