# 18. 启动目标可行性前置验证

> 2026-09-26。按 P1 流程，在继续任何启动优化前先做最小对照组。

## 结论

目标「冷启动 ≤200ms」被最小对照组地板挡住：

```text
control（最小 Text("x")）：n=20，p50=210ms，CV=2.7%，usable
candidate（当前首页）：     n=20，p50=262.5ms，CV=8.3%，usable
目标：200ms
判定：blocked_by_control_floor
```

因此本轮**不进入局部启动优化**，也不把 control 的 210ms 宣称为理论极限；正确动作是升级为架构/需求决策。

## 口径

- 设备：iPhone 13 / iOS 26.7 / physical
- 构建：Release
- warmup：3 次，不计入样本
- 样本：n=20，间隔 5s
- 指标：`startup.cold.first_frame`
- control 与 candidate 使用同一测量 profile、设备、构建类型和命令

## Control 变化

在临时 detached worktree 中只替换首页内容为：

```swift
Text("x")
```

保留：

- App 生命周期；
- `AppLaunchTracker` 与 `EarlyLaunchMark` 埋点；
- 根视图、onAppear、task、sheet 等外围生命周期；
- Release 构建与同一测量命令。

## 证据

- control：`.apm/runs/control-clean-2b3a1ea-warmup3-n20/`
- candidate：`.apm/runs/20260926-clean-2b3a1ea-warmup3-n20-candidate/`
- 机器结论：`.apm/feasibility/20260926-startup-200ms.json`

## 后续

在接受「改目标」或「改架构」之前，不继续做局部启动优化。若要重新评估，必须先改变一个架构级变量，并重新建立 control 与 candidate 的同口径 n=20 测量。
