# 对译 Duiyi

多语言现场沟通平台：面对面、同声传译、会议记录。任务保存在本机，能用 Apple 智能就总结，不能用就导出分享。

Xcode 工程：[`Duiyi.xcodeproj`](Duiyi.xcodeproj)  
最低系统：iOS 26.4，真机优先（语音与翻译模型在模拟器上不完整）

## 打开工程

```bash
open Duiyi.xcodeproj
```

首次运行会引导：选语言 → 麦克风 / 语音识别 → 下载模型。之后先到**首页**选模块：

- **面对面**：手机平放，上半屏倒字给对方，下半屏正字给用户
- **同声传译**：单栏正字听现场；可选戴耳机读出译文
- **会议记录**：单语全文稿，会后总结或导出
- **任务历史**：本机记录，可回看、总结、导出分享

每个模块：先点**新任务**，再点中间钮开始听。**结束任务**才写入历史。暂停只停麦克风。

iPhone 13 等不能使用 Apple 智能的设备会直接说明，并仍可导出 UTF-8 文字稿到系统分享。

## 设计文档

平台（模块、任务、历史、总结、会议记录）：

| 文档 | 内容 |
| --- | --- |
| [docs/09-platform-prototype.md](docs/09-platform-prototype.md) | 平台产品原型 |
| [docs/10-platform-architecture.md](docs/10-platform-architecture.md) | 平台架构 |
| [docs/11-platform-tech-choices.md](docs/11-platform-tech-choices.md) | 平台技术选型 |
| [docs/12-platform-roadmap.md](docs/12-platform-roadmap.md) | 平台落地线路图 |
| [prototype/platform.html](prototype/platform.html) | 平台可交互原型 |

模块细则：

| 文档 | 内容 |
| --- | --- |
| [docs/01-product-prototype.md](docs/01-product-prototype.md) | 面对面产品原型 |
| [docs/02-architecture.md](docs/02-architecture.md) | 面对面架构 |
| [docs/03-tech-choices.md](docs/03-tech-choices.md) | 面对面技术选型 |
| [docs/04-roadmap.md](docs/04-roadmap.md) | 面对面落地线路图 |
| [prototype/index.html](prototype/index.html) | 面对面可交互原型 |
| [docs/05-simultaneous-prototype.md](docs/05-simultaneous-prototype.md) | 同声传译产品原型 |
| [docs/06-simultaneous-architecture.md](docs/06-simultaneous-architecture.md) | 同声传译架构 |
| [docs/07-simultaneous-tech-choices.md](docs/07-simultaneous-tech-choices.md) | 同声传译技术选型 |
| [docs/08-simultaneous-roadmap.md](docs/08-simultaneous-roadmap.md) | 同声传译落地线路图 |
| [prototype/simultaneous.html](prototype/simultaneous.html) | 同声传译可交互原型 |
