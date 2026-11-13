# 反馈 kit 问题（缺陷 / 文档不一致 / 需求建议）

> 宿主遇到 kit 自身问题时，优先交回 kit 上游，不要在宿主仓私改 kit 门禁绕过——升级会覆盖，问题会留给下一个宿主。

## 1. 先分诊

| 现象 | 归属 | 动作 |
| --- | --- | --- |
| init / adopt / 门禁脚本报错、结果不可信、模板或 JSON 渲染坏 | kit 缺陷 | 按 §2 开 issue |
| 文档与行为不一致（命令跑不通、字段/路径变了） | 文档缺陷 | 开 issue；能定位就直接向上游提 PR |
| 未登记文档、测试命令不真实、环境/签名/CI 平台差异 | 宿主侧 | 宿主内修，不占 kit issue |
| kit 未承诺能力（不跑测试、不解析测试输出、不做代码迁移） | kit 边界 | 先读 kit README「局限与未验证」 |
| 想加 profile / 门禁 / 场景 | 需求建议 | 开 issue 并附真实失败案例 |

## 2. 必附信息（缺项会被退回）

- kit 版本：`<kit>/VERSION`，或宿主 `.harness-manifest.json` 的 `kitVersion`；
- profile 与宿主技术栈（如 `standard` + Node/pnpm）；
- 复现命令原文 + 退出码 + 关键输出（**脱敏后**）；
- 期望 vs 实际；
- 最小复现：空白临时仓 `harness-init` 步骤，或一个最小 commit / 精简片段。

不贴密钥/Token、宿主私有代码、本机绝对路径（用 `<repo>` 代替）。

## 3. 提交

- 地址：<https://github.com/DavidTeam2008/harness-engineering-kit/issues>（公开镜像仓受理 issue；镜像只读，修复在来源仓完成后随版本发布）。
- 标题建议：`[缺陷|文档|需求] <一句话现象>`。
- 先输出一份可直接粘贴的 issue 草稿给用户确认；**不要替用户直接发布对外内容**。

## 4. 修复后回流

1. `harness-upgrade --check/--plan` 对照新版；只回写 kit 管理面（见 `upgrade.md`）。
2. 重装入口 skill：`<kit>/scripts/harness-skill install --scope user --force`。
3. `make verify-static` 复核，把结论回写 issue。

## 5. 不要做

- 不通过改宿主 `tools/`、`Makefile.harness`、kit 模板来「绕过」缺陷：升级会覆盖，且同样问题会扩散。
- 不为变绿删除/弱化门禁；先按 `adopt.md` 与 kit `docs/adoption.md` §2.2.1「已知坑」核对是否已有解法。
