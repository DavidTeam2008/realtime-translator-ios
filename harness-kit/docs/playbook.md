# 采用 playbook：五步改造法（Harness Engineering 五子系统落地）

> 给宿主项目做一次 Harness Engineering 改造的操作手册：按 Instructions / State / Verification / Scope / Session Lifecycle 五子系统落地。每步给出**命令**、**可检查的输出/退出信号**与**回滚点**。
> 前置约定与完整契约见 [`../README.md`](../README.md) 与 [`../SPEC.md`](../SPEC.md)；按读者选择路径：[`adoption.md`](adoption.md)（skill 优先接入与日常使用 + 命令行手动接入 + 前后评分）、本文（逐步操作）、[`governance.md`](governance.md)（演化、反臃肿、多人协作）、[`agent-prompts.md`](agent-prompts.md)（兜底提示词库，仅不支持 skills 的宿主用）。

## 0. 完成定义（先对齐，避免“看起来接入了”）

| profile | 接入完成的最低判据 |
| --- | --- |
| `minimal` | `make check` exit 0 |
| `standard` | `make check` exit 0 且 `make verify-static` exit 0 |
| `strict` | 以上 + `make adapters-check` exit 0 + `make release-check` 在**有 fresh 证据**时 exit 0 |

> 首次接入时仓库里通常还没有证据；`release-check` 在造出证据前**不可能为 0**，这不算失败（见 §5）。

## 第 1 步：盘点（只读，不改文件）

```bash
cd /path/to/your-repo
git status --short                    # 必须是干净的；有未提交改动先处理
ls -1                                 # 先看是否已有 AGENTS.md / Makefile / docs/
git ls-files '*.md' | wc -l           # 现有文档量（决定预算与是否需要裁剪）
test -f Makefile && echo "有 Makefile（init 会写 Makefile.harness 而不是覆盖）"
```

**退出信号**：以上全部只读命令应 exit 0；`git status` 为空。若工作区不干净，先提交或 stash，**不要**在脏树上 init（备份+覆盖会放大风险）。

## 第 2 步：选 profile（先 dry-run 看差异）

| 你的情况 | 选择 |
| --- | --- |
| 只要规则与文档门禁、还没有稳定测试 | `minimal` |
| 有真实仓库、需要计划/证据/CI 防盗绿 | `standard`（**存量仓库默认**） |
| 长期维护、发布前要强门禁与红队、多 Agent 适配 | `strict`（**仅显式选择并写明理由**；默认不升） |

```bash
python3 harness-kit/scripts/harness-init --profile standard --target ../myapp --name MyApp --dry-run
```

**退出信号**：`--dry-run` exit 0，并按动作打印 `RENDER / COPY / APPEND / CONFLICT` 计划；不写文件、不跑检查。先读一遍计划再执行。

## 第 3 步：init（写文件并跑首次检查）

```bash
python3 harness-kit/scripts/harness-init --profile standard --target ../myapp --name MyApp
```

- 非 `--dry-run` 时，写完会在目标目录执行 `make check` 并**透传其退出码**；加 `--no-check` 可先跳过。
- 已有驱动文件默认不覆盖：目标已有 `Makefile` → 写 `Makefile.harness`，按提示在原 Makefile 末尾加 `include Makefile.harness`（该情况下首次检查由 init 用 `make -f Makefile.harness check` 执行）。
- 冲突默认 `fail` 并列出文件；确认要覆盖时用 `--force`（先备份到 `<target>/.harness-init-backup/<UTC>/`）。
- 重复 init 不会重复追加 `.gitignore`；冲突而非静默覆盖是预期行为。

**退出信号**：init 的退出码约定（见脚本 header）= `0` 成功；`1` 用法/配置/冲突（写文件前失败）；其他非 0 = 首次 `make check` 失败（文件已写入）。`--no-check` 时成功只代表“文件已生成”。失败可回滚：`git checkout -- .` + 删除本次新增的未跟踪产物（或直接删除新增的 `harness/`、`docs/` 等目录，先看 diff）。

## 第 4 步：确认规则与真实命令（让门禁对得起你的项目）

