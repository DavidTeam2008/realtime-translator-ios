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
- **执行器政策**：默认 mattpocock code-review（宿主有 subagent 时并行两轴），自定义两轴 prompt 兜底；人工可直接替代。任何执行器都必须复跑关键门禁或明确写“未复跑”，未复跑不得写 PASS。

## 4. 输出结构

保留 front matter（`base` / `head` / `reviewer` / `p0` / `p1` / `p2` / `verdict`），delivery-check 继续按此门禁；正文采用：

1. 结论（通过 / 有条件通过 / 不通过）。
2. 复跑与边界。
3. Standards 轴（仓库标准 + smell 基线，仓库标准优先）。
4. Spec 轴（需求/场景覆盖、缺失、偏差、越界）。
5. 归一问题表（轴 + P0/P1/P2 + 关闭状态）。
6. 被挑战假设、缺失信息与最小验证清单。
7. 作者回应（接受 / 拒绝 / 待定 + 理由）。

可选字段：`review_method` / `review_method_commit` / `axes`，只作方法溯源，不参与门禁。

## 5. 归档与回应

- 报告命名 `<YYYY-MM-DD>-<topic>.md`，从 [`_template.md`](_template.md) 复制。
- 作者逐条回应（接受 / 拒绝 / 待定 + 理由），最多两轮；P0/P1 执行前解决，P2 记录排期。
- 报告与回应中的证据用 ID 或相对路径，不写本机绝对路径与设备信息。
