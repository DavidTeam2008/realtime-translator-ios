# 15. 启动优化（对照抖音实战篇 + 二进制重排落地）

> ⚠️ **2026-09-24 订正**：本文的收益判断已被**真机实测推翻**。见
> [16-startup-measurement-verification.md](16-startup-measurement-verification.md)。
> 要点：真机 A/B 显示**无显著改善**（280ms → 279ms，p=0.605）；
> SwiftData 实际开库耗时**只有 12ms**（不是"最重的一项"）；
> pre-main 在真机只占 **11ms**，瓶颈在 `environmentReady → firstFrame` 的 ~250ms。
> 本文其余章节（文章精读、诊断、二进制重排原理）仍然有效。

> 参考：字节《抖音品质建设 - iOS启动优化〈实战篇〉》（developer.volcengine.com/articles/7599494340179984426）
> 结论前置：本 App 瓶颈在 `main` 后同步主线程工作，二进制重排已落地但预期仅 5–30ms；
> 本次大头收益来自 SwiftData 延迟开库 + 音频/语音合成懒加载 + 首帧后预热。

## 1. 文章精读（监控 / 工具 / 最佳实践）

- **监控**：起点 `sysctl` 进程创建时间，终点逼近 `CA::Transaction::commit`
  （iOS12- `viewDidAppear`，iOS13+ `applicationDidBecomeActive`）；分阶段 + `os_signpost`；
  无侵入用 RunLoop `CFRunLoopPerformBlock`（<13）/`kCFRunLoopBeforeTimers`（≥13）；
  研发期自动化（Release 包 + 控制变量 + 二分归因 + 火焰图），线上看大盘 pct50 并拆版本/机型/地区。
- **工具**：`Time Profiler` 只做粗粒度（1ms 采样）；`System Trace` 看 `Page In` +
  线程挂起/抢占 + System Load；`os_signpost` 近零损耗打点；火焰图（`objc_msgSend`
  hook / 编译期插桩）做 diff 归因。
- **最佳实践（删 > 延迟 > 并发 > 更快）**：`main` 前减动态库、清无用代码、迁 `+load`/静态构造；
  `main` 后用启动器做并发 DAG + 延迟时机 + 耗时管控；三方 SDK 下线/延迟；高频缓存；
  全局锁（dyld/Runtime/`dlopen`）排查；QoS 与线程数；图片放小 Asset + 子线程预建；
  `fishhook` 能免则免；`Page In` 靠**二进制重排**（`ld -order_file`，抖音静态扫描 ~90%
  vs Facebook LLVM 插桩最优）。

## 2. 本 App 启动链诊断

- 纯 Swift + SwiftUI，无 ObjC/`+load`/C++ 静态构造/自建动态库，仅链接
  `AVFoundation/Speech/Translation` 系统库 → `main` 前 `dyld` 极小（`Duiyi.xcodeproj`）。
- 真瓶颈全在 `main` 后主线程同步链（改前）：
  1. `Duiyi/App/AppEnvironment.swift` `init` 同步 `ModelContainer(Schema(...))`
     开 SQLite（文件 I/O + 迁移检查），阻塞首帧最重一项；
  2. `BilingualSpeechEngine(init)` → `AudioEngineCapturer.init` 同步
     `AVAudioEngine() + sharedInstance()`，碰音频硬件（`Duiyi/Services/Audio/AudioEngineCapturer.swift`）；
  3. `SystemSpeechSynthesizer.init` 同步 `AVSpeechSynthesizer()`，拉语音 daemon IPC
    （`Duiyi/Services/SpeechSynthesis/SystemSpeechSynthesizer.swift`）；
  4. `RootView.onAppear` 同步建 4 个 VM + `HomeView.task` 同步查 `unfinishedTasks()`
     （`Duiyi/App/RootView.swift`，`Duiyi/Features/Home/HomeView.swift`），把功能代码页
     提前 `Page In`。
- 首帧本身轻（`HomeView` 纯 `ScrollView + systemImage`），`bootstrap()` 只在进二级页才跑，
  不在启动路径。

## 3. 本次改动（7 文件 + 2 新增 + order/script）

