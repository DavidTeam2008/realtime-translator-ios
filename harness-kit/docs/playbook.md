# 采用 playbook：五步改造法

> 给宿主项目做一次 harness 改造的操作手册。每步给出**命令**、**可检查的输出/退出信号**与**回滚点**。
> 前置约定与完整契约见 [`../README.md`](../README.md) 与 [`../SPEC.md`](../SPEC.md)；本文只讲怎么落地。

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
| 有真实仓库、需要计划/证据/CI 防盗绿 | `standard`（推荐默认） |
| 长期维护、发布前要强门禁与红队、多 Agent 适配 | `strict` |

```bash
python3 harness-kit/scripts/harness-init --profile standard --target ../myapp --name MyApp --dry-run
```

**退出信号**：`--dry-run` exit 0，并打印 `CREATE / SKIP / CONFLICT / RENDER` 计划；不写文件、不跑检查。先读一遍计划再执行。

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

# 3a) 先提交 scaffold（证据写入要求 clean tree）
git add -A && git commit -m "harness scaffold"
#    然后新建计划：填必填节 + 提交（草稿未填/未提交时 make check 红是预期）
make plan TOPIC=<topic>        # 补目标/验收/下一步/scope.allow 后提交

# 3b) 跑真实测试 → 写证据（证据要求 clean tree；claim 定义在 harness/config.json）
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

- 证据是**可被反驳的对象**：test-count 类 claim 由基线（`harness/test-baseline.json`）约束门槛与 skip；static 类 claim 复跑静态脚本。
- **kit 不解析测试输出**：`passed/failed/skipped` 要由宿主写进 evidence 草稿（如 `swift test` 的 `Executed N test`、`node --test` 的 `# pass N`）；不同测试框架的计数口径以宿主为准。
- 伪造不可行：`write` 要求 clean tree，证据绑定 git commit；`verify-claim --fresh` 会比较证据 commit 与工作树，`--strict` 下 STALE/缺失一律不能判 PASS。

**退出信号**：`verify_claim --all`：全 PASS → 0；任一 FAIL → 1；否则任一 UNVERIFIED → 2（exit 2 不是通过）。strict 档发布前用 `make release-check` 收口。

## 常见坑

1. **占位符未替换**：渲染后残留 `{{...}}` 会让门禁或后续工具失败——第 4 步用 `grep -rn "{{"` 兜底。
2. **测试命令不存在**：`commands.test` 写了项目里跑不通的命令，证据永远写不出来；先在宿主仓库手动跑通再写入配置。
3. **AGENTS 超预算**：规则越加越多会顶格；按“目录页 ≤200 行”收敛，细节下沉 `references/` 或嵌套 AGENTS。
4. **`§` 引用错节号**：引用 `§6` 但目标文件没有 `## 6.` 标题 → `check_agents` 报错；改引用或补标题，不要删校验。
5. **伪造证据不可行也不划算**：无产物/命令记录、dirty tree、commit 不可达都会被判 FAIL/UNVERIFIED；如实写“未验证 + 手动步骤”。
6. **别把 kit 文件当产品代码**：生成物是研发流程约束（规则/门禁/证据），不要 import 进业务运行时，也不要让 CI 依赖宿主语言之外的解释器。
7. **新建计划草稿会让 `make check` 变红**：`make plan` 生成的是待填草稿；先补「目标/验收/下一步/scope.allow」并删掉占位符，或删除草稿，再继续。

## profile 升级路径

- **升级 = 在已接入目录上再 init 更高档**：先 `--dry-run` 对比新增文件/冲突，再执行；已有文件默认 CONFLICT。
- `--force` 会备份后覆盖同名文件——逐项 `difftool` 复核差异，尤其是 `AGENTS.md`、`Makefile.harness`、`harness/config.json`。
- Makefile 升级：用更高档模板生成的 `Makefile.harness` 替换旧文件（已有宿主 `Makefile` 保持不变，仍通过 `include` 接入）。
- 该升级流程**尚未在真实项目上验证**（SPEC 未定义专用迁移命令）；按 dry-run 计划人工合并，并在计划里记录实际卡点。

## 如何验证接入成功（期望退出码与本机限制）

| 命令 | 期望 | 说明 |
| --- | --- | --- |
| `make check` | 0 | minimal 即 docs+agents；standard 含 plan；strict 含 adapters-check |
| `make verify-static` | 0 | standard/strict 含证据校验；失败先修证据/静态项 |
| `python3 tools/verify_claim.py --all` | 0（全 PASS）/1（有 FAIL）/2（有 UNVERIFIED） | exit 2 不是通过；逐条看 `CLAIM <id>:` 原因 |
| `make release-check` | 0（fresh 证据）/2（无证据或 STALE）/1（有 FAIL） | 仅 strict；要求证据 fresh 且 strict。**刚接入无证据时 exit 2 属预期** |
| `make doctor` | 0（OK/WARN）/2（缺必需项） | strict：python3/git/测试命令可执行性检查 |
| `make adapters-check` | 0（一致）/1（漂移） | strict：skills 单源同步后应一致 |

**本机限制**：静态门禁只需要 Python 3 + make + git，不联网、不需要宿主语言工具链；测试类 claim 需要宿主自己的构建/测试环境，kit 不代跑、也无法在无该环境的机器上验证——环境不满足时写“未验证”，不要把环境失败记成代码失败。

## 最小验收清单（勾完再算接入完成）

- [ ] `git status` 干净，init 产物已 review（无占位符、无密钥/本机路径）
- [ ] `make check` exit 0
- [ ] standard+：`make verify-static` exit 0
- [ ] standard+：`make plan TOPIC=<topic>` 能建计划，计划模板的必填节齐全
- [ ] standard+：真实测试跑通并把 evidence 写入 `harness/evidence/`，`verify_claim --all` 为 0
- [ ] strict：`make release-check` 在 fresh 证据下 exit 0；`make adapters-check` exit 0
- [ ] 计划/handoff 记录：实际卡点、未验证项、下一步（供下一位维护者恢复）
