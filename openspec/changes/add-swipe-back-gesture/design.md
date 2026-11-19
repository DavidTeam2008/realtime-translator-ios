## Decisions

1. **采用根级左边缘 DragGesture（方案 B），不依赖 UIKit 内部 pop 手势（方案 A）。**
   - 方案 A 需要拿到隐藏导航栏的 `UINavigationController` 并重设 `interactivePopGestureRecognizer`，依赖 SwiftUI 私有视图层级，跨 iOS 版本脆弱。
   - 方案 B 只依赖公开的 SwiftUI 手势和现有 `AppCoordinator`，可单测、可用 XCUITest / 模拟器手势验证；代价是缺少跟手转场。
   - 方案 C（显示透明系统导航栏以恢复系统手势）会改变现有自定义 chrome 的高度与视觉，不采用。
2. **触发条件集中在 `EdgeSwipeBackPolicy`：**
   - 导航栈非空；
   - 手势起点 `x` 不超过 24pt；
   - 横向位移不少于 60pt；
   - 纵向漂移绝对值小于横向位移，且不超过 80pt（避免「主要是纵向滑动」误触发）。
3. **挂载方式：** 在 `RootView` 的 `NavigationStack` 上使用 `.simultaneousGesture`，避免阻断子视图按钮与滚动；策略不通过时不消费手势。
4. **返回动画：** 在 `withAnimation(.easeInOut(duration: 0.2))` 中调用现有 `coordinator.pop()`，沿用 `NavigationStack` 的转场。
5. **状态语义：** 返回路径不新增任务操作；模块页 `onDisappear` 继续负责停止听写，任务保持进行中，与点击「首页」一致。

## Risks

- **与横向内容冲突**：历史行已有 trailing `swipeActions`，sheet 内有语言网格；限制仅左边缘起点与纵向漂移可降低误触，UI 测试覆盖模块页与首页。
- **根路径越界**：策略先检查导航栈非空；空栈直接忽略。
- **手势竞争**：`.simultaneousGesture` 不阻塞子视图点击；若模拟器或真机出现竞争，回退为仅边缘窄条命中区。
- **没有跟手转场**：用户可见差异是页面在松手后播放返回动画；本试点接受该取舍，后续可评估原生方案 A。
- **返回不结束任务**：返回后任务仍在进行中，用户可在首页「未完成的任务」继续；这是既有产品语义，不是本变更引入的行为。

## Verification

- **单元测试**：`EdgeSwipeBackPolicy` 的接受矩阵与拒绝矩阵（根路径、起点偏移、短距离、纵向漂移）。
- **UI 测试**：模块页左边缘右滑后回到首页；首页边缘右滑不产生导航；现有 `nav-home` 路径仍可用。
- **门禁**：`make evidence-unit` / `make evidence-ui` 产生新证据；`make delivery-check CHANGE=add-swipe-back-gesture`、`make verify-static`、`make release-check` 通过。
- **人工复核**：模拟器或真机观察返回动画与任务不丢；不修改既有断言。
