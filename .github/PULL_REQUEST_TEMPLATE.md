## 变更类型

- [ ] 文档 / 规则 / 工具（`make verify-static`）
- [ ] Swift 逻辑 / ViewModel（`make test`）
- [ ] UI（`make test-ui`）
- [ ] 语音 / 翻译 / TTS / 音频 / 持久化（真机 `harness/tools/device-test.sh`）

## 变更说明

（目标与非目标；影响范围；为什么需要这次改动）

## 验证（必填；未运行请写“未验证”，不要留空）

- 命令：
- 结果（exit code / 通过数与 skip 数）：
- 环境（Xcode / 模拟器 runtime 或真机型号 + iOS）：
- evidence id（如有，见 `harness/evidence/`）：
- 未验证项：

## 检查清单

- [ ] `make check` PASS（文档/规则/工具改动必跑）
- [ ] 没有提交签名 Team、设备 UDID、本机绝对路径或密钥
- [ ] 涉及 harness 规则/计划时：已更新计划与证据（见 `harness/AGENTS.md`）
- [ ] 没有为“变绿”删除检查、放宽 skip 或改写既有断言
