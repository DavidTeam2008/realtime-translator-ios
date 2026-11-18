PROJECT ?= Duiyi.xcodeproj
SCHEME ?= Duiyi
SIM_NAME ?= iPhone 17 Pro Max
# 基线 runtime；换 Xcode/模拟器时用 SIM_OS=<version> 覆盖
SIM_OS ?= 26.4.1
SIM_DEST ?= platform=iOS Simulator,name=$(SIM_NAME),OS=$(SIM_OS)
DERIVED ?= /tmp/duiyi-build
DERIVED_DEVICE ?= $(DERIVED)-device
TEAM_RULES ?= ../../agent/template
# 独立模板仓（harness-kit 镜像）；`make kit-publish` 只往这里推
KIT_REMOTE ?= git@github.com:DavidTeam2008/harness-engineering-kit.git
N ?= 10
# 仅本机证据构建设置（空格分隔）；例如 macOS 26+ 嵌套沙箱 + 模拟器禁签名
XCODEBUILD_BUILD_ARGS ?=
XCODEBUILD_BUILD_FLAG = $(foreach arg,$(XCODEBUILD_BUILD_ARGS),--xcodebuild-arg '$(arg)')

# 门禁工具是 Python 标准库脚本：禁止写 __pycache__（运行卫生）
export PYTHONDONTWRITEBYTECODE := 1

.PHONY: help build build-device test test-ui test-one device-test device-test-ui device-test-one \
	status start verify handoff release check check-plan-strict check-evidence check-host \
	adapters-check adapters-sync verify-static verify-claim verify-all release-check doctor doctor-ios plan \
	selftest upgrade-check scorecard check-arch check-tests check-docs check-harness check-plan \
	resume end verify-claim-fresh check-agents check-all evidence hooks-install kit-check kit-prompts \
	kit-publish kit-drift measure-launch harness-audit evidence-chain-check evidence-unit evidence-ui evidence-ui-device

help: ## 显示本帮助
	@echo "对译 Duiyi · 可用命令（模拟器=$(SIM_NAME) / iOS $(SIM_OS)）"
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  make %-22s %s\n", $$1, $$2}'

# ── 宿主：构建 / 测试 / 真机 ──────────────────────────────────────────────
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
	harness/tools/device-test.sh

device-test-ui: ## 真机 UI（预热后）
	harness/tools/device-test.sh ui

device-test-one: ## 真机单用例：make device-test-one TEST=DuiyiUITests/SimultaneousFlowTests/testHomeModuleNavigation
	@test -n "$(TEST)" || { echo "用法：make device-test-one TEST=Target/Class/test"; exit 2; }
	harness/tools/device-test.sh one $(TEST)

measure-launch: ## 真机冷启动：APM_APP=... APM_UDID=... make measure-launch [N=10]
	@test -n "$(APM_APP)" || { echo "缺少 APM_APP（Release-iphoneos 的 .app）"; exit 2; }
	@test -n "$(APM_UDID)" || { echo "缺少 APM_UDID（硬件 UDID）"; exit 2; }
	APM_APP="$(APM_APP)" APM_UDID="$(APM_UDID)" harness/tools/measure-launch.sh $(N)

# ── kit 0.5.4：状态 / 计划 / 证据 / 适配层（配置唯一来源 harness/config.json）──
status: ## 一屏状态（只读；Agent 冷启动第一命令）
	python3 tools/harness.py status

start: ## 新建计划：make start TOPIC=<topic> [GOAL="..."] [SCOPE="dir1 dir2"]
	@test -n "$(TOPIC)" || { echo "用法：make start TOPIC=<topic> [GOAL=\"...\"] [SCOPE=\"dir1 dir2\"]"; exit 2; }
	python3 tools/harness.py start --topic "$(TOPIC)" $(if $(GOAL),--goal "$(GOAL)") $(foreach s,$(SCOPE),--scope $(s))

verify: ## 同步未提交段 + 静态门禁 + 计划严格校验
	python3 tools/harness.py verify

handoff: ## 交接摘要：make handoff [PLAN=harness/plans/xxx.md]
	python3 tools/harness.py handoff $(if $(PLAN),--plan $(PLAN),)

release: ## 发布前检查：严格计划 + fresh 证据（standard 分级）
	python3 tools/harness.py release --check

check-plan-strict: ## 计划严格校验（未提交段 / 归档 / submitted scope）
	python3 tools/check_plan.py check --strict

check-evidence: ## 证据 schema 校验
	python3 tools/evidence.py validate

check-host: ## 宿主卫生 / 分层守卫（未配置 hygiene/layers 时 SKIP）
	python3 tools/check_hygiene.py
	python3 tools/check_layers.py

adapters-check: ## 校验适配层（skills 单源 / 哈希）
	python3 tools/adapters.py check

