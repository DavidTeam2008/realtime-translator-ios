# 独立审查报告（reviews）

> 只读、独立、可复核；报告是证据的一部分，不是过程日志。
> 发起条件与红队协议见 [`../../references/workflow.md`](../../references/workflow.md)；目录规则见 [`../AGENTS.md`](../AGENTS.md)。

## 1. 适用

- 高风险 L2：并发、持久化、发布 / 迁移（沿用 `AGENTS.md `7` 与 `references/workflow.md`；规则/门禁自身大改是否强制独立复核由用户/项目规则另行确认）。
- 两轴审查是 L2 review 的推荐方法，不改变上述红队触发范围。
- 其他 L2 至少做一次自检清单 + 用户确认；需要独立 reviewer 时用本格式。
- 两轴审查是 **M2/M3 起推荐方法**；L0/L1 默认不做正式 review。

## 2. 输入

- 任务描述 + 方案 + 仓库路径（含目标 commit / 工作树状态）。
- 不提供：起草对话、作者自评、既往结论；审查者自行读取当前树。
- Spec 轴输入：proposal / design / spec delta / acceptance / originating issue（至少一处）。

## 3. 规则

- 只读：不改文件、不跑破坏性命令、不读密钥或 `.env`。
- 结论必须可定位：`file:line` 或命令输出摘要。
- 不做风格偏好争论；只报影响正确性、可验证性与可维护性的问题。
- **两轴分离**：Standards 与 Spec 各自给最严重问题，不跨轴排序、不合并成单一赢家。
- **归一化**：每条发现必须落到 P0/P1/P2，并记录关闭状态；交付结论以归一表为准。
- **执行器政策**：默认 mattpocock code-review（两个 sub-agent、隔离上下文）；没有 subagent 工具时必须用两个独立进程/上下文分别跑 Standards 与 Spec，单上下文不得作为 L2 独立 review 通过交付。任何执行器都必须复跑关键门禁或明确写“未复跑”，未复跑不得写 PASS。
- **可机检结构（v2，强制）**：front matter 必须声明 `review_mode: dual-context`、`executor`、`axes`、`standards_report`、`spec_report`、`gate_report`、`gate_runner`；两份轴报告分别带 `axis` 与 `context: isolated|fresh`；`gate_runner` 不得等于 `reviewer`；存在 P1 时必须提供 `p1_fix_review` 与 `p1_fix_reviewed_head`。`make review-check CHANGE=<id>` 与 `delivery-check` 会 fail-closed 校验这些字段与文件是否 tracked。

## 4. 输出结构

保留 front matter（`base` / `head` / `reviewer` / `p0` / `p1` / `p2` / `verdict`），并补 v2 可机检字段（见 §3）；delivery-check 继续按此门禁；正文采用：

1. 结论（通过 / 有条件通过 / 不通过）。
2. 复跑与边界。
3. Standards 轴（仓库标准 + smell 基线，仓库标准优先）。
4. Spec 轴（需求/场景覆盖、缺失、偏差、越界）。
5. 归一问题表（轴 + P0/P1/P2 + 关闭状态）。
6. 被挑战假设、缺失信息与最小验证清单。
7. 作者回应（接受 / 拒绝 / 待定 + 理由）。

可选字段：`review_method` / `review_method_commit` / `axes`，只作方法溯源，不参与门禁。

## 5. 门禁接入与偏差防护

- `make review-check CHANGE=<id>`：只校验 review bundle 结构；`make delivery-check` 在调用 pinned toolchain 前自动调用同一 guard。
- 单上下文 review 只能作为自检记录，**不能**作为 L2 独立 review 通过交付；发现偏差时用新 commit 追加 correction/addendum，不改写已发布历史。
- 旧报告被纠正时，在同一目录新增双上下文 bundle（standards / spec / gates / aggregate 四份），聚合报告声明 `supersedes` 或 addendum 关系；delivery-check 只看当前 change 的 review path。
- guard 只证明“结构存在、文件 tracked、head 绑定”，不证明 reviewer 真读了 skill；最终信任锚仍是 Git、独立 reviewer 与人工复核。

## 6. 归档与回应

- 报告命名 `<YYYY-MM-DD>-<topic>.md`，从 [`_template.md`](_template.md) 复制。
- 作者逐条回应（接受 / 拒绝 / 待定 + 理由），最多两轮；P0/P1 执行前解决，P2 记录排期。
- 报告与回应中的证据用 ID 或相对路径，不写本机绝对路径与设备信息。