```bash
# 1) 确认真实测试命令：init 会按 --language 自动推断并在 stdout 打 NOTE；
#    与项目不符时再改，或 init 时用 --test-command 显式指定（不要为了“填”而改对的值）
grep -n '"test"' harness/config.json       # 与项目真实命令对照

# 2) 检查没有遗留占位符（渲染后不得出现 {{）
grep -rn "{{" AGENTS.md HARNESS.md CONTRIBUTING.md docs/ references/ harness/ 2>/dev/null || echo "OK 无残留"

# 3) 按项目实际调整预算/白名单后自检
python3 tools/check_agents.py        # 指令层：预算/§ 引用/敏感串
python3 tools/check_docs.py          # 文档：链接/围栏/索引/白名单
```

**退出信号**：两个脚本均 exit 0。超预算先删重复、不删有效规则；`§` 引用报错时改节号或补目标标题；敏感串命中（如本机路径、密钥样式）必须清掉，不要加白名单绕过。

## 第 5 步：接入 CI / hooks / 证据链

```bash
# 1) 本地 push 前门禁（standard+ 的 githooks 适配器；也可手装）
git config core.hooksPath .githooks

# 2) CI：认领生成的 .github/workflows/verify.yml（静态门禁；昂贵测试按项目另行分层）

# 2b) 发布源码包/镜像时排除 harness 过程文件（可选）：init 加 --adapters gitattributes
#     生成 .gitattributes 的 export-ignore 块；npm/Docker/Xcode 做法见 adoption §3.5

# 3a) 先提交 scaffold（证据写入要求 clean tree）
git add -A && git commit -m "harness scaffold"
#    然后新建计划：填必填节 + 提交（草稿未填/未提交时 make check 红是预期）
make plan TOPIC=<topic>        # 补目标/验收/下一步/scope.allow 后提交

# 3b) 跑真实测试 → 生成 JUnit XML → evidence_from_junit → evidence.py write（clean tree；claim 定义在 harness/config.json）
<你的测试命令>
cat > /tmp/evidence-draft.json <<'JSON'
{
  "schemaVersion": 1,
  "claim": "tests-pass",
  "command": "<你的测试命令>",
  "environment": {"project": "<项目名>", "toolchain": "<语言/版本>", "os": "<OS>"},
  "result": {"status": "SUCCEEDED", "passed": 1, "failed": 0, "skipped": 0, "durationSec": 0.0},
  "verdict": "PASS",
  "verifier": "manual"
}
JSON
python3 tools/evidence.py write --from-json /tmp/evidence-draft.json

# 4) 三值判定
python3 tools/verify_claim.py --all
```

- 证据是**可被反驳的对象**：test-count 类 claim 由基线（`harness/test-baseline.json`）约束门槛与 skip，并要求 JUnit XML artifact 可重算；static 类 claim 复跑静态脚本。
- **kit 不解析测试输出**：`passed/failed/skipped` 要由宿主写进 evidence 草稿（如 `swift test` 的 `Executed N test`、`node --test` 的 `# pass N`）；不同测试框架的计数口径以宿主为准。
- 伪造成本被抬高：`write` 要求 clean tree，证据绑定 git commit；`verify-claim` 复核 commit 祖先/dirty，并从 JUnit XML 重算 counts（与自报不一致→FAIL）；`--fresh` 再比较证据 commit 与工作树。**不承诺绝对防伪**（能写仓库的人仍可伪造），但矛盾/无产物会被拒绝。

**退出信号**：`verify_claim --all`：全 PASS → 0；任一 FAIL → 1；否则任一 UNVERIFIED → 2（exit 2 不是通过）。strict 档发布前用 `make release-check` 收口。

## 存量项目（brownfield）改造：七步法

> 五步法面向空白/新项目；已有文档、测试与构建历史的仓库用本七步法：先只读盘点，再接骨架、蒸馏文档、清卫生、接传感器，最后做冷启动首访验收。
> 完成定义：七步完成 + `make check` exit 0 + 首访 5 问可答；strict 另需 `make release-check` 在 fresh 证据下 exit 0。
> 通用回滚原则：动手前 `git status` 干净；逐批 `commit`；删除/移动用 `git mv` 保留历史；不干净不操作。

### ① 只读盘点（不改目标）

