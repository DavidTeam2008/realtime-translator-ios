# HARNESS.md · Harness Engineering 实践地图（对译 Duiyi）

> 一句话：把「Agent 该做什么」（**guides**，前馈）和「仓库怎么否证完成声明」（**sensors**，反馈）固化进仓库，让「做完了/已验证」变成可被脚本判定的声明。
> 这是**系统地图**，不是事实真源。真源优先级见 [`docs/README.md`](docs/README.md)；规则入口 [`AGENTS.md`](AGENTS.md)；本地开发 [`CONTRIBUTING.md`](CONTRIBUTING.md)。

## 1. 问题

Agent 的常见失败不是「不会写代码」，而是完成声明不可验证、上下文每次重建、验证成本错配、过程文档淹没主线。harness 不给模型加能力，它给「完成」加一道可复核闸门。

## 2. 五个子系统与落点

| 子系统 | 作用 | 本项目落点 |
|---|---|---|
| Instructions | 该做什么、去哪读 | [`AGENTS.md`](AGENTS.md) + 嵌套 `AGENTS.md` + [`references/`](references/)；`make check` 校验预算/引用/敏感串 |
| State | 做到哪、上次结论 | [`harness/plans/`](harness/plans/)（唯一 active）+ [`harness/evidence/`](harness/evidence/) |
| Verification | 怎么算完成、能否否证 | 四层验证（§4）+ 证据三值 `make verify-claim` |
| Scope | 一次只做什么 | 计划 `scope.allow/deny` + L0/L1/L2 分级 + 红队（L2 并发/持久化/发布） |
| Session Lifecycle | 开工/交接/收尾 | `make resume` / `make handoff` / `make end` + `.dsh/skills/` 流程 skill |

## 3. 两条回路

- **前馈**：AGENTS 路由 + 嵌套规则 + `references/` 契约；根指令只指路。
- **反馈**：`make check`（文档/指令/架构/计数/计划/适配层）→ `make verify-static`（+ 计划严格/证据 schema/宿主/kit 验收）→ `make verify-claim`（证据三值）→ `make verify-all`；`make selftest` 负向注入证明门禁会红。
- CI 与 pre-push 只跑静态层；动态测试按需本地/真机执行。

## 4. 验证分层（口径唯一源：[`references/verification.md`](references/verification.md)）

| 层 | 命令 | 说明 |
|---|---|---|
| 静态 | `make check` / `make verify-static` | 秒级、无 Xcode；改文档/规则/工具必跑 |
| 模拟器 | `make test` / `make test-ui` | 逻辑/VM 必跑；语音 UI 用例 skip 是预期 |
| 真机 | `make device-test` | 语音/翻译/TTS/音频/持久化改动必跑（`device-verify` skill） |
| 性能 | Release 真机 n≥10 | 启动优化已暂停，不重启微优化 |

## 5. 证据政策

- 一条证据一个 JSON：命令、环境、计数、commit、verdict；**当前证据必须 git 跟踪**，原始产物不入库。
- 三值 **PASS / FAIL / UNVERIFIED**；无证据即未验证；`verify-claim` 校验 commit 祖先、clean tree、counts 与 artifact 重算。
- 归档用 `git mv` 进 `harness/evidence/_archive/`，旧证据由新 PASS 证据 `supersedes` 接管；归档 FAIL/UNVERIFIED 未接管 → 聚合 UNVERIFIED。
- 细则见 [`harness/evidence/README.md`](harness/evidence/README.md)。**当前 test-count claim 为 `requireArtifact:false`（legacy opt-out）**：本机无 Xcode，待补 xcresult→JUnit 流水线后收紧（见计划未验证项）。

## 6. 阶段与现状

- Phase 0/1/2.5 已完成：五子系统、静态门禁、证据三值、CI、skills；独立复评 ≈4.0/5（报告见 [`harness/reviews/`](harness/reviews/)）。
- Phase 3/4 已完成：clean clone 可复现、CI、`v1.0.0` tag + Release；分支保护/PR 流程未完全落地。
- Phase 5：模板抽取为 [`harness-kit/`](harness-kit/README.md)（独立镜像，当前 `v0.5.4`）。Phase 6（行为级测试）未排期。

## 7. kit 维护（唯一源 + 只读镜像）

- 唯一源是本仓 [`harness-kit/`](harness-kit/)；镜像 <https://github.com/DavidTeam2008/harness-engineering-kit> 只读。
- 改完 `make kit-check`（330 tests）→ 发布 `make kit-publish`（subtree split push 镜像 main）→ 镜像仓手动打 annotated tag。
- `make kit-drift` 校验本地与镜像一致；**不一致回源仓改，不直接改镜像仓**；kit 缺陷走镜像仓 issue。
- 本仓宿主层升级走 `harness-upgrade --plan` 逐文件回写（`--apply` 未实现），记录在计划。

## 8. 复制到其他项目（10 分钟路径）

装入口 skill（首选 npx，见 [`harness-kit/README.md`](harness-kit/README.md)；无 Node/离线用 `harness-skill install`）→ 对 Agent 说「接入这个项目」；或命令行 `harness-adopt`→ `harness-init --profile standard|strict` → `make check` → `make selftest`。

## 9. 局限

- 静态门禁不证明行为正确；动态层依赖 Xcode/模拟器/真机，缺环境只能写「未验证」。
- 证据不防伪造，只提高说谎成本；高风险改动仍走独立红队。
- 指令文件有 token 预算，规则增长优先删/合并/下沉；kit 升级无 in-place 命令，需人工合并。

## 10. 月度审计清单（人工）

Instructions/State/Verification/Scope/Lifecycle 各 1–5 分（预算、active 唯一、证据 fresh、越界、交接可恢复），结论写 `harness/reviews/` 并回写 issue。
