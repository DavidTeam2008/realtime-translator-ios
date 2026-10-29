# 对译 Duiyi

多语言现场沟通 App：**面对面**、**同声传译**、**会议记录**。听写、翻译、
总结都在设备端完成（首次需联网下载系统语音/翻译资源），任务保存在本机，
不依赖后端、不上传音频。

- Xcode 工程：[`Duiyi.xcodeproj`](Duiyi.xcodeproj)
- 最低系统：**iOS 26.4**，仅 iPhone、竖屏
- 语言：中 / 英 / 日 / 韩 / 泰 / 越
- 真机优先：iOS 模拟器不提供 `SpeechTranscriber`，无法验证真实听写链路

> **接手项目请先读 [`HANDOFF.md`](HANDOFF.md)。**
> 里面有签名/构建、真机测试、已知坑、架构速览和下一步优先级。
> 文档索引见 [`docs/README.md`](docs/README.md)。

## 功能模块

- **面对面**：手机平放，上半屏倒字给对方，下半屏正字给自己；双向听写 + 双向翻译。
- **同声传译**：单栏看现场译文，可选戴耳机读出译文；单向听写 + 单向翻译。
- **会议记录**：单语全文稿，会后总结或导出；不做实时翻译。
- **任务历史**：只有点“结束任务”才写入本机，可回看、总结、导出分享。

## 快速开始

```bash
open Duiyi.xcodeproj
```

1. 在 **Signing & Capabilities** 里把 App / `DuiyiTests` / `DuiyiUITests`
   三个 target 改成你自己的 Team 和唯一 Bundle ID（工程当前写的是原开发者的
   `REDACTED_TEAM_ID` / `com.david.Duiyi`）。
2. 选一台 iOS 26.4+ 真机运行。
3. 首次启动按引导选语言、允许麦克风/语音识别、下载端侧资源。
4. 首页选模块 → **新任务** → 中间按钮开始听 → **结束任务** 写入历史。

命令行构建 / 安装：

```bash
xcrun devicectl list devices

xcodebuild -project Duiyi.xcodeproj -scheme Duiyi \
  -destination 'platform=iOS,id=<UDID>' \
  -allowProvisioningUpdates \
  -derivedDataPath /tmp/duiyi-build build

xcrun devicectl device install app --device <UDID> \
  /tmp/duiyi-build/Build/Products/Debug-iphoneos/Duiyi.app
xcrun devicectl device process launch --device <UDID> com.david.Duiyi
```

## 测试

```bash
# 单元测试（120 个，Swift Testing；模拟器即可）
xcodebuild test -project Duiyi.xcodeproj -scheme Duiyi \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro Max' \
  -only-testing:DuiyiTests

# 真机完整套件（120 单元 + 3 UI，自动预热 testmanagerd）
.apm/tools/device-test.sh
```

真机 UI 测试必须先预热 `testmanagerd`，否则会以 `exit 74` /
`Timed out while enabling automation mode` 失败。`.apm/tools/device-test.sh`
已固化这个顺序；说明见 [`docs/20`](docs/20-ui-test-hittable-fix.md)。

## 项目结构

```text
Duiyi/
  App/            入口、依赖注入、导航、首页模块注册
  Features/       Home / Conversation / Interpretation / Meeting / History / Onboarding / Shared
  Domain/         纯模型与纯函数（任务、语言、字幕、切句、路由）
  Services/       语音、音频、翻译、TTS、持久化、总结、导出、权限、资源
  DesignSystem/   Tokens、卡片、列表行、安全区
DuiyiTests/       120 个单元测试（Swift Testing）
DuiyiUITests/     启动性能 + 导航 + 同传监听 UI 测试
.apm/             性能基准、问题单、测量/真机测试脚本（runs 不入库）
Order/            Release 二进制重排符号表（生成物）
tools/            order file 生成脚本
docs/             设计文档、架构分析、真机测试与问题闭环记录
prototype/        可交互 HTML 原型
```

## 文档

| 文档 | 内容 |
| --- | --- |
| [`HANDOFF.md`](HANDOFF.md) | **接手入口**：环境、构建、测试、坑、架构、下一步 |
| [`docs/README.md`](docs/README.md) | 全部文档索引与阅读顺序 |
| [`docs/13-architecture-analysis.md`](docs/13-architecture-analysis.md) | 架构深挖、数据链路、问题清单（最值得先读） |
| [`docs/14-device-test-iphone13.md`](docs/14-device-test-iphone13.md) | iPhone 13 真机性能与同传测试报告 |
| [`docs/19-ended-translation-persistence-fix.md`](docs/19-ended-translation-persistence-fix.md) | 已结束任务译文持久化修复 |
| [`docs/20-ui-test-hittable-fix.md`](docs/20-ui-test-hittable-fix.md) | UI 测试假绿/权限/模拟器能力问题闭环 |
| [`docs/15`](docs/15-startup-optimization.md)–[`docs/18`](docs/18-startup-feasibility-verification.md) | 启动优化过程与结论（**已暂停，不要重启微优化**） |
| [`docs/01`](docs/01-product-prototype.md)–[`docs/12`](docs/12-platform-roadmap.md) | 产品/架构/路线图设计历史 |

## 当前状态

- 三个模块、任务历史、总结、导出、6 语种、引导流程均已落地。
- 真机测试：**123 passed, 0 failed, 0 skipped**（iPhone 13 / iOS 26.7）。
- 冷启动约 **0.32s**（XCTest 口径）；20s 同传监听内存峰值 **10–13MB**，无 Hang。
- 启动 200ms 目标经对照实验判定**不可达**（空壳 App 地板约 210ms），已暂停。
- 主要技术债：语音引擎全局仲裁、长会话数据留存、SwiftData 写放大、
  翻译队列积压、导出竞态。详见 [`HANDOFF.md`](HANDOFF.md) §5。

## 隐私

默认不保存音频；文本只在 settled / 暂停 / 结束时写入本机；无后台音频模式；
无自建网络服务、无第三方 SDK、无 API Key。总结优先用 Apple 智能，设备不支持时
回退到本地摘要并如实提示。
