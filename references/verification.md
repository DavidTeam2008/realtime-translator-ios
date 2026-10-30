# 验证与真机验收

> 触发：跑测试、真机验收、性能测量时读。入口优先用脚本；设备亮屏解锁。

## 命令

| 命令 | 用途 |
|---|---|
| `make test` | 模拟器单元（`DuiyiTests`） |
| `make test-ui` | 模拟器 UI（语音用例 skip） |
| `make device-test` | 真机全套（预热 + 120 单元 + 3 UI） |
| `make device-test-ui` | 真机 UI（预热后） |
| `make device-test-one TEST=...` | 真机单用例 |
| `APM_DEVICE=<CoreDevice ID> make device-test` | 换设备 |
| `make check-docs` / `make check-agents` | 文档 / 团队基线 |

真机脚本依赖 `mobilebuildmcp`；启动测量另需 `idevicesyslog`、`timeout`。模拟器默认 `iPhone 17 Pro Max` / iOS 26.4.1，runtime 不同用 `SIM_OS=` 覆盖。

## 验证矩阵

| 变更 | 最低验证 |
|---|---|
| Domain 纯逻辑 / 文本工具 | 模拟器单元 |
| ViewModel 策略 | 模拟器单元（假引擎/假 store/假合成器） |
| UI 导航 / 布局 | 模拟器 UI；手工走主路径 |
| 语音 / 翻译 / TTS / 音频 | **真机**；模拟器不能替代 |
| SwiftData / 任务留存 | 单元 + 杀进程重开；迁移需演练 |
| 启动 / 性能 | Release 真机、`measure-launch.sh`、n≥10、同口径 |
| 文档 / 配置 | `make check-docs` + 事实核对 |

## 计数与预期

- 基线 **120 单元 + 3 UI**；真机 **123**。只增不减；改计数同步本文件。
- 模拟器 `testSimultaneousListeningPressure` skip（无 `SpeechTranscriber`）是预期，不要 mock。
- 真机 UI 前必须预热 testmanagerd（脚本已强制）；iOS 15+ 还需过 `Enable UI Automation` 密码弹窗（HANDOFF §3.2）。
- 首次真机跑脚本自动生成 runner profile；provisioning 警告无害。

## 真机坑（其余见 HANDOFF §2）

1. `exit 74` / automation 超时：先预热，再查密码授权弹窗。
2. 手机锁屏：脚本 exit 2；解锁后重跑。
3. 免费证书 App 数量满：删不用的自签名 App，或换付费账号。
4. 设备 ID：`devicectl` 显示硬件 UDID；脚本用 CoreDevice ID（`mobilebuildmcp device list` 亦然）。
5. 首页 `not hittable`：用 `-duiyi.onboardingComplete YES`；历史返回用 `nav-home`。

## 性能口径

- `testColdLaunch` 0.31–0.33s 是 XCTest“到首页卡片可点”；`AppLaunchTracker` 240–280ms 是“进程创建 → 首帧提交”。不要混用。
- 模拟器高估 pre-main 20 倍以上；单次样本不可用；n≥10，先读 `.apm/baseline/README.md` 和 `.apm/report.md`。

## 失败处理

- 先定位原因再改；环境/网络/已知 flaky 不计入修复次数。
- 同一失败修复 2 次仍失败、同一子任务 3 轮无进展：停止，按 `references/workflow.md` 上报。
- 设备/签名不可用：最多重试 1 次，然后写“未验证”+ 手动步骤；不要反复跑全套。
- 不能实际操作设备时，不得声称已验证。
