# 16. 启动优化效果实测验证（真机 A/B）

> 2026-09-24。目的：验证 `ac5974c 启动优化` 那轮改动**在真机上到底有没有效果**。
> 结论前置：**真机上没有可测量的改善（280ms → 279ms，p=0.605）**，
> 原因是该轮优化针对的瓶颈（SwiftData 开库）实测只需要 **12ms**，不是瓶颈。

---

## 1. 测量方法

| 项 | 值 |
|---|---|
| 设备 | iPhone 13「菀墨」`REDACTED_UDID`，iOS 26.7 |
| 构建 | Release / iphoneos / arm64，自动签名 |
| 对照版本 | `4e9dbd2`（优化前，HEAD~2） |
| 优化版本 | `3e22adb`（当前 HEAD） |
| 终点口径 | `RootView.onAppear` 后延迟一个 runloop 打点（逼近 `CA::Transaction::commit`） |
| 起点口径 | `sysctl KERN_PROC_PID` 取进程创建时间 |
| 采集 | `devicectl device process launch --terminate-existing` + `idevicesyslog` 抓 os_log |

**对照公平性**：优化前版本原本没有埋点，已给它补上**完全相同**的 `AppLaunchTracker`
与**相同的终点定义**。埋点本身开销为 `os_signpost` + 一次日志，两边一致。

---

## 2. 真机 A/B 结果：无显著差异

```
对照(优化前)  中位数 280ms   样本 276 283 280 278 334 302 279 276   n=8  CV 7.0%
优化后(当前)  中位数 279ms   样本 279 270 269 295 295              n=5  CV 4.6%

改善 +0ms (-0.2%)   置换检验 p=0.605   → 差异不显著
```

**判定：该轮启动优化在真机上没有可测量的收益。**

> 对照：同一对版本在**模拟器**上测出 389ms → 371ms（-4.6%，p=0.0088）。
> 模拟器给出了一个真机上不存在的"改善" —— 见 §4。

---

## 3. 为什么没有收益：真机阶段拆分

真机冷启动各阶段（`优化后` 版本，中位数）：

| 阶段 | 耗时 | 占比 |
|---|---|---|
| **pre-main（dyld + 镜像初始化）** | **11 ms** | 4% |
| App init → environmentReady | ~6 ms | 2% |
| **environmentReady → firstFrame** | **~250 ms** | **89%** |
| 合计 | ~280 ms | |

各项子测量：

- **pre-main = 11ms**（n=6，范围 10–13，CV 13%）—— 由新增的 C 构造函数测得
- **SwiftData 开库 = 12ms**（n=6，范围 12–27）
- 音频/语音合成已懒加载，不在首帧路径

### 关键发现：开库只要 12ms

原优化文档判断「SwiftData 同步开库是阻塞首帧最重的一项」。
**实测开库只需 12ms**，把它移出关键路径最多省 12ms —— 在 280ms 的启动里不可测量。

那阶段拆分里出现的 `storeReady +179ms` **不是开库耗时**，而是
`Task.detached(priority: .utility)` 这个后台任务**被调度的延迟**
（主线程忙于渲染时，utility 任务会排队）。开库本身由新增的
`STORE open took Nms` 打点直接测得。

**因此真正的瓶颈是 environmentReady → firstFrame 之间的 ~250ms**，
即 SwiftUI/UIKit 的框架初始化与首次渲染 —— 这一轮优化没有触及它。

---

## 3b. 那 250ms 的构成 —— 用空白 App 做对照

为了区分「框架固有问题」与「本 App 特有问题」，另建了一个**空白 SwiftUI App**
（Hello World，`scaffold-ios` 生成 + 同样的 C 构造函数与打点），在同一台 iPhone 13 上测同一批分段。

新增打点：`appBody`（`DuiyiApp.body` 首次求值）、`rootBody`、`homeBody`。
注意 `body` 会被多次求值，所以用 `beginOnce` 只记首次。

### 真机分段表（中位数）

| 分段 | 空白 App | **Duiyi** | 差值 | 性质 |
|---|---|---|---|---|
| pre-main | ~1–22 ms | 11 ms | ~0 | 框架 |
| **App init → 首个 body 求值** | **115–143 ms** | **117 ms** | **≈0** | ⛔ **框架固有** |
| 首个 body → 视图树末级 body | 17–22 ms | 29 ms | +10 ms | 轻 |
| **视图 body → 首帧提交** | **5 ms** | **89 ms** | **+84 ms** | ⭐ **本 App 特有** |
| 合计 | ~150 ms | ~257 ms | ~107 ms | |

### 消融实验结果（真机，每组 3–4 次取中位数）

