# 验证证据（evidence）

> 目的：把「已验证 / 测试通过 / 真机通过 / 性能没退化」从**自由文本**变成**可被脚本反驳的对象**。
> 规则：无 evidence 的「已验证」按**未验证**处理；`UNVERIFIED` 不是 `PASS`。
> 事实源：schema 见 [schema.json](schema.json)，起稿见 [TEMPLATE.json](TEMPLATE.json)，测试基线见 [harness/test-baseline.json](../test-baseline.json)。

## 1. 目录与入库策略

| 文件 | 说明 | 入库 |
| --- | --- | --- |
| `schema.json` | draft-07 证据 schema（`tools/evidence.py` 实现其子集，无第三方依赖） | 是 |
| `TEMPLATE.json` | 起稿模板；`id` 必须改成文件名 stem | 是 |
| `<UTC 时间>Z-<claim>.json` | 每次验证 1 条摘要，1–3KB，不含大产物 | 是 |
| 原始产物（xcresult / 日志 / trace） | 留在本机或 `harness/runs/`（已 gitignore） | **否** |

不写本机绝对路径、设备 UDID/CoreDevice ID、密钥。机器本地事实写 `AGENTS.local.md`（gitignore）。
**dirty 工作树生成的证据不能判 PASS**：正确顺序是 clean tree → 跑验证 → 生成证据 `/ 提交`；提交后证据里的 commit 变成新 HEAD 的祖先，仍可复核。

## 2. 命名与 id

- 文件名 = `<UTC 时间>Z-<claim>.json`，例：`20261105T052500Z-unit-tests-pass.json`。
- `id` 必须等于文件名 stem；`createdAt` 是同一时刻的 UTC RFC3339。
- 生成工具自动填 `id/createdAt/git/verifier`，不要手改。

## 3. claim 类型与判定规则

三值：`PASS`（exit 0）/ `FAIL`（exit 1）/ `UNVERIFIED`（exit 2，**证据不足，不算通过**）。

| claim | 含义 | verify-claim 校验（摘要） |
| --- | --- | --- |
| `unit-tests-pass` | 模拟器单元（`make test`） | passed ≥ baseline.unit.floor；failed=0；skipped=0；commit 合法且 dirty=false；xcresult 存在，否则 UNVERIFIED |
| `ui-tests-pass` | UI 测试（模拟器或真机） | passed ≥ baseline.ui.floor；simulator 环境 expected skipped=1，device 环境=0；其余同上 |
| `device-tests-pass` | 真机全套（预热+单元+UI） | passed ≥ unit.floor+ui.floor；skipped=0（真机白名单）；其余同上 |
| `docs-pass` | 文档门禁 | 复跑 `tools/check-docs.py`，exit 0 → PASS |
| `arch-pass` | 架构铁律 R1–R6 | 复跑 `tools/check-arch.py`，exit 0 → PASS |
| `perf-measurement` / `perf-no-regression` / `perf-improved` | 启动性能测量 | metrics 文件存在；context 的 commit/build 与证据一致；n≥10；CV≤10%；否则 UNVERIFIED |

> 性能 `PASS` 只表示**测量可用 + context 一致**；A/B 显著性与最小效应属后续阶段，不要拿本 PASS 当"更快了"的证明。

## 4. 生成

真机与测量自动写（推荐）：

```bash
make device-test          # 成功后自动写 harness/evidence/<UTC>-device-tests-pass.json
harness/tools/measure-launch.sh 10
```

其他验证手工写（示例，命令按实际改动替换）：

```bash
python3 tools/evidence.py write \
  --claim unit-tests-pass --status SUCCEEDED --passed 120 --failed 0 --skipped 0 \
  --duration 42.5 --xcode "Xcode 27.1" --simulator "iOS 26.4.1" --build Debug \
  --command "make test" --xcresult <xcresult 路径或 ~/…>
```

`--from-json -` 可读 stdin；设备脚本即为"草稿 JSON → `write --from-json`"两段式。
写入前会按 schema 校验；失败 exit 1 且不落盘。

## 5. 校验

```bash
python3 tools/evidence.py ls                 # = make evidence
python3 tools/evidence.py show <id|路径>     # 查看单条
python3 tools/evidence.py validate           # = make check-evidence
make test-tools                              # evidence / verify-claim 工具单测

python3 tools/verify-claim.py <证据路径>     # = make verify-claim CLAIM=<路径>
python3 tools/verify-claim.py --all          # = make verify-claim（缺省 --all）
```

输出固定格式：`CLAIM <id>: PASS|FAIL|UNVERIFIED — <原因>`。
`make verify-static` 已包含 `check-evidence` + `test-tools`（无需手跑）。

## 6. 何时必须写证据

- 任何「已完成 / 已修复 / 测试通过 / 真机验证 / 性能没退化」声明之前。
- 计划「验证证据」表必须引用 evidence id（表列：命令 | 结果 | 环境 | 证据 ID）。
- 环境不可用（无 Xcode / 无设备）→ 不写 PASS 证据，写「未验证 + 手动步骤」；可用 `make doctor` 说明环境原因。

## 7. 限制（诚实声明）

- 提高撒谎成本 ≠ 绝对防伪：evidence JSON 可被伪造；但 commit 祖先校验、计数、xcresult/metrics 存在性、CI 复跑静态门禁会显著提高成本。
- 行为质量（翻译/听写正确性、UI 手感）本目录无法自动判定；夹具 eval 就绪前，此类声明一律 UNVERIFIED。
- `harness/runs/` 保持 gitignore：入库的是摘要；xcresult/metrics 路径跨机器不可达时，verify-claim 正确地判 UNVERIFIED，而不是绿。