```bash
python3 harness-kit/scripts/harness-adopt --target ../legacy-app
python3 harness-kit/scripts/harness-adopt --target ../legacy-app --report ../harness-adoption-report.md
python3 harness-kit/scripts/harness-adopt --target ../legacy-app --json   # 机器可读
```

- 关注：语言/构建探测、文档索引缺口与断链、被跟踪构建产物、绝对符号链接、本机路径、大文件；以及 v0.5.2 新增的**接入诊断**：根 AGENTS 是否超预算、当前分支 vs 仓库默认分支、测试命令的「可执行探测」（只跑 `--version`，**不等于**已验证）、按语言判定的 `.gitignore` 缺失项。
- 报告末尾的「下一步」会直接给出带入 init 的 flags（`--default-branch` / `--agents-mode move` / `--install-hooks`），照抄即可。
- 退出信号：exit 0 = 盘点完成；exit 1 = 用法错误/目标不存在。默认 0 写入（只有 `--report` 写你指定文件）。
- 回滚：删除报告文件即可。

### ② 基线测试与证据

```bash
cd ../legacy-app && git status --short    # 必须干净
<现有测试命令>                            # 记录命令 / 结果 / 环境
```

- 退出信号：现有测试能跑通；跑不通先修，或在计划里写“未验证 + 手动步骤”，不要带着坏基线改造。
- 回滚：无写入；把基线记录进计划的「验证证据」表（后续改造前后可对比）。

### ③ scaffold（`harness-init`，不碰既有文档）

```bash
python3 harness-kit/scripts/harness-init --profile standard --target ../legacy-app --dry-run \
  --test-command "<宿主实跑通过的测试命令>" --default-branch main \
  --agents-mode move --install-hooks
python3 harness-kit/scripts/harness-init ...   # 复核 dry-run 后去掉 --dry-run 执行
```

- 约束：init 对已存在文件默认 `CONFLICT` 不覆盖；目标已有 `Makefile` 时写 `Makefile.harness`（不改原文件）。
- `--agents-mode`：`replace`（无 AGENTS 时生成模板）/ `keep`（保留现有，预算门禁可能红）/ `move`（`git mv` 到 `docs/legacy-agents.md`，保留历史并自动登记 config 白名单 + docs 索引）。存量 AGENTS 超预算时用 `move`。
- `--default-branch`：在 feature 分支接入时必填（默认探测 `origin/HEAD`），否则 CI 会锁死在 feature 分支。
- `--install-hooks`：直接设置 `core.hooksPath=.githooks`；不加时 init 会明确 WARN「pre-push 未生效」。
- 含双引号/反斜杠的 `--test-command` 会自动 JSON 转义并在写盘前回读校验（K01）。
- init 后可生成改造计划草稿：`python3 harness-kit/scripts/harness-adopt --target ../legacy-app --write-plan`（输出 `<target>/harness/plans/<DATE>-adopt-harness.md`，已存在则拒绝覆盖；需 `harness/plans/` 已存在）。
- 退出信号：0 = 生成并首次 `make check` 通过；1 = 用法/冲突；其他非 0 = 首次 check 失败（按提示修）。
- 回滚：先读 dry-run 计划；失败时删除本次新增的未跟踪文件/目录，或 `git checkout -- .`（`--force` 会先备份）。

### ④ 文档蒸馏（当前 docs 重写 + 原文归档）

```bash
mkdir -p docs/_archive
git mv docs/old-design.md docs/_archive/old-design.md    # 原文留档，git 历史可查
# 只保留现行文档并重写 docs/README.md 索引；归档区不参与 check_docs
python3 tools/check_docs.py
```

- 规则：`docs/_archive/` 是归档区（`check_docs` 跳过 `_archive`）；索引只列现行文档；同一事实只留一个真源。
- 退出信号：`check_docs.py` exit 0（链接/围栏/索引/白名单/预算全过）。
- 回滚：`git mv` 反向 + 恢复索引行；按批 commit。

### ⑤ 清洁批次（版本库卫生）

```bash
git ls-files | grep -E '(^|/)(build|dist|DerivedData|\.cache)/' || true   # 被跟踪构建产物
git ls-files -s | awk '$1=="120000"'                                       # 符号链接
git grep -nE '/(Users|home|Volumes)/|[A-Fa-f0-9]{8}-[A-Fa-f0-9]{4}-' || true   # 本机路径 / ID 样本
```

