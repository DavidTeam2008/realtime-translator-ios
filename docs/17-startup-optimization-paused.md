# 17. 启动优化：暂停记录

> 2026-09-24。**本方向暂停，不继续投入。** 结论与余额记录在此，供日后需要时接续。

## 为什么暂停

启动耗时已经不是本项目的短板：

| 事实 | 数据 |
|---|---|
| 真机冷启动（iPhone 13） | **240ms** —— Apple 建议首帧 ≤600ms，已在优秀区间 |
| 其中框架固有、不可优化 | **46%**（SwiftUI 引导 ~110ms，空白 App 对照证明） |
| 全部可优化空间 | **约 64ms（27%）** |
| 上一轮优化的实际收益 | **0ms**（p=0.605，无统计显著差异） |

而剩下这 64ms 的来源是：

- **首页内容 29ms** —— 结构 + SF Symbols 的成本
- **外围脚手架 ~35ms** —— 候选是 `@Environment` / `.sheet` / `.toolbar` 等
  **这些是产品需要的能力，把它们当敌人去砍，方向是错的**

**判断：边际收益已低于风险与复杂度，ROI 不划算。**

## 已完成的测量基线（可直接复用）

打点已固化在代码里，日后需要复查时无需重做：

| 打点 | 位置 | 含义 |
|---|---|---|
| `EARLY pre-main` | `EarlyLaunchMark.c`（C 构造函数） | dyld + 镜像初始化 |
| `TRACKER init at +Nms` | `AppLaunchTracker.init` | 埋点首次触碰 |
| `appBody` / `rootBody` / `homeBody` | 三个 `body` 首次求值 | 视图树求值 |
| `rootAppear` / `homeAppear` | `onAppear` | 进入出现回调 |
| `homeTaskStart` / `homeTaskEnd` | `HomeView.task` | 后台任务边界 |
| `firstFrame` | `RootView.onAppear` 后延迟一拍 | 逼近 `CA::Transaction::commit` |
| `STORE open took Nms` | `DeferredTaskStore.openContainer` | **真实开库耗时（区别于后台调度延迟）** |

查看方式：

```bash
# 真机
idevicesyslog -u <UDID> | grep -a "Launch stages\|EARLY\|STORE open"
```

⚠️ **口径提醒**：`firstFrame` 是延迟一拍打点，与直接用 `onAppear` 打点**不可比**。
做对照实验时必须用同一终点定义（这次的教训，见 `docs/16` §3b 末）。

## 如果日后要接续，从这里开始

按 ROI 排序，**均需真机验证**：

1. **二分那 ~35ms 脚手架**：把 `HomeView` 内容临时换成 `Text("x")`（保留全部外围），
   然后逐个摘掉外围修饰符，每项一个构建 + 真机测 3 次取中位数。建议顺序：
   `@Environment(AppEnvironment.self)` → `.sheet(isPresented:)` →
   `.toolbar(.hidden)` + `.navigationBarTitleDisplayMode(.inline)` →
   `RootView` 的 `.onChange` ×2 与 `.navigationDestination(for: AppRoute.self)`
2. **首页内容 29ms**：SF Symbols 首载有固定成本（CoreGlyphs）。
   评估次要卡片延后一帧渲染的收益与代价 —— 注意别损害首屏可用的感知。
3. ⛔ **不要碰 pre-main（7%）与 SwiftData（3%）** —— 前者经空白 App 对照证明是框架固有。

## 已排除的方向（不必再试）

| 方向 | 实测结果 |
|---|---|
| 二进制重排 | 已正确落地（1479 符号 100% 匹配、`_main` 打头），但当前包体下**不可测量** |
| SwiftData 延迟开库 | 真实开库仅 **12ms**，移出关键路径的收益淹没在噪声里 |
| 弱链接 FoundationModels / Speech / Translation | pre-main 真机仅 11ms，上限收益 < 10ms，**低于噪声** |
| `NavigationStack` | **+0ms** |
| 无障碍修饰 | **+3ms** |

## 环境遗留

- 设备上装着带完整打点的 Release 版 `com.david.Duiyi`（非 App Store 版本，下次正常构建会覆盖）
- 两个我误建的 trace 目录未删：`Launch_Duiyi_2026-09-24_19.40.13_D7880679.trace/`、
  `Launch_Duiyi_2026-09-24_19.40.25_AD23ADBF.trace/`
- `xctrace` 对这台设备持续超时（`Waiting for device to boot`），
  而 `devicectl` 正常、DDI 已缓存、`ioreg` 可见 iPhone。
  修通后可用 App Launch / Time Profiler 直接定位，比手工消融快得多。
