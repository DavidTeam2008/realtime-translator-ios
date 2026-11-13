# 案例：fcnsystem 存量接入（v0.5.1 → kit v0.5.2 反哺）

> 案例类型：**brownfield（存量仓库）真实接入**，由接入方独立写反馈报告，kit 维护方逐条复盘并反哺。
> 目标仓：fcnsystem（Next.js 16 + React 19 + TypeScript + pnpm + MySQL 行情/产品库）。
> 接入方式：standard profile + `tools/harness.py` + `make` 门禁 + CI/pre-push 适配器。
> 反馈报告：接入方仓库内 `harness/reports/harness-kit-adoption-feedback.md`（本项目不外链，避免把宿主私有仓写进 kit）。
> 本文只记录**可复用的结论**：哪些坑必然遇到、kit 怎么修、哪些是宿主侧责任。

## 1. 接入结果

| 项 | 结果 |
| --- | --- |
| 落地文件 | 41 个（`tools/` 门禁、`harness/config.json`、计划/证据/评分卡、`Makefile`、`.github/workflows/verify.yml`、`.githooks/pre-push`、`references/`、`HARNESS.md`、根 `AGENTS.md`） |
| 门禁 | `make check` / `make verify-static` / `make verify-claim` / `make selftest` 全绿 |
| 测试与证据 | 4 个测试用例；2 条证据 PASS（`test-count` 从脱敏 JUnit 重算 + `static` 复跑） |
| 指令层迁移 | 原 `AGENTS.md` ≈6864 tokens（预算 1200）→ `git mv` 到 `docs/fcn-domain-notes.md`；新根入口 ≈1179 tokens |
| 业务代码 | 零改动（`src/`、`package.json` 未改） |
| 提交 | 接入提交 + 证据提交（已 push 到项目分支） |

## 2. 接入过程（时间顺序）

1. **只读盘点**：`harness-adopt` 扫描技术栈/测试命令/文档/CI，输出报告（dry-run 式透明）。
2. **dry-run → init**：standard + githooks + ci；34 个文件预演，落盘成功——但 `config.json` 需手工修（K01）。
3. **首次 `make check`**：6 篇文档未登记（项目侧修内容，非门禁问题）。
4. **AGENTS 冲突**：原文件远大于预算，只能自行决定迁移方式（K03）。
5. **测试命令**：盘点建议 `node --test`，实测报 `ERR_MODULE_NOT_FOUND`，换 `tsx --test` 后 4/4 通过（K04）。
6. **首轮 selftest**：工作树 dirty 被拒，提交后执行。
7. **证据闭环**：JUnit artifact 落进证据目录 → 工作树 dirty → `evidence.py write` 拒绝，用 `.git/info/exclude` 绕过（K02）。
8. **收口**：scorecard / verify / selftest 全绿。

## 3. 问题清单与 v0.5.2 处理

严重度：P1 = 阻断或高风险误导；P2 = 明显摩擦/文档不一致；P3 = 打磨项。
状态：**已修** = v0.5.2 代码/模板已改；**已核对** = 复核后确认现状已满足或非 kit 缺陷；**宿主侧** = 不属于 kit 保证。