- 规则：逐批处理（死代码 → 构建产物 → 符号链接 → 本机路径），每批一个 commit，并补 `.gitignore`。
- 退出信号：以上命令无残留，或全部记录在计划；`make check` 仍为 0。
- 回滚：逐批 `git revert` / `git checkout`；不要一次性大清理。

### ⑥ 宿主传感器（分层 / 卫生 / docmap / 负向注入）

```bash
make check && make verify-static            # standard+ 的 verify-static 已含 check-host
python3 tools/check_docs.py && python3 tools/check_agents.py && python3 tools/check_plan.py check
python3 tools/check_hygiene.py              # 可选：卫生门禁（config 缺 hygiene 段 → SKIP）
python3 tools/check_layers.py               # 可选：分层门禁（config 缺 layers 段 → SKIP）
# 负向注入自测：对目标仓的临时副本注入，断言门禁真的会红、恢复后复核全绿（默认不写目标仓）
python3 harness-kit/scripts/harness-selftest --target ../legacy-app
# 手工负向注入备用：删一条索引行 / 写错 § 号 / 造敏感串 / 超预算 → 确认对应 sensor 变红 → 恢复
```

- `check-host` 由 `check_hygiene.py` + `check_layers.py` 组成，只读 `harness/config.json` 的可选 `hygiene` / `layers` 段；**未配置时 SKIP（不算覆盖）**，要在配置里写明构建产物、根文件白名单、本机路径模式与分层规则后再验收。
- `harness-selftest`：exit 0=所有注入都被对应门禁拦截且恢复后全绿；1=有门禁未按预期变红（门禁空转，先修门禁本身）；2=目标仓脏或 baseline 本身红（先清理/修好再测）。`--keep` 可保留临时副本排查。
- 退出信号：正向全 0，且负向注入时按预期非 0（每项记录「注入前 / 注入后 / 恢复后」exit；selftest 输出表格即证据）。
- 回滚：`git checkout -- <file>` 恢复注入改动；负向注入必须在干净工作树上做。

### ⑦ 接入后收口（归档 / 评分卡 / 自检 / waiver）

- 归档只读盘点报告：`python3 harness-kit/scripts/harness-adopt --target . --archive-report <报告路径>`（只复制到 `harness/reports/adoption-<YYYY-MM-DD>.md`，拒绝覆盖，不重扫）。
- 生成评分卡草稿：`make scorecard`（`harness/reviews/<date>-scorecard.md`；自评 / 独立复评分列）。
- 负向注入自检：`make selftest`（证明门禁会红；需要 clean tree）。
- 完成前统一跑 `make verify-all`（= `verify-static` + `verify-claim`；standard/strict）；`verify-static` 只覆盖静态门禁，**不含**证据三值判定。
- 未验证项清零，或写计划「未验证豁免」表（理由 / 负责人 / 到期日）后归档。

### ⑧ 冷启动首访验收

- 让未参与改造的人（或新会话）只按 README → `docs/README.md` 走：回答 5 问（是什么 / 为什么值得看 / 怎么跑 / 怎么验证 / 怎么复制 harness），并跑 `make check`。
- 退出信号：5 问可答、命令 exit 0；卡点列表写入计划的「未验证项 / 下一步」。
- 回滚：只读验收，无代码回滚；卡点回写文档或开 issue。

### 存量项目常见坑

