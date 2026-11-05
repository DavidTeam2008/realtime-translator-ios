PROJECT ?= Duiyi.xcodeproj
SCHEME ?= Duiyi
SIM_NAME ?= iPhone 17 Pro Max
# 基线 runtime；换 Xcode/模拟器时用 SIM_OS=<version> 覆盖
SIM_OS ?= 26.4.1
SIM_DEST ?= platform=iOS Simulator,name=$(SIM_NAME),OS=$(SIM_OS)
DERIVED ?= /tmp/duiyi-build
DERIVED_DEVICE ?= $(DERIVED)-device
TEAM_RULES ?= ../../agent/template
N ?= 10

.PHONY: help build build-device test test-ui test-one device-test device-test-ui device-test-one check-docs check-arch check-tests check-harness check-plan check-evidence test-tools check check-all verify-static verify verify-claim evidence hooks-install harness-audit doctor resume end measure-launch plan handoff

help: ## 显示本帮助
	@echo "对译 Duiyi · 可用命令（模拟器=$(SIM_NAME) / iOS $(SIM_OS)）"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  make %-18s %s\n", $$1, $$2}'

build: ## 模拟器编译
	xcodebuild -project $(PROJECT) -scheme $(SCHEME) -destination '$(SIM_DEST)' -derivedDataPath $(DERIVED) build

build-device: ## 真机编译（需签名）
	xcodebuild -project $(PROJECT) -scheme $(SCHEME) -destination 'generic/platform=iOS' -allowProvisioningUpdates -derivedDataPath $(DERIVED_DEVICE) build

test: ## 模拟器单元测试（DuiyiTests）
	xcodebuild test -project $(PROJECT) -scheme $(SCHEME) -destination '$(SIM_DEST)' -derivedDataPath $(DERIVED) -only-testing:DuiyiTests

test-ui: ## 模拟器 UI 测试（语音用例会 skip）
	xcodebuild test -project $(PROJECT) -scheme $(SCHEME) -destination '$(SIM_DEST)' -derivedDataPath $(DERIVED) -only-testing:DuiyiUITests

test-one: ## 单个测试：make test-one TEST=DuiyiTests/TaskStoreTests
	@test -n "$(TEST)" || { echo "用法：make test-one TEST=DuiyiTests/TaskStoreTests"; exit 2; }
	xcodebuild test -project $(PROJECT) -scheme $(SCHEME) -destination '$(SIM_DEST)' -derivedDataPath $(DERIVED) -only-testing:$(TEST)

device-test: ## 真机全套（预热 + 单元 + UI）
	.apm/tools/device-test.sh

device-test-ui: ## 真机 UI（预热后）
	.apm/tools/device-test.sh ui

device-test-one: ## 真机单用例：make device-test-one TEST=DuiyiUITests/SimultaneousFlowTests/testHomeModuleNavigation
	@test -n "$(TEST)" || { echo "用法：make device-test-one TEST=Target/Class/test"; exit 2; }
	.apm/tools/device-test.sh one $(TEST)

check-docs: ## 文档链接 / 围栏 / 索引 / token 预算
	python3 tools/check-docs.py

check-arch: ## 架构铁律 R1–R6（依赖单向 / 翻译锚 View / 单引擎 / 内存为准）
	python3 tools/check-arch.py

check-tests: ## 测试计数下限 + skip 白名单（防删测试变绿）
	python3 tools/check-test-baseline.py

check-harness: ## 指令层机检：预算 / § 引用 / 嵌套 AGENTS / skills / 敏感路径
	python3 tools/check-harness.py

check-plan: ## 计划状态机与必填字段 / 未提交改动 vs git
	python3 tools/plan.py check

check-evidence: ## 证据 schema 校验（.apm/evidence/*.json）
	python3 tools/evidence.py validate

test-tools: ## harness 脚本单测（verify-claim / evidence）
	python3 -m unittest discover -s tools/tests -q

verify-static: check check-evidence test-tools ## 本地秒级门禁（docs+架构+计数+harness+计划+证据+脚本语法+脚本单测）
	@bash -n .apm/tools/*.sh tools/*.sh .githooks/pre-push
	@python3 -m py_compile tools/*.py

verify: verify-static ## 同 verify-static（阶段别名）

verify-claim: ## 校验证据：make verify-claim [CLAIM=.apm/evidence/xxx.json]（默认全部）
	python3 tools/verify-claim.py $(if $(CLAIM),$(CLAIM),--all)

evidence: ## 列出已入库证据
	python3 tools/evidence.py ls

hooks-install: ## 安装 git hooks（pre-push 跑 verify-static）
	@git config core.hooksPath .githooks
	@chmod +x .githooks/pre-push
	@echo "已安装 core.hooksPath=.githooks；SKIP_HARNESS_HOOK=1 可跳过 pre-push"

harness-audit: check-all doctor evidence ## 五子系统月度审计入口（Phase 3 前人工打分）
	@echo "按 HARNESS.md 的审计清单给 Instructions/State/Verification/Scope/Lifecycle 打分，结果写 .apm/reviews/"

doctor: ## 环境自检（Xcode / 模拟器 / mobilebuildmcp / python / 模板仓）
	python3 tools/doctor.py

resume: ## 接手：active 计划 + git 状态 + 下一步 + 建议阅读
	python3 tools/plan.py resume

end: verify-static ## 收尾：门禁 + 计划检查 + git 状态 + 未验证项
	@python3 tools/plan.py end

check-agents: ## 校验团队基线（无模板仓时 SKIP）
	@if [ ! -f "$(TEAM_RULES)/scripts/sync_team_baseline.py" ]; then \
		echo "[SKIP] 未找到团队规则仓：$(TEAM_RULES)"; \
		echo "       有模板仓时用 TEAM_RULES=<path> make check-agents 复跑"; \
	else \
		python3 "$(TEAM_RULES)/scripts/sync_team_baseline.py" --check AGENTS.md; \
	fi

check: check-docs check-arch check-tests check-harness check-plan ## 本地门禁（不依赖模板仓）
check-all: verify-static check-agents ## 本地门禁 + 团队基线

plan: ## 新建跨会话计划：make plan TOPIC=speech-gate
	@test -n "$(TOPIC)" || { echo "用法：make plan TOPIC=speech-gate"; exit 2; }
	@python3 tools/plan.py new "$(TOPIC)"

handoff: ## 交接摘要：make handoff [PLAN=.apm/plans/xxx.md]
	@python3 tools/plan.py brief $(PLAN)

measure-launch: ## 真机冷启动：APM_APP=... APM_UDID=... make measure-launch [N=10]
	@test -n "$(APM_APP)" || { echo "缺少 APM_APP（Release-iphoneos 的 .app）"; exit 2; }
	@test -n "$(APM_UDID)" || { echo "缺少 APM_UDID（硬件 UDID）"; exit 2; }
	APM_APP="$(APM_APP)" APM_UDID="$(APM_UDID)" .apm/tools/measure-launch.sh $(N)
