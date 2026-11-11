# v0.4.0 候选 · 真实接入仓只读复验（barra）

> 对象：`barra`（Python 3.12 / MySQL，standard 档，kit 0.3.0 接入；HEAD `bab9ac6`）
> 方式：新 kit 工具 + `--root` 只读运行；迁移修复在 `/tmp` 克隆上验证，**未修改真实仓库**
> 日期：2026-11-11；kit 候选：v0.4.0（本地工作树）

## 1. 修复前（新工具直接跑真实仓）

| 命令 | 结果 |
| --- | --- |
| `check_layers.py --root barra` | **PASS**：来源 git tracked；扫描 **171** 个 `.py`（tracked 171 / untracked 0），不再扫 `.venv` 的 6129 个；`core` 规则 eligible=171/matched=24、`portfolio` matched=3、0 违规 |
| `verify_claim.py --all --root barra` | **UNVERIFIED（exit 2）**：2 条当前证据 PASS；归档 `20261111T073858Z-tests-pass` 为 UNVERIFIED 且未被 `supersedes` 接管 → 明确输出不再静默 |
| `check_plan.py --root barra`（日常） | **PASS**：归档计划 12 条问题全部 WARN（含 `13a02f0` 改 `scripts/*`、`54ef607` 改 `.github/workflows/ci.yml` / `llms.txt`，以及 7 个 commit 早于计划文件） |
| `check_plan.py check --strict --root barra` | **FAIL**：上述归档问题升 FAIL（pre-push 会拦），证明「先归档再跑门禁」不再变绿 |
| `harness.py status`（/tmp 克隆，覆盖新 tools） | 无 active 计划时回读上一归档计划：标注「归档时点快照」、列出未验证项/下一步；`git.inSync=null`，不再输出「与计划声明一致」 |
| `harness.py handoff`（同） | 输出 `# handoff（无 active 计划；回读最近归档计划·历史快照）` + 未验证项 + 下一步，exit 0 |

## 2. 迁移路径实测（/tmp/barra-v04，一次性）

按 playbook「v0.3.0 → v0.4.0 升级自检」：

1. 当前 `tests-pass` 证据加 `"supersedes": ["20261111T073858Z-tests-pass"]`；
2. 归档计划补「未验证豁免」表（3 条未验证项，理由/负责人/到期日 +60 天）；
3. 补「提交范围例外」表（`scripts/preflight_storage.py`、`scripts/restore_registry_after_test_wipe_20260929.py`、`.github/workflows/ci.yml`、`llms.txt`，各带理由/负责人/到期日）。

结果：

| 命令 | 结果 |
| --- | --- |
| `verify_claim.py --all --root /tmp/barra-v04` | **PASS**：归档证据 `SUPERSEDED — 已被 20261111T100154Z-tests-pass 取代`，聚合 2 PASS |
| `check_plan.py check --strict --root /tmp/barra-v04` | **PASS**（0 error / 7 warn）：7 条 WARN 均为「commit 早于计划文件，用当前 scope 审计」——历史不可回溯，已明确标注而非伪造通过 |

结论：v0.4.0 的「可见 WARN → strict 可修通」迁移路径在真实仓成立；新仓（计划先于提交）不会出现该
WARN，可用 `check_plan --strict` 直接阻断「提交后再放宽 scope」。

## 3. 未验证/边界

- 未在真实 barra 仓执行迁移修复（只读要求）；修复在临时克隆验证。
- 未重跑 barra 全量 pytest（约 97 分钟）与 CI；`verify_claim` 的 test-count 重算基于仓内已入库 JUnit。
- barra 的 `make check`/`verify-static` 未升级 Makefile；新 target（`selftest`/`scorecard`/`upgrade-check`）需按 migration 矩阵回写。
- 归档计划文本中的未验证项不会自动回填（本次通过豁免表声明），这是刻意设计（历史不改写）。