1. **双真源**：旧交接文档/设计稿与 docs 并存 → 先定唯一真源，其余归档并在原处留指针。
2. **历史文档误当现状**：带日期的报告是当时口径，不改数字；现行结论重写进规范文档。
3. **构建缓存入库**：`build/`、`DerivedData/`、`.cache/` 被跟踪会让证据写入因 dirty tree 失败；先出库 + `.gitignore`。
4. **本机路径泄漏**：home 目录路径、设备 ID、Team 不要入库；`check_agents.py` 扫到即清，不要加白名单绕过。
5. **升级没有 in-place 命令**：版本升级与 profile 升级都是「临时渲染新版 → 逐文件 diff → 人工合并」；版本升级已在 Android/Gradle 存量仓验证（v0.2.2→v0.2.3），profile 升级（minimal→standard→strict）仍未验证。
6. **profile 选择**：统一口径——存量仓库**默认 `standard`**（计划 + 证据 + CI）；`minimal` 只适合先立规则；`strict`（adapters / red-team / release-check）必须由用户**显式选择并写清理由**，报告里的备选不自动采用。
7. **存量 AGENTS 超预算**：模板已瘦身（约 730 tokens / 预算 1200），但老仓 AGENTS 仍可能数倍于预算；用 `--agents-mode move` 迁移并保留历史，不要直接调高预算或删规则了事。
8. **首次证据死锁**：JUnit artifact 天然让工作树 dirty；v0.5.2 起证据目录下的待提交产物默认豁免（WARN），其他目录用 `--allow-untracked-under`。不要长期靠 `.git/info/exclude` 绕过且不记录。
9. **自动探测不是验证**：adopt 的 `--version` 探测只证明程序存在；测试命令必须在宿主实跑，Node 24 的 `node --test` 对无扩展名 TS 相对导入会 `ERR_MODULE_NOT_FOUND`，优先 `tsx --test` / 项目 `scripts.test`。
10. **仓库当前分支≠默认分支**：在 feature 分支接入后，merge 到 main 的 CI 可能不再触发；init 会探测 `origin/HEAD`，接入后用 `python3 tools/harness.py status` 检查 manifest 分支漂移。

## 常见坑

1. **占位符未替换**：渲染后残留 `{{...}}` 会让门禁或后续工具失败——第 4 步用 `grep -rn "{{"` 兜底。
2. **测试命令不存在**：`commands.test` 写了项目里跑不通的命令，证据永远写不出来；先在宿主仓库手动跑通再写入配置。
3. **AGENTS 超预算**：规则越加越多会顶格；按“目录页 ≤200 行”收敛，细节下沉 `references/` 或嵌套 AGENTS。
4. **`§` 引用错节号**：引用 `§6` 但目标文件没有 `## 6.` 标题 → `check_agents` 报错；改引用或补标题，不要删校验。
5. **伪造证据会被门禁抓住**：counts 与 JUnit XML 不一致、无产物、dirty tree、commit 不可达都会判 FAIL/UNVERIFIED；如实写“未验证 + 手动步骤”。
6. **别把 kit 文件当产品代码**：生成物是研发流程约束（规则/门禁/证据），不要 import 进业务运行时，也不要让 CI 依赖宿主语言之外的解释器。
7. **新建计划草稿会让 `make check` 变红**：`make plan` 生成的是待填草稿；先补「目标/验收/下一步/scope.allow」并删掉占位符，或删除草稿，再继续。

## 日常循环（v0.3.0-alpha.1 起）

Agent 侧装一次入口 skill（`<kit>/scripts/harness-skill install --scope user`）后按意图直接触发；下面是与人共用的同一条链（命令行等价动作，不依赖提示词复制）：

1. `make status`（或 `python3 tools/harness.py status`）——一屏状态 + 建议下一步；冷启动第一命令。
2. `make start TOPIC=<topic> GOAL="<目标>" SCOPE="src/ ..."`——幂等建 active 计划；建完 `make check` 即绿（未提交段差异只告警）。有需求卡时用 `python3 tools/harness.py intake --file <卡>`（机检验收判据，模糊判据会被拒绝）。
3. 实现；`make check` 日常门禁。
4. 完成前 `python3 tools/harness.py verify`——自动同步计划「未提交改动」段 → `make verify-static` → 计划严格校验 → 证据三值摘要；`--claims-strict` 可把 UNVERIFIED/FAIL 计入门禁。
5. 发布前 `python3 tools/harness.py release --check`（静态门禁 + fresh 证据；strict 档 `--strict`；证据 UNVERIFIED 不算通过）。
6. 交接/中断 `python3 tools/harness.py handoff`（`--json` 可机读）。