adapters-sync: ## 同步 .dsh/skills → .claude/skills（本机生成物）
	python3 tools/adapters.py sync

verify-claim: ## 证据三值判定：make verify-claim [CLAIM=harness/evidence/xxx.json]
	python3 tools/verify_claim_chain.py $(if $(CLAIM),$(CLAIM),--all)

verify-claim-fresh: ## 证据时效检查（STALE 告警，不阻断）
	python3 tools/verify_claim_chain.py --all --fresh

verify-all: verify-static verify-claim ## 完整本地验证（静态门禁 + 证据三值判定）
	@echo "[INFO] verify-all 通过：静态门禁 + 证据三值判定"

doctor: ## 环境自检（kit 通用：python3 / git / 测试命令 / 适配器）
	python3 tools/doctor.py

doctor-ios: ## iOS 宿主环境自检（Xcode / 模拟器 runtime / 真机入口 / 模板仓）
	python3 tools/doctor-ios.py

plan: ## 新建跨会话计划：make plan TOPIC=<topic>
	@test -n "$(TOPIC)" || { echo "用法：make plan TOPIC=<topic>"; exit 2; }
	python3 tools/check_plan.py new "$(TOPIC)"

selftest: ## 负向注入自检（证明门禁会红；需 tools/harness_selftest）
	@test -f tools/harness_selftest || { echo "缺少 tools/harness_selftest：用 v0.4.0+ 的 profile 重新 init，或从 kit 复制 scripts/harness-selftest"; exit 2; }
	python3 tools/harness_selftest --target .

upgrade-check: ## 只读检查 kit 升级项（需要 KIT_ROOT 指向 kit 克隆）
	@test -n "$(KIT_ROOT)" || { echo "用法：make upgrade-check KIT_ROOT=<kit 克隆路径>"; exit 2; }
	@test -f "$(KIT_ROOT)/scripts/harness-upgrade" || { echo "KIT_ROOT 下缺少 scripts/harness-upgrade：$(KIT_ROOT)"; exit 2; }
	python3 "$(KIT_ROOT)/scripts/harness-upgrade" --target . --check

scorecard: ## 生成/刷新评分卡草稿（harness/reviews/<date>-scorecard.md）
	python3 tools/scorecard.py --generate

evidence: ## 列出已入库证据
	python3 tools/evidence.py ls

evidence-chain-check: ## 证据链 pin + manifest/freshness 负向自检
	python3 tools/evidence_chain.py check-pin
	python3 tools/evidence_chain.py selftest
	python3 tools/evidence_chain.py freshness-selftest

delivery-check-pin: ## 固定外部 delivery toolchain 版本与哈希
	python3 tools/evidence_chain.py check-pin
	python3 tools/delivery_check.py --pin-only

delivery-check: ## 交付门禁：make delivery-check CHANGE=<id> [CI_JSON=<path>]
	@test -n "$(CHANGE)" || { echo "用法：make delivery-check CHANGE=<id> [CI_JSON=<path>]"; exit 2; }
	python3 tools/delivery_check.py --change "$(CHANGE)" $(if $(CI_JSON),--ci-json "$(CI_JSON)")

delivery-check-fixtures: ## delivery-check 结构正/负 fixture
	python3 tools/delivery_fixtures.py

delivery-discipline-fixtures: ## discipline receipt 正/负 fixture（宿主 v0.3.1）
	python3 tools/delivery_discipline_fixtures.py

doctor-skills: ## 检查 Claude Code 的 openspec/superpowers 用户级软链
	python3 tools/doctor_skills.py

evidence-unit: ## 单元测试 → xcresult/JUnit/manifest（WRITE=1 写入证据）
	python3 tools/evidence_chain.py run --claim unit-tests-pass \
		$(if $(filter 1,$(WRITE)),--write-evidence) $(if $(RUN_ID),--run-id $(RUN_ID)) \
		$(if $(TIMEOUT),--timeout $(TIMEOUT)) $(XCODEBUILD_BUILD_FLAG)

evidence-ui: ## UI 测试 → xcresult/JUnit/manifest（WRITE=1 写入证据）
	python3 tools/evidence_chain.py run --claim ui-tests-pass \
		$(if $(filter 1,$(WRITE)),--write-evidence) $(if $(RUN_ID),--run-id $(RUN_ID)) \
		$(if $(TIMEOUT),--timeout $(TIMEOUT)) $(XCODEBUILD_BUILD_FLAG)

evidence-ui-device: ## 真机 UI（需 APM_TEAM；预热 + xcresult/JUnit/manifest）
	@test -n "$(APM_TEAM)" || { echo "用法：APM_TEAM=<Team ID> make evidence-ui-device [WRITE=1]"; exit 2; }
	APM_TEAM="$(APM_TEAM)" python3 tools/evidence_chain.py run --claim ui-device-tests-pass \
		$(if $(filter 1,$(WRITE)),--write-evidence) $(if $(RUN_ID),--run-id $(RUN_ID)) \
		$(if $(TIMEOUT),--timeout $(TIMEOUT)) $(XCODEBUILD_BUILD_FLAG)

