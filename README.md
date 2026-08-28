# 对译 Duiyi

面对面、离线、实时的中英互译字幕。

Xcode 工程：[`Duiyi.xcodeproj`](Duiyi.xcodeproj)  
最低系统：iOS 26.4，真机优先（语音与翻译模型在模拟器上不完整）

## 打开工程

```bash
open /Users/<user>/Documents/code/ios/realtimeTranslator-ox/Duiyi.xcodeproj
```

首次运行会引导：选「我看的语言」→ 麦克风 / 语音识别 → 下载中英模型。之后把手机平放在两人中间即可。

- 下半屏正字给用户
- 上半屏旋转 180° 给对方
- 中间按钮：点按开始 / 暂停，长按设置

## 设计文档

| 文档 | 内容 |
| --- | --- |
| [docs/01-product-prototype.md](docs/01-product-prototype.md) | 产品原型 |
| [docs/02-architecture.md](docs/02-architecture.md) | 架构 |
| [docs/03-tech-choices.md](docs/03-tech-choices.md) | 技术选型 |
| [docs/04-roadmap.md](docs/04-roadmap.md) | 落地线路图 |
| [prototype/index.html](prototype/index.html) | 可交互界面原型 |