> 入口 skill（默认）：用户级 `install --scope user`（写 `~/.agents/skills/harness/` 与 `~/.claude/skills/harness/`，一次安装所有仓库会话可见；升级 kit 后 `--force` 重装）；需要团队 pin 版本时 `--scope project` 装到 `.dsh/skills/` / `.agents/skills/` / `.claude/skills/` 并提交。支持斜杠的宿主优先输入 `/harness` 显式加载（DSH / Qoder CN / Claude Code 有「技能」补全），自然语言点名是兜底。行为级 A/B 后置（v0.5.x），skill 只做入口路由。

> 严格校验在 `check-plan-strict` / `verify-static` / CI；计划未提交段不再需要手抄，`verify`/`handoff` 会按 `git status` 重写。
>
> 接入后基线/自检：`make scorecard`（评分卡草稿，过期由 `make check` WARN）、`make selftest`（负向注入）、`make upgrade-check KIT_ROOT=<kit>`（只读升级检查）。

## 升级路径

### 版本升级（v0.2.13 起：先 check/plan，再人工应用）

kit 不提供 in-place 迁移命令；对已接入仓直接再 init 只会全 CONFLICT（还可能想写 `Makefile.harness`，与既有宿主 `Makefile` 冲突）。v0.2.13 起先用只读工具拿到准确基线：

0. **检查基线与预览**（v0.2.13+，只读）：
   `python3 <kit>/scripts/harness-upgrade --target <target> --check`（in sync 0 / 本地漂移 1 / 版本不符 3）；
   `python3 <kit>/scripts/harness-upgrade --target <target> --plan`（三方 diff：SAME / LOCAL_ONLY / UPGRADE / ALREADY / CONFLICT / ADD / OBSOLETE / APPEND）。
   旧仓（v0.2.13 之前接入）没有 `.harness-manifest.json`：`--check` 会提示走手工路径，`--plan` 仍可渲染预览。
1. **临时渲染新版**（无 manifest 或需复核时）：`python3 harness-kit/scripts/harness-init --profile <档> --language <语言> --target /tmp/kit-render-<ver> --no-check`（需要目标版本 kit）。
2. **逐文件 diff**：`git diff --no-index <target>/<file> /tmp/kit-render-<ver>/<file>`；只回写 kit 管理面——`tools/`、`harness/config.json` 的 `kitVersion`/配置、Makefile 的 kit 目标段、CI/hook 模板。项目自有文档（AGENTS/CONTRIBUTING/README/docs/references）不回写。**CONFLICT 行必须人工合并，不要整文件覆盖**。
3. **配置迁移**：config schema 有变化时写映射（如 0.2.3 把宿主私有 `layers` 键映射为通用 `rules` + `symbolGuards`）；`kitVersion` 与 VERSION 对齐。
4. **复核**：`make verify-static`，再用 `python3 <kit>/scripts/harness-selftest --target .` 做负向注入——升级后门禁仍必须按预期变红，否则视为升级引入回归。升级后更新 `.harness-manifest.json` 的方式：以新版 kit 在临时目录 init 得到 manifest，按实际回写结果人工同步 files/append 哈希（`--apply` 仍未实现，计划在 v0.4.x）。
5. **记录**：升级计划写实际卡点、映射表、selftest 前后矩阵；有宿主 fork 的，升级后应删除 fork、只留配置差异。

**实测**：真实 Android/Gradle 存量仓 v0.2.2→v0.2.3：4 个宿主 fork 脚本换回上游、`layers`/`hygiene` 配置迁移、`static-gates` 证据落地；selftest 在升级前发现门禁模式被历史清洗成 `/local/`（M5/M8 失效），修复后 **8/8**。细节见该仓归档计划。

### v0.3.0 → v0.4.0 升级自检（行为变更，逐项处理）

v0.4.0 是**行为变更**版本：更严的审计与默认脱敏会让旧仓出现新的红/WARN。升级步骤同「版本升级」，
应用新版 kit 管理面后先跑 `make verify-static`，按下表逐项处理（不要为了变绿删检查或放宽配置）：