| # | 实验 | 结果 |
|---|---|---|
| 1 | 空白 App + `NavigationStack` | **+0ms**（5→5ms）→ 排除 |
| 2 | + SF Symbols + 卡片结构 | **+24ms**（5→29ms）→ **该结构本身有成本** |
| 3 | + 无障碍修饰（`accessibilityIdentifier/Label/Hint` + `children:.combine`） | **+3ms**（66→69ms）→ 排除 |
| 4 | **Duiyi 首页内容换成 `Text("x")`**（保留全部外围修饰符 / environment / task） | **`body→appear` 40→11ms；`appear→commit` 74→66ms** |

**实验 4 是关键**：内容只剩一个 `Text` 后，`appear→commit` 仍是 66ms，
而结构等价的对照 App 只有 36ms —— **说明这段的大部分不是内容造成的，而是外围脚手架。**

### 完整归因（真机 iPhone 13，冷启动 ≈240ms）

| 段 | ms | 占比 | 性质 | 依据 |
|---|---|---|---|---|
| pre-main | 18 | 7% | ⛔ 框架 | 空白 App 同样 |
| App init → environmentReady | 6 | 3% | ✅ 已极轻 | 延迟开库生效 |
| **SwiftUI 引导（appBody）** | **~110** | **46%** | ⛔ **框架固有** | 空白 App 115–143ms |
| 视图树 body 求值（rootBody+homeBody） | 22 | 9% | ~ | — |
| **首页内容渲染** | **29** | **12%** | ⭐ **可优化** | 内容换 Text 后 40→11ms |
| **外围脚手架（commit 阶段）** | **~35** | **15%** | ⭐ **可优化** | 内容换 Text 后仍 66ms（对照 36ms） |

### 结论

- **46% 是 SwiftUI 框架引导，不可优化**（空白 App 对照证明）。原优化文档的所有努力都发生在这段之前或之后，**根本碰不到它**。
- **可优化的只有两块，合计约 64ms（27%）**：
  1. **首页内容 29ms** —— 结构 + SF Symbols 的成本（实验 2 已量化结构本身占 24ms）
  2. **外围脚手架 ~35ms** —— 内容换空后依然存在。候选：`@Environment(AppEnvironment.self)` 的 Observable 追踪、`.sheet`、`.toolbar(.hidden)`、`.preferredColorScheme(.dark)`、`RootView` 的 `.onChange` ×2 与 `.navigationDestination`

### 下一步（按 ROI）

1. **继续二分那 ~35ms**：在实验 4 的基础上，逐个摘掉 `HomeView`/`RootView` 的外围修饰符（每项一个构建）。
   优先 `@Environment(AppEnvironment.self)`（Observable 环境追踪是最大嫌疑）与 `.sheet`。
2. **首页内容 29ms**：SF Symbols 有固定首载成本（CoreGlyphs）。可评估是否值得延后渲染次要卡片。
3. ⛔ **不要再投入 pre-main 或 SwiftData**：分别只占 7% 和 3%，且前者是框架固有。

⚠️ **方法论修正**：本文早期版本曾用「89ms vs 空白 App 5ms」得出"84ms 全可优化"，
那是**错误的对比** —— Duiyi 的 `firstFrame` 经 `DispatchQueue.main.async` 延迟一拍
（刻意逼近 `CA::Transaction::commit`），而当时的对照组是直接 `onAppear`。
两者不是同一个终点。**给对照组补上相同的延迟打点后，真实差值才显现。**
这正是"口径必须一致"的一个真实案例。

---

## 4. ⚠️ 模拟器结论不能用于真机（双向失真）

同一对版本、同一口径，两边数据如下：

| 指标 | 模拟器 | 真机 iPhone 13 | 差异 |
|---|---|---|---|
| **pre-main** | **257 ms** | **11 ms** | 模拟器高估 **23 倍** |
| SwiftData 开库 | 124 ms | 12 ms | 模拟器高估 **10 倍** |
| 总启动 | 459 ms | 280 ms | — |

**失真方向是相反的**：

- 模拟器**没有 dyld 共享缓存**，框架要从宿主磁盘加载 → **严重高估 pre-main**
- 模拟器跑在 Mac 的 SSD 与充裕内存上 → **严重低估 I/O 与缺页成本**

所以模拟器上"pre-main 占 56%"是真机上的假象（真机只占 4%）。
**启动优化必须真机验证，模拟器只能用于功能性回归。**

---

## 5. 弱链接 FoundationModels / Speech / Translation 评估

**结论：不建议做。** 依据：

1. **pre-main 在真机上总共只有 11ms**。即使把这些框架的加载成本全部消除，
   上限收益也只是其中一部分 —— 而 `SwiftUI`/`UIKit`/`Foundation` 是必需的，动不了。
   乐观估计收益 < 10ms（< 4%），且会被测量噪声淹没。