resume: ## 接手：active 计划 + git 状态 + 下一步（status 别名）
	python3 tools/harness.py status

end: verify-static verify-claim-fresh check-plan-strict ## 收尾：静态门禁 + 证据判定/时效 + 计划严格校验
	@git status --short

# ── 宿主：既有检查（保留）────────────────────────────────────────────────
check-arch: ## 架构铁律 R1–R6（依赖单向 / 翻译锚 View / 单引擎 / 内存为准）
	python3 tools/check-arch.py

check-tests: ## 测试计数下限 + skip 白名单（防删测试变绿）
	python3 tools/check-test-baseline.py

check-docs: ## 文档链接 / 围栏 / 索引 / 预算（check_docs 别名）
	python3 tools/check_docs.py

check-harness: ## 指令层机检（check_agents 别名）
	python3 tools/check_agents.py

check-plan: ## 计划状态机与必填字段（check_plan 别名）
	python3 tools/check_plan.py check

check: check-arch check-tests ## 本地门禁（kit + 宿主）
	@python3 tools/check_docs.py
	@python3 tools/check_agents.py
	@python3 tools/check_plan.py check --lenient-uncommitted
	@python3 tools/scorecard.py --check-stale
	@python3 tools/adapters.py check

check-agents: ## 校验团队基线（无模板仓时 SKIP）
	@if [ ! -f "$(TEAM_RULES)/scripts/sync_team_baseline.py" ]; then \
		echo "[SKIP] 未找到团队规则仓：$(TEAM_RULES)"; \
		echo "       有模板仓时用 TEAM_RULES=<path> make check-agents 复跑"; \
	else \
		python3 "$(TEAM_RULES)/scripts/sync_team_baseline.py" --check AGENTS.md; \
	fi

check-all: verify-static check-agents ## 本地门禁 + 团队基线

verify-static: check check-plan-strict check-evidence check-host evidence-chain-check kit-check ## 本地静态门禁（计划严格 + 证据 schema + 宿主 + 证据链 pin + kit 验收；不含证据三值判定）
	@bash -n harness/tools/*.sh tools/*.sh .githooks/pre-push
	@echo "[INFO] verify-static 不含证据三值判定；完成声明 / PR 前请运行 make verify-claim 或 make verify-all"

release-check: verify-static ## 发布前门禁：证据时效 strict + 评分卡有效期
	@python3 tools/scorecard.py --check-stale --strict
	@python3 tools/verify_claim_chain.py --all --fresh --strict

hooks-install: ## 安装 git hooks（pre-push 跑 verify-static）
	@git config core.hooksPath .githooks
	@chmod +x .githooks/pre-push
	@echo "已安装 core.hooksPath=.githooks；SKIP_HARNESS_HOOK=1 可跳过 pre-push"

harness-audit: check-all doctor-ios evidence ## 五子系统月度审计入口（Phase 3 前人工打分）
	@echo "按 HARNESS.md 的审计清单给 Instructions/State/Verification/Scope/Lifecycle 打分，结果写 harness/reviews/"

# ── kit 仓自身：发布 / 镜像 ──────────────────────────────────────────────
kit-check: ## harness-kit 端到端验收（三 profile init + make check + hygiene）
	PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s harness-kit/tests -q

kit-prompts: ## 由 harness-kit/prompts/ 重新生成 kit 提示词文档
	@python3 harness-kit/scripts/harness-prompt render

kit-publish: ## 把仓内 harness-kit 同步到独立模板仓（镜像只接受这条路径）
	@set -e; sha=$$(git subtree split --prefix=harness-kit); \
	echo "kit split → $$sha"; \
	git push $(KIT_REMOTE) "$$sha:refs/heads/main"; \
	echo "镜像仓 tag：临时 clone 镜像仓后 git tag -a v<ver> -m <note> && git push origin v<ver>"

kit-drift: ## 校验独立模板仓与仓内 harness-kit 是否同步（漂移 exit 1）
	@set -e; local_sha=$$(git subtree split --prefix=harness-kit); \
	remote_sha=$$(git ls-remote $(KIT_REMOTE) refs/heads/main | cut -f1); \
	if [ "$$local_sha" = "$$remote_sha" ]; then \
		echo "kit mirror in sync ($$local_sha)"; \
	else \
		echo "kit mirror DRIFTED: local=$$local_sha remote=$$remote_sha"; \
		echo "只改仓内 harness-kit/ 再 make kit-publish；不要直接改镜像仓"; \
		exit 1; \
	fi
