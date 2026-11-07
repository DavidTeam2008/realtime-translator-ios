# 白屏检测记录

## 结论

当前构建**未发现可复现的白屏/黑屏/纯色屏问题**，因此没有进入定位或修复阶段。

## 证据

### 真机

- 设备：iPhone 13 / iOS 26.7 / physical
- 旧 `idevicescreenshot -u <DEVICE_UDID> ...` 两次均失败：
  `Could not start screenshotr service: Invalid service`
- 通过新增的 `apm_screenshot.py` + 可选 `pymobiledevice3` DVT 后端成功抓取真机 PNG：
  `real-wrapper-final.png`，1170×2532（backend=`pymobiledevice3-native`）。
- 真机截图经 `apm_white_screen.py --json` 判定为 `content_present`。
- 旧 screenshotr 后端仍标记为不可用；DVT 后端是真机验证通过的路径。

### 模拟器替代验证（明确标注）

- 模拟器：iPhone 17 Pro / iOS 26.4
- 构建：Duiyi / Release / `com.david.Duiyi`
- 启动后重新启动 App，在 0.1s、0.3s、0.6s、1s、2s、4s 抓取 6 帧。
- `apm_white_screen.py --json` 结果：6/6 `content_present`，`blank_count=0`。

代表性指标：

```text
frame-01: modal_ratio=0.7866, luminance_std=80.885, edge_density=0.00578
frame-02: modal_ratio=0.7178, luminance_std=76.485, edge_density=0.01091
```

即使某帧白色区域占比较高，文字/控件边缘与亮度变化仍满足“有内容”判据。

## 后续

若要继续白屏闭环，需要以下任一输入：

1. 一个已知会白屏的页面/状态及其进入步骤；
2. 允许在目标工程中注入一个可控白屏故障用于 detector 回归测试；
3. 如需更多真机帧，继续用 `apm_screenshot.py` 的 DVT 后端采集。

本记录不修改目标工程源码。