2. **风险显著**：弱链接后每个调用点都要做可用性判断，遗漏会在运行期崩溃；
   `FoundationModels` 的可用性还依赖设备与系统版本，分支会扩散。
3. **收益随时间衰减**：iOS 的 dyld 共享缓存让框架加载越来越便宜，
   这条优化路径的长期价值在下降。

**真正的收益点不在这里，而在 §3 那 ~250ms。**

---

## 6. 建议的下一步（按 ROI）

**只剩两块可优化，合计约 64ms（占 27%）。** 详见 §3b 的完整归因表。

1. **继续二分那 ~35ms 的外围脚手架**（最高优先）。
   在"内容换成 `Text("x")`"的基础上，逐个摘掉外围修饰符，每项一个构建 + 真机测 3 次。
   建议顺序：
   - `@Environment(AppEnvironment.self)` / `@Environment(AppCoordinator.self)`（Observable 追踪，最大嫌疑）
   - `.sheet(isPresented:)`
   - `.toolbar(.hidden, for: .navigationBar)` + `.navigationBarTitleDisplayMode(.inline)`
   - `RootView` 的 `.onChange` ×2 与 `.navigationDestination(for: AppRoute.self)`
2. **首页内容 29ms**：其中 SF Symbols + 卡片结构约占 24ms（实验 2 已量化）。
   可评估次要卡片延后一帧渲染的收益与代价。
3. ⛔ **停止在 pre-main 与 SwiftData 上投入**：分别只占 7% 与 3%，且前者经空白 App 对照证明是框架固有的。
4. **不要以"首帧优化"为由给 `DeferredTaskStore` 加码**：它换来 12ms，
   却引入懒建兜底 / 失败回退 / warm 时机三处复杂度。保留或简化都行，但天花板已明确。
5. **Instruments 值得修通**：本次 xctrace 对这台设备一直超时
   （`Timed out waiting for device to boot`，而 `devicectl` 可正常连、DDI 也已缓存，USB 上 `ioreg` 可见 iPhone）。
   修通后可用 App Launch / Time Profiler 直接定位，比手工消融快得多。
   排查方向：设备解锁状态、`sudo killall -9 usbmuxd` 后重试、Xcode Devices 窗口手动准备设备。
   它带来的是 12ms 的收益，但引入了懒建兜底、失败回退、warm 时机等复杂度。
   若为可维护性考虑，保留亦可，但**不应再以"首帧优化"为由继续加码**。
4. **二进制重排保持现状**。已验证正确生效（1479 符号 100% 匹配、`_main` 打头），
   零运行时成本，作为管线保留合理 —— 但不要期待它在当前包体下可测量。
5. ⚠️ **`Order/App.order` 的来源与流程不符**：文件头注释显示来源于
   **模拟器**构建（`build/Release-sim/...`），而 `tools/generate-order-file.sh`
   注释中规定的命令是 `-sdk iphoneos`（真机构建）。建议按规定的真机构建重新生成一次，
   并在脚本里加校验，避免下次不一致。

---

## 7. 本次新增的埋点（已落在代码里）

| 文件 | 作用 |
|---|---|
| `Duiyi/Services/Diagnostics/EarlyLaunchMark.c`（新增） | C 构造函数，在**任何 Swift 代码之前**记录 pre-main 耗时。用纯 C + `os_log`，不需要 bridging header |
| `AppLaunchTracker.swift` | ① 记录埋点自身被触碰的时刻（`TRACKER init at +Nms`）<br>② **打印 6 个阶段的完整拆分**（原实现只打印总数，导致盲区） |
| `DeferredTaskStore.swift` | 打印**真实开库耗时**（`STORE open took Nms`），区别于后台调度延迟 |

真机日志形如：

```
EARLY pre-main: 11 ms since process start
TRACKER init at +23ms since process start
STORE open took 12ms (background task)
App launch first-frame: 270ms since process start
Launch stages (since/+delta ms): processStart=22/+22 appInit=23/+1
  environmentReady=30/+6 storeReady=226/+196 viewModelsReady=226/+0 firstFrame=270/+44
```

---

## 8. 方法论提醒

- **单次样本会骗人**：本轮首次冒烟测出「476ms vs 359ms」，看起来有 117ms 大幅改善；
  交替测量 5 次后真实差异是 18ms（模拟器）/ 0ms（真机）。
  任何启动优化结论都不能基于单次测量。
- **必须看显著性**：`p=0.605` 与 `p=0.0088` 是两个完全不同的结论，
  只看中位数差值（-0.5ms vs -18ms）分不出来。
- **口径不一致=结论无效**：起止点、构建类型、设备、样本量任一项不同，都不能直接比。
