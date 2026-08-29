# 对译 Duiyi

面对面离线字幕，加上同声传译（听现场、看或听译文）。

Xcode 工程：[`Duiyi.xcodeproj`](Duiyi.xcodeproj)  
最低系统：iOS 26.4，真机优先（语音与翻译模型在模拟器上不完整）

## 打开工程

```bash
open Duiyi.xcodeproj
```

首次运行会引导：选语言 → 麦克风 / 语音识别 → 下载模型。之后：

- **面对面**：手机平放，上半屏倒字给对方，下半屏正字给用户
- **同声传译**：单栏正字听现场；可选戴耳机读出译文

中间按钮：点按开始 / 暂停。中间栏右侧齿轮打开设置（长按中间按钮也可以）。同声传译进界面后不会自动开始听。

## 设计文档

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