| 变更 | 旧仓预期 | 修复动作 |
| --- | --- | --- |
| `submitted` 每个 commit 按**提交时点** scope 审计（越界 FAIL；merge 只比第一父） | `check` 红；提交后补 allow 不再能洗白 | 收窄 scope，或补「提交范围例外」表（路径/理由/负责人/到期日）；历史 commit 早于计划文件时给 WARN（不可回溯，别靠它变绿） |
| 归档计划不再免检 | `status` 非 done/archived → **daily 也 FAIL**；归档 done 的内容问题：`make check` **WARN**，`check-plan-strict`/pre-push **FAIL** | 先修计划再归档；归档 done 问题补「未验证豁免」/「提交范围例外」后再跑 strict，不要当绿 |
| `done` 计划未验证项必须清零或有「未验证豁免」表 | `check` 红 | 清零未验证项，或补豁免表（理由≥5 字 / 负责人 / 到期日≤90 天；逐条覆盖） |
| 证据/artifact 需 git 跟踪；JUnit 默认脱敏并复制入库 | 未跟踪 PASS 证据 → `UNVERIFIED`；旧 artifact 路径 → WARN/重跑 | `git add harness/evidence`；用新版 `tools/evidence_from_junit.py` 重生成（默认脱敏；`--keep-raw` 仅显式逃生） |
| 归档证据 `SUPERSEDED` 只列出、不改退出码；但归档 FAIL/UNVERIFIED 必须被当前 PASS 证据 `supersedes` 合法接管，否则聚合 UNVERIFIED；归档计划可由 status/handoff 回读 | 旧仓可能有未接管的归档 UNVERIFIED → `verify-claim` exit 2 | 在当前 PASS 证据里加 `supersedes: [<归档id>]`（同 claim），或把归档证据归档理由写清；不要直接删文件 |
| `check_layers` 改 `git ls-files` + untracked、默认排除 `.venv`/`build` 等、规则 0 匹配 WARN | 旧 `layers` 配置可能扫到 `.venv` 或 `matched=0` WARN | 按新格式补 `exclude`；先修 `sourceRoot`/`pathPrefix`/`extensions`，再考虑 `--strict` |
| `scorecard` 进 standard；`make check` 对过期只 WARN | 无 scorecard → WARN（不阻断） | `make scorecard` 生成草稿；人工自评 / 独立复评；过期后重新生成 |
| 新 Makefile target：`selftest` / `upgrade-check` / `scorecard`；`check` 增加 `scorecard --check-stale` | 旧 `Makefile.harness` 缺 target → `make selftest` 失败 | 用新版 profile 重新渲染 Makefile（或手工同步 kit 目标段）；`make upgrade-check KIT_ROOT=<kit>` 看差异 |
| 新 profile 安装项：`tools/scorecard.py`、`tools/harness_selftest`、`docs/harness-scorecard.md`；`check-plan-strict` 改用 `--strict` | 旧 standard 仓缺这些文件时 `detect_target_stage` 判 partial；`make check` 可能因缺 `tools/scorecard.py` 失败 | 按「版本升级」回写 kit 管理面文件；`harness-prompt list --target .` 的 `targetStage` 应为 adopted |

升级后必须再跑一次 `python3 <kit>/scripts/harness-selftest --target .`：证明门禁仍会红；
selftest 矩阵异常（SKIP≠PASS）时先修门禁，不要发布。

### v0.4.0 → v0.5.0 升级自检（入口变化，门禁无行为变更）

v0.5.0 只改**入口与文档**：`tools/`、门禁、证据判定、`config` schema 均不变，旧仓的 `make check` / `make verify-static` 结果不变。要做的只有：

| 变更 | 旧仓预期 | 修复动作 |
| --- | --- | --- |
| 默认入口改为入口 skill（一次用户级安装，跨仓生效） | 无强制影响；旧提示词流程仍可用（降级为兜底） | `python3 <kit>/scripts/harness-skill install --scope user`；`check --scope user` 应 in sync |
| `harness-skill` 新增 `--scope user/project`、`uninstall`、`agents` 目标 | 项目级旧安装仍可 `check`（`.dsh/skills`、`.claude/skills`） | 需要统一时 `install --scope project --force` 后提交；`check` 报漂移再跟进 |
| `harness-adopt` 多一行 skill 安装提示；`harness-prompt copy` 多一行 stderr 提示 | 无行为影响 | 无需处理 |
| `docs/agent-prompts.md` 改为「兜底入口」定位 | 无行为影响 | 无需处理 |