| ID | 严重度 | 问题 | v0.5.2 处理 |
| --- | --- | --- | --- |
| K01 | P1 | `--test-command` 含双引号时模板直拼 → 非法 `config.json` | **已修**：JSON 上下文 `json.dumps` 转义；渲染后 `json.loads` 回读校验，init 阶段直接失败 |
| K02 | P1 | 首次证据死锁：artifact 脏树 → `write` 拒绝 | **已修**：证据目录默认豁免 + WARN；`--allow-untracked-under`；错误信息给 `git add` 解法；文档补两阶段说明 |
| K03 | P1 | 模板 AGENTS ≈1172 tokens / 预算 1200，存量必迁移 | **已修**：模板瘦身到约 730 tokens；`init --agents-mode replace\|keep\|move`；`move` 自动 `git mv` + 登记 config 白名单与 docs 索引；adopt 给出超预算诊断与迁移命令 |
| K04 | P1 | adopt「--version 探测」被报告写成「已验证命令」 | **已修**：改称「可执行探测（只跑 `--version`，不执行测试）」，JSON `smoke=not-run`；Node/TS 建议优先 tsx（`ERR_MODULE_NOT_FOUND` 提示） |
| K05 | P1 | CI 默认分支取当前分支（feature 接入后 CI 失联） | **已修**：默认分支探测 `origin/HEAD` → `init.defaultBranch` → 当前分支；`--default-branch` 覆盖；CI `pull_request` 不限分支 + `workflow_dispatch`；`status` 检测 manifest 分支漂移 |
| K06 | P2 | 未跟踪的新 `docs/README.md` 被误报缺失 | **已修**：磁盘存在即算有索引，JSON 区分 `hasIndexTracked` |
| K07 | P2 | 计划 bullet `- dir/：中文说明` 整句当路径 | **已修**：先按中/英文冒号切路径，再解析；回归用例 |
| K08 | P2 | `verify-static` 不含 `verify-claim`，可能假绿 | **已修**：`verify-static` 末尾显式提示未跑三值判定；新增 `verify-all = verify-static + verify-claim`（不把 claim 塞进 verify-static，保证 fresh init 可绿） |
| K09 | P2 | evidence README 示例缺 `--from-json` | **已修**：示例与 skill 同步为 `write --from-json` |
| K10 | P2 | githooks 只落文件不安装，静默失效 | **已修**：`init --install-hooks`；未安装时 summary 明确 WARN；`status` 检查 `core.hooksPath` |
| K11 | P2 | `.gitignore` 无条件追加 Python/Swift 条目且重复 | **已修**：按 `--language` 只追加相关条目 + 对已有行去重；adopt 的缺失项也按语言判定 |
| K12 | P3 | selftest 的 SKIP 语义易被误读 | **已核对**：`harness-selftest` 已支持 `--json` 与 `summary.notApplicable`（SKIP ≠ PASS） |
| K13 | P3 | 门禁运行产生 `__pycache__` | **已修**：Makefile 模板 `export PYTHONDONTWRITEBYTECODE := 1`；kit 侧测试命令同样禁用字节码 |
| K14 | P3 | 手工修 CI 分支后 manifest 仍记旧分支，无告警 | **已修**：`harness.py status` 比较 `manifest.options.branch` 与默认分支，不一致输出 `[WARN]` + 下一步 |
| K15 | P3 | `docs/harness-scorecard.md` 占位页与生成位置不一致 | **已修**：模板明确「本页是口径说明，不自动更新；草稿在 `harness/reviews/`」，`make scorecard` 帮助文本同步 |
| K16 | P2 | `git mv` 跨目录时源删除被判越界 | **已修**：scope 审计用 `--name-status -M`，rename 只审目标路径；普通删除仍审源路径（回归用例保护） |
| K17 | P1 | 非 ASCII 路径被 Git 转义，scope 审计误判越界 | **已修**：`check_plan` 的 `git diff`/`diff-tree` 改用 `-z`（接入方 PR 已并入）；本轮补 `verify_claim.changed_paths` 的 `-z` 与中文路径回归用例 |

## 4. 反哺后的行为变化（对已接入仓）

- 已接入仓**不会**自动获得 Makefile/模板改动：升级后按 playbook「版本升级」逐文件 diff，只回写 kit 管理面。
- `verify-static` 行为未变（仍不含证据判定），只是多了提示；想用完整入口可手工加 `verify-all` 目标。
- 旧仓若在 feature 分支接入且 manifest 记错分支：升级时用 `harness.py status` 的 WARN 定位，重跑 init `--default-branch` 或手工同步 workflow/manifest。
- 旧仓若曾用 `.git/info/exclude` 绕过证据锁：升级后可直接用新 `evidence.py`，建议把这类本地绕过记录进宿主的「已知本地配置」。
- 接入方反馈的后续问题（新的 K 编号）：按 v0.5.2 起的反馈通道回到上游——issue 走公开镜像仓（见 [adoption §3.6](../adoption.md#36-遇到-kit-问题反馈上游)），不要在宿主仓改 `tools/` 绕过。

## 5. 结论（可复用）

1. **存量接入的主要成本在「指令/文档迁移」与「真实测试命令」，不在脚手架本身**：kit 能做的是把迁移动作变成显式 flag + 诊断（--agents-mode、adopt 探测语义），而不是替用户猜。
2. **首次闭环必须一条命令能走通**：证据写入的 clean-tree 检查与「待提交产物」天然冲突，任何类似门禁都要先问“第一次怎么产生被检查的产物”。
3. **自动探测只能用弱证据命名**：`--version` 探测不是「已验证」，三值语义要从报告字段贯彻到文案。
4. **项目侧责任仍占大头**：文档登记、测试基线、Gitee/CI 平台差异、评分卡独立复评不由 kit 保证；kit 只保证结构性、可机检的部分。
5. **单样本不要外推**：本案例是 1 个项目、1 个技术栈、接入方视角；结论已写成可回归的用例，但“所有存量仓都会遇到同样问题”不成立。
6. **反馈要能回流**：接入方写 17 条反馈 → kit 修 17 条 → 案例与回归用例，这个闭环成立的前提是「宿主知道去哪反馈、附什么信息」。v0.5.2 起把反馈入口写进入口 skill、根 `AGENTS.md`、init summary 与 adopt 报告，避免问题止步于宿主侧绕过。

## 6. 复现方法（通用，不含宿主私有信息）

```bash
# 1) 只读盘点（0 写入）
<kit>/scripts/harness-adopt --target <repo> --report /tmp/adoption-report.md --json

# 2) 看报告里的 branch / AGENTS / testCommand / gitignore / docs 五项建议
python3 -m json.tool /tmp/adoption-report.json 2>/dev/null || true

# 3) dry-run 后 init（存量典型 flags）
<kit>/scripts/harness-init --profile standard --target <repo> \
  --test-command "<real test cmd>" --default-branch main \
  --agents-mode move --install-hooks --dry-run
```

验收：`make check` → 提交 scaffold → 跑真实测试并写证据 → `make verify-all` → `make selftest`。
