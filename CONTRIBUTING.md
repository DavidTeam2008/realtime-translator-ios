# Contributing · 对译 Duiyi

> 先读 [`README.md`](README.md)；AI Agent 协作者先读 [`AGENTS.md`](AGENTS.md)。
> 本文是本地开发、验证与提交的唯一入口；产品行为见 [`docs/01`](docs/01-product-design.md)，架构见 [`docs/02`](docs/02-architecture.md)。

## 1. 环境

| 用途 | 需要 |
| --- | --- |
| 静态门禁 / 文档 / 计划 / 证据校验 | macOS 或 Linux + `python3`（标准库）+ `make` + `git` |
| 构建与模拟器测试 | macOS + Xcode 26.4+（当前验证 27.1）+ iOS 26.4 Simulator |
| 真机测试（语音/翻译/持久化） | iPhone（iOS 26.4+）、开发者模式、信任此 Mac |
| 真机测试脚本 | `npm i -g mobilebuildmcp`；启动测量另需 `idevicesyslog`、`timeout` |

无第三方依赖，不需要 `pod install` / SPM 解析。

## 2. 10 分钟验证（不需要 Xcode）

```bash
git clone <repo-url> && cd realtimeTranslatorOptimize
make check          # 文档/架构/计数/harness/计划，约 0.3s
make verify-static  # 再加证据 schema、脚本单测、语法检查，约 4.3s
```

任何失败先修门禁再提交；不要为变绿删检查、改断言或放宽 skip。

## 3. 完整 iOS 环境

1. 用 Xcode 打开 `Duiyi.xcodeproj`；
2. **签名**：App、`DuiyiTests`、`DuiyiUITests` 三个 target 设置自己的 Team 和全局唯一 Bundle ID。工程里的 `com.david.Duiyi` 只是示例；不要把别人的 Team 提交回仓库。机器本地信息写 `AGENTS.local.md`（模板见 [`AGENTS.local.md.example`](AGENTS.local.md.example)）；
3. 真机开启开发者模式并信任此 Mac；
4. 首次启动按引导选语言、允许麦克风/语音识别、下载端侧资源。

```bash
make build                  # 模拟器构建
make test                   # 模拟器单元测试
make test-ui                # 模拟器 UI 测试（语音用例按预期 skip）
APM_DEVICE=<CoreDevice ID> .apm/tools/device-test.sh   # 真机完整套件（先预热 testmanagerd）
```

设备 CoreDevice ID 用 `xcrun devicectl list devices` 或 `mobilebuildmcp device list` 查（本机值可写 `AGENTS.local.md`）；真机预热、`exit 74`、`Enable UI Automation` 密码弹窗等坑见 [`references/verification.md`](references/verification.md)。

## 4. 改完怎么验证

按变更类型选最低验证（完整矩阵见 [`references/verification.md`](references/verification.md)）：

| 变更 | 最低验证 |
| --- | --- |
| Domain / ViewModel 逻辑 | `make test` |
| UI 导航 / 布局 | `make test-ui` + 手工走主路径 |
| 语音 / 翻译 / TTS / 音频 / 持久化 | 真机（`device-test.sh`），模拟器不能替代 |
| 文档 / 规则 / 工具 | `make verify-static` |

完成声明必须附：命令、退出码、环境、证据 ID（`.apm/evidence/`）。未运行就写“未验证”，不能把“环境跑不了”写成“代码通过”。

## 5. Agent 协作

- 冷启动：`AGENTS.md`；动作卡：`.dsh/skills/`；
- 跨会话任务：active 计划（`.apm/plans/`），用 `make resume` / `make end` / `make handoff`；
- 证据：`make evidence` 查看，`make verify-claim` 做 PASS / FAIL / UNVERIFIED 三值判定；
- 变更分级见 [`references/workflow.md`](references/workflow.md)（L0 / L1 / L2），L2 先方案后执行。

## 6. 提交与 PR

- 提交前跑 `make verify-static`；`make hooks-install` 装上 pre-push 钩子；
- 一次提交只做一件事；提交信息用英文，跟随仓库近 5 条非 merge commit；不加 AI 署名；
- 不提交：`build/`、xcuserdata、`.apm/runs/`、日志、签名/设备信息、本机绝对路径；
- PR 请写清：变更、验证命令与结果、未验证项。

## 7. 已知限制

- 模拟器不提供 `SpeechTranscriber`，语音链路必须在真机验收；不得 mock 能力检查来“修绿”；
- 启动优化已暂停：200ms 目标经对照实验判定不可达（[`docs/17`](docs/17-startup-optimization-paused.md)、[`docs/18`](docs/18-startup-feasibility-verification.md)）；
- 免费开发者账号有自签名 App 数量上限（UI Test Runner 也占一个名额）。

## 8. 安全与隐私

- 不提交密钥/Token/凭证，不提交他人 Team ID / Bundle ID / 设备 ID；
- 产品默认不保存音频、不上传；总结优先 Apple 智能，设备不支持时本地回退。