升级后 `make selftest` 预期不变（M1–M9）。行为级 A/B 未执行前，不要对外声称 skill 提升了 Agent 表现。

### profile 升级（仍未验证）

- **升级 = 在已接入目录上再 init 更高档**：先 `--dry-run` 对比新增文件/冲突，再执行；已有文件默认 CONFLICT。
- `--force` 会备份后覆盖同名文件——逐项 `difftool` 复核差异，尤其是 `AGENTS.md`、`Makefile.harness`、`harness/config.json`。
- Makefile 升级：用更高档模板生成的 `Makefile.harness` 替换旧文件（已有宿主 `Makefile` 保持不变，仍通过 `include` 接入）。
- 该路径**尚未在真实项目上验证**（SPEC 未定义专用迁移命令）；按 dry-run 计划人工合并，并在计划里记录实际卡点。

## 如何验证接入成功（期望退出码与本机限制）

| 命令 | 期望 | 说明 |
| --- | --- | --- |
| `make check` | 0 | minimal 即 docs+agents；standard 含 plan；strict 含 adapters-check |
| `make verify-static` | 0 | standard/strict 含证据校验；失败先修证据/静态项 |
| `python3 tools/verify_claim.py --all` | 0（全 PASS）/1（有 FAIL）/2（有 UNVERIFIED） | exit 2 不是通过；逐条看 `CLAIM <id>:` 原因 |
| `make release-check` | 0（fresh 证据）/2（无证据或 STALE）/1（有 FAIL） | 仅 strict；要求证据 fresh 且 strict。**刚接入无证据时 exit 2 属预期** |
| `make doctor` | 0（OK/WARN）/2（缺必需项） | strict：python3/git/测试命令可执行性检查 |
| `make adapters-check` | 0（一致）/1（漂移） | strict：skills 单源同步后应一致 |
| `python3 <kit>/scripts/harness-skill check --scope user` | 0（in sync）/1（漂移）/2（未安装） | 入口 skill 用户级安装；升级 kit 后 `install --scope user --force` 重装 |
| `make scorecard` | 0 | 生成 `harness/reviews/<date>-scorecard.md` 草稿；自评/独立复评 TBD |
| `make check` 的 scorecard 提醒 | 0（WARN 不算失败） | 过期/缺失只 WARN；`--strict` 才 exit 1（发布门禁可用） |
| `make selftest` | 0（全拦截）/1（门禁空转）/2（环境或基线红） | 负向注入；SKIP ≠ PASS |

**本机限制**：静态门禁只需要 Python 3 + make + git，不联网、不需要宿主语言工具链；测试类 claim 需要宿主自己的构建/测试环境，kit 不代跑、也无法在无该环境的机器上验证——环境不满足时写“未验证”，不要把环境失败记成代码失败。

## 最小验收清单（勾完再算接入完成）

- [ ] `git status` 干净，init 产物已 review（无占位符、无密钥/本机路径）
- [ ] `make check` exit 0
- [ ] standard+：`make verify-static` exit 0
- [ ] standard+：`make plan TOPIC=<topic>` 能建计划，计划模板的必填节齐全
- [ ] standard+：真实测试跑通并把 evidence 写入 `harness/evidence/`，`verify_claim --all` 为 0
- [ ] Agent 入口：`harness-skill install --scope user` 已装，`check --scope user` exit 0（或宿主不支持 skills，确认兜底提示词流程可用）
- [ ] strict：`make release-check` 在 fresh 证据下 exit 0；`make adapters-check` exit 0
- [ ] 计划/handoff 记录：实际卡点、未验证项、下一步（供下一位维护者恢复）

> 实测（2026-11-11，Python/MySQL 存量仓）：升级 v0.4.0 后 `make check` 仍 PASS（归档问题为 WARN），
> `check-plan-strict` 暴露 4 个 submitted 越界文件与 3 条归档未验证项；补「未验证豁免」+「提交范围例外」+
> 当前证据 `supersedes` 后 strict 转 PASS（仍保留“计划晚于提交”的 WARN）。逐项证据见该仓的
> `harness/reports/` 与 kit 的 `harness/reviews/2026-11-11-adoption-feedback-v04/barra-validation.md`。