| 改动 | 文件 | 效果 |
|---|---|---|
| SwiftData 延迟开库 | `Duiyi/Services/Persistence/DeferredTaskStore.swift`（新增），`Duiyi/App/AppEnvironment.swift` | `init` 零 I/O；首次使用（首帧后）才在 `.utility` 后台 `openContainer()`，失败回退内存 |
| 音频懒加载 | `Duiyi/Services/Audio/AudioEngineCapturer.swift` | `AVAudioEngine/AVAudioSession` 移到 `start()` 内创建，`stop()` 释放 |
| 语音合成懒加载 | `Duiyi/Services/SpeechSynthesis/SystemSpeechSynthesizer.swift` | `AVSpeechSynthesizer` 改 `ensureSynthesizer()` 首次 `speak()` 才建 |
| 首帧后预热 VM | `Duiyi/App/RootView.swift` | `onAppear` 只保 onboarding + `markFirstFrame()`；VM + store 预热移到 `.task(priority: .utility)`；二级页有缺失兜底懒建 |
| Home 延迟查库 | `Duiyi/Features/Home/HomeView.swift` | `.task` 改 `.task(priority: .utility)`，空态先画 |
| 启动埋点 | `Duiyi/Services/Diagnostics/AppLaunchTracker.swift`（新增） | `sysctl` 进程起点 + `os_signpost("launch")` 分段 + `MetricKit` 回调 + 首帧耗时日志 |
| 二进制重排 | `Order/App.order` + `Duiyi.xcodeproj/project.pbxproj`（Release `ORDER_FILE`）+ `tools/generate-order-file.sh` | Release `__text` 按启动顺序排（已验证 `_main` 打头，1479 符号） |

验证：Release-sim `BUILD SUCCEEDED`（order 生效前后各一次）；
`DuiyiTests` 全过（`TEST SUCCEEDED`）；
`DuiyiUITests/SimultaneousFlowTests` 在基线（stash 前）同样失败（新机 onboarding 盖住首页，
`home-module-simultaneous not hittable`），属预存失败，非本次回归。

## 4. 二进制重排：对本 App 提升有多大

- **原理**：启动函数离散 → `Page In` 利用率低；`order_file` 把启动热符号排到连续区，
  减少缺页次数。抖音大包（百 MB/上万函数/上百 Page In）可省 100–200ms+。
- **本 App 实测口径**：二进制 ~12MB（sim），`__text` 启动热符号 ~1479 个；
  无 `+load`/大动态库，冷启 Page In 基数小（预计 <30 次），且 iOS26 `dyld3 + page cache + SSD`
  单次缺页 ~0.1–0.5ms。按此估算**重排收益约 5–30ms（< 总启动 2%）**，不可感知。
- **为什么仍落地**：零运行时成本、纯构建期改动、为以后包变大留好管线；
  真正省 Page 的是本次的“延迟加载”（不进首帧的代码页根本不碰），效果比重排更持久。
- **维护**：Swift 符号每次 wholemodule 构建都变，**禁止手写**，必须用脚本从 Release
  二进制再生：
  ```bash
  xcodebuild -project Duiyi.xcodeproj -scheme Duiyi -configuration Release \
    -sdk iphoneos -derivedDataPath build/Release -destination 'generic/platform=iOS' build
  ./tools/generate-order-file.sh build/Release/Build/Products/Release-iphoneos/Duiyi.app/Duiyi
  ```
  仅 Release 生效（`ORDER_FILE` 只配了 Release），Debug 增量构建不受影响；
  `Order/` 在工程同步目录之外，不会打进包。
- **测量**：`AppLaunchTracker` 日志（首帧 ms）+ `MetricKit` + Instruments `App Launch`
  模板对比 `Page In` 次数/字节；发版后重采一次 order。

## 5. 后续（ROI 排序）

1. 真机冷启实测（`DYLD_PRINT_STATISTICS=1` + App Launch trace），确认 SwiftData 延迟量；
2. `FoundationModels/Speech/Translation` 弱链接评估（首帧完全用不到的系统框架）；
3. 轻量启动器（并发 DAG + CodeReview 管控新增启动任务）；
4. UITest 基线修（launch 参数跳过 onboarding，如 `UITEST_SKIP_ONBOARDING=1`）。
