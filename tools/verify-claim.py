#!/usr/bin/env python3
"""完成声明的三值判定：PASS(0) / FAIL(1) / UNVERIFIED(2)。

输入：一条 evidence JSON 路径，或 `--all` 扫描 `.apm/evidence/*.json`。
判定顺序：schema/语义 → git（HEAD 或其祖先、dirty=false）→ 按 claim 类型复核：

    unit-tests-pass    passed≥baseline.unit.floor；failed=0；skipped=0；
                       xcresult 缺失/不存在 → UNVERIFIED
    ui-tests-pass      passed≥baseline.ui.floor；skipped：模拟器=1 / 真机=0；
                       xcresult 缺失/不存在 → UNVERIFIED
    device-tests-pass  passed≥unit.floor+ui.floor；skipped=0（真机白名单）；
                       xcresult 缺失/不存在 → UNVERIFIED
    docs-pass          复跑 tools/check-docs.py；exit 0 → PASS
    arch-pass          复跑 tools/check-arch.py；exit 0 → PASS
    perf-*             metrics 存在；context.commit/build 与证据一致；n≥10；CV≤10%；
                       不满足 → UNVERIFIED（测量无效不是"通过"）

输出固定格式：`CLAIM <id>: PASS|FAIL|UNVERIFIED — <原因>`。
无 evidence 文件 → FAIL（"未验证的声明"）。
`--all` 退出码：任一 FAIL→1；否则任一 UNVERIFIED→2；全 PASS→0。
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import subprocess
import sys
from pathlib import Path
from typing import Any

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))
import evidence as evidence_tool  # noqa: E402

DEFAULT_ROOT = Path(__file__).resolve().parent.parent
BASELINE_REL = ".apm/test-baseline.json"
MIN_PERF_SAMPLES = 10
MAX_PERF_CV_PERCENT = 10.0
STATIC_TIMEOUT_SEC = 120
TEST_CLAIMS = ("unit-tests-pass", "ui-tests-pass", "device-tests-pass")
PERF_CLAIMS = ("perf-measurement", "perf-no-regression", "perf-improved")

PASS, FAIL, UNVERIFIED = "PASS", "FAIL", "UNVERIFIED"


# ── 辅助 ───────────────────────────────────────────────────────────────────
def resolve_artifact(root: Path, value: str) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = root / path
    return path


def run_git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        timeout=30,
    )


def load_json(path: Path) -> tuple[Any | None, str | None]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except json.JSONDecodeError as exc:
        return None, f"JSON 非法：{exc}"
    except OSError as exc:
        return None, f"无法读取：{exc}"


def load_baseline(root: Path) -> tuple[dict[str, Any] | None, str | None]:
    path = root / BASELINE_REL
    if not path.is_file():
        return None, f"缺少 {BASELINE_REL}（测试计数基线）"
    data, error = load_json(path)
    if error:
        return None, f"{BASELINE_REL} {error}"
    if not isinstance(data, dict):
        return None, f"{BASELINE_REL} 必须是 object"
    try:
        int(data["unit"]["floor"])
        int(data["ui"]["floor"])
        int(data["expectedSkipped"]["simulator"])
        int(data["expectedSkipped"]["device"])
    except (KeyError, TypeError, ValueError):
        return None, f"{BASELINE_REL} 结构不完整（unit/ui/expectedSkipped）"
    return data, None


# ── git 证据有效性 ─────────────────────────────────────────────────────────
def check_git(root: Path, doc: dict[str, Any]) -> list[str]:
    git = doc.get("git")
    if not isinstance(git, dict):
        return ["缺少 git 字段"]
    commit = str(git.get("commit", "")).strip()
    dirty = git.get("dirty")
    if not re.fullmatch(r"[0-9a-f]{7,40}", commit):
        return [f"git.commit 非法：{commit!r}"]
    if dirty is not False:
        return ["git.dirty 必须为 false（dirty 工作树的证据不可判 PASS）"]
    head = run_git(root, "rev-parse", "HEAD")
    if head.returncode != 0:
        return [f"无法确定仓库 HEAD（git exit {head.returncode}）"]
    ancestor = run_git(root, "merge-base", "--is-ancestor", commit, "HEAD")
    if ancestor.returncode != 0:
        return [f"git.commit {commit} 不是当前 HEAD 或其祖先"]
    return []


# ── 测试类 claim ───────────────────────────────────────────────────────────
def check_test_claim(root: Path, doc: dict[str, Any], claim: str) -> tuple[str, list[str]]:
    baseline, error = load_baseline(root)
    if baseline is None:
        return FAIL, [error or "测试基线不可用"]
    result = doc.get("result")
    environment = doc.get("environment")
    if not isinstance(result, dict) or not isinstance(environment, dict):
        return FAIL, ["result/environment 结构非法"]
    unit_floor = int(baseline["unit"]["floor"])
    ui_floor = int(baseline["ui"]["floor"])
    simulator_skipped = int(baseline["expectedSkipped"]["simulator"])
    device_skipped = int(baseline["expectedSkipped"]["device"])

    if claim == "unit-tests-pass":
        floor = unit_floor
        expected_skipped = 0
    elif claim == "ui-tests-pass":
        floor = ui_floor
        if environment.get("device"):
            expected_skipped = device_skipped
        elif environment.get("simulator"):
            expected_skipped = simulator_skipped
        else:
            return UNVERIFIED, ["无法确定运行环境（environment.simulator/device 均为空）"]
    else:  # device-tests-pass
        floor = unit_floor + ui_floor
        if not environment.get("device"):
            return UNVERIFIED, ["device-tests-pass 需要 environment.device 非空"]
        expected_skipped = device_skipped

    status = result.get("status")
    passed = int(result.get("passed", 0) or 0)
    failed = int(result.get("failed", 0) or 0)
    skipped = int(result.get("skipped", 0) or 0)

    if status != "SUCCEEDED":
        return FAIL, [f"result.status={status!r} 不是 SUCCEEDED"]
    if failed != 0:
        return FAIL, [f"failed={failed}，失败的测试不能算通过"]
    if passed < floor:
        return FAIL, [f"passed={passed} < 基线 floor={floor}（疑似删测试/少跑）"]
    if skipped != expected_skipped:
        return FAIL, [f"skipped={skipped} ≠ 环境预期 {expected_skipped}（skip 白名单漂移）"]

    artifact = result.get("xcresultPath")
    if not artifact:
        return UNVERIFIED, ["缺 xcresult 产物路径（计数符合，但无机器可复核产物）"]
    path = resolve_artifact(root, str(artifact))
    if not path.exists():
        return UNVERIFIED, [f"xcresult 不存在：{artifact}（换机器/已清理则无法复核）"]
    return PASS, [
        f"passed={passed} ≥ floor={floor}",
        "failed=0",
        f"skipped={skipped} == 预期 {expected_skipped}",
        "xcresult 存在",
    ]


# ── 静态门禁 claim ─────────────────────────────────────────────────────────
def check_static_claim(
    root: Path, script_rel: str, label: str
) -> tuple[str, list[str]]:
    script = root / script_rel
    if not script.is_file():
        return UNVERIFIED, [f"缺 {script_rel}，无法复跑静态门禁"]
    try:
        proc = subprocess.run(
            [sys.executable, str(script), "--root", str(root)],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=STATIC_TIMEOUT_SEC,
        )
    except (OSError, subprocess.SubprocessError) as exc:  # pragma: no cover - 环境异常
        return UNVERIFIED, [f"无法执行 {script_rel}：{exc}"]
    if proc.returncode == 0:
        return PASS, [f"{label} 复跑 PASS"]
    tail = (proc.stdout + proc.stderr).strip().splitlines()[-1:] or [""]
    return FAIL, [f"{label} 复跑 exit {proc.returncode}：{tail[0][:160]}"]


# ── 性能 claim ─────────────────────────────────────────────────────────────
def check_perf_claim(root: Path, doc: dict[str, Any]) -> tuple[str, list[str]]:
    result = doc.get("result")
    environment = doc.get("environment")
    git = doc.get("git")
    if not isinstance(result, dict) or not isinstance(environment, dict) or not isinstance(git, dict):
        return FAIL, ["result/environment/git 结构非法"]
    metrics_ref = result.get("metricsPath")
    if not metrics_ref:
        return UNVERIFIED, ["缺 metricsPath（性能证据需要 metrics.json 摘要）"]
    path = resolve_artifact(root, str(metrics_ref))
    if not path.is_file():
        return UNVERIFIED, [f"metrics 文件不存在：{metrics_ref}"]
    data, error = load_json(path)
    if error:
        return UNVERIFIED, [f"metrics {error}"]
    if not isinstance(data, dict):
        return UNVERIFIED, ["metrics.json 必须是 object"]
    context = data.get("context")
    metrics = data.get("metrics")
    if not isinstance(context, dict) or not isinstance(metrics, list) or not metrics:
        return UNVERIFIED, ["metrics.json 缺 context/metrics"]

    context_commit = str(context.get("commit", "")).strip()
    evidence_commit = str(git.get("commit", "")).strip()
    if context_commit and context_commit not in ("unknown", "None"):
        if not (
            evidence_commit.startswith(context_commit)
            or context_commit.startswith(evidence_commit)
        ):
            return FAIL, [f"metrics context.commit={context_commit} 与证据 commit={evidence_commit} 不一致"]
    context_build = str(context.get("build", "")).strip()
    evidence_build = str(environment.get("build") or "").strip()
    if context_build and evidence_build and context_build.lower() != evidence_build.lower():
        return FAIL, [f"metrics context.build={context_build} 与 environment.build={evidence_build} 不一致"]

    chosen: dict[str, Any] | None = None
    for metric in metrics:
        if isinstance(metric, dict) and metric.get("name") == "startup.cold.first_frame":
            chosen = metric
            break
    if chosen is None:
        for metric in metrics:
            if isinstance(metric, dict) and isinstance(metric.get("samples"), list) and metric["samples"]:
                chosen = metric
                break
    if chosen is None:
        return UNVERIFIED, ["metrics 中没有可用的 samples"]
    samples = [
        float(value)
        for value in chosen.get("samples", [])
        if isinstance(value, (int, float)) and not isinstance(value, bool)
    ]
    count = len(samples)
    if count < MIN_PERF_SAMPLES:
        return UNVERIFIED, [f"n={count} < {MIN_PERF_SAMPLES}（样本不足，测量无效）"]
    mean = statistics.fmean(samples)
    if mean <= 0:
        return UNVERIFIED, ["样本均值 <= 0，测量无效"]
    cv = statistics.stdev(samples) / mean * 100 if count > 1 else 0.0
    if cv > MAX_PERF_CV_PERCENT:
        return UNVERIFIED, [f"CV={cv:.1f}% > {MAX_PERF_CV_PERCENT:.0f}%（测量无效）"]
    return PASS, [
        f"测量可用：metric={chosen.get('name')} n={count} CV={cv:.1f}%",
        "context commit/build 一致",
        "显著性/最小效应属 Phase 2，本 PASS 不代表性能改善",
    ]


def load_schema_for(root: Path) -> tuple[dict[str, Any] | None, list[str]]:
    """优先用 --root 指到的仓库 schema；fixture 仓库没有时退回工具自身仓库的 schema。"""
    schema, errors = evidence_tool.load_schema(root)
    if schema is not None:
        return schema, errors
    fallback, fallback_errors = evidence_tool.load_schema(DEFAULT_ROOT)
    if fallback is not None:
        return fallback, []
    return None, errors + fallback_errors


# ── 单条判定 ───────────────────────────────────────────────────────────────
def verify_one(
    root: Path, path: Path, *, require_filename_id: bool = False
) -> tuple[str, list[str], str]:
    """返回 (verdict, reasons, id)。

    require_filename_id=True 用于 --all 扫描证据目录：文件名必须等于 id；
    显式传入单条证据路径时不做这一约束（便于 fixture/临时文件）。
    """
    if not path.is_file():
        return FAIL, [f"未验证的声明：没有 evidence 文件（{path.name}）"], path.stem
    doc, error = load_json(path)
    if error:
        return FAIL, [f"evidence {error}"], path.stem
    if not isinstance(doc, dict):
        return FAIL, ["evidence 必须是 JSON object"], path.stem
    claim_id = str(doc.get("id") or path.stem)

    schema, schema_errors = load_schema_for(root)
    if schema is None:
        return FAIL, schema_errors, claim_id
    schema_errors = evidence_tool.validate_document(doc, schema)
    if schema_errors:
        return FAIL, [f"schema 校验失败：{schema_errors[0]}（共 {len(schema_errors)} 项）"], claim_id
    semantic = evidence_tool.semantic_errors(doc, path) if require_filename_id else []
    if semantic:
        return FAIL, [f"语义校验失败：{semantic[0]}"], claim_id

    git_errors = check_git(root, doc)
    if git_errors:
        return FAIL, git_errors, claim_id

    claim = str(doc.get("claim"))
    if claim in TEST_CLAIMS:
        return (*check_test_claim(root, doc, claim), claim_id)
    if claim == "docs-pass":
        return (*check_static_claim(root, "tools/check-docs.py", "check-docs"), claim_id)
    if claim == "arch-pass":
        return (*check_static_claim(root, "tools/check-arch.py", "check-arch"), claim_id)
    if claim in PERF_CLAIMS:
        return (*check_perf_claim(root, doc), claim_id)
    return FAIL, [f"不支持的 claim 类型：{claim!r}"], claim_id


def print_result(claim_id: str, verdict: str, reasons: list[str]) -> None:
    print(f"CLAIM {claim_id}: {verdict} — {'；'.join(reasons)}")


def exit_code(verdicts: list[str]) -> int:
    if any(verdict == FAIL for verdict in verdicts):
        return 1
    if any(verdict == UNVERIFIED for verdict in verdicts):
        return 2
    return 0


# ── CLI ────────────────────────────────────────────────────────────────────
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="完成声明三值判定：PASS(0) / FAIL(1) / UNVERIFIED(2)",
    )
    parser.add_argument("claim", nargs="?", help="evidence JSON 路径（省略时等价 --all）")
    parser.add_argument("--all", action="store_true", help="校验 .apm/evidence/*.json 全部证据")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="仓库根（默认脚本上级目录）")
    parser.add_argument("--evidence-dir", type=Path, help="证据目录（默认 <root>/.apm/evidence）")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.root).resolve()
    if args.claim:
        verdict, reasons, claim_id = verify_one(root, Path(args.claim).expanduser())
        print_result(claim_id, verdict, reasons)
        return exit_code([verdict])

    directory = Path(args.evidence_dir) if args.evidence_dir else root / ".apm" / "evidence"
    if not directory.is_dir():
        print_result("(none)", FAIL, [f"未验证的声明：缺少证据目录 {directory.name}"])
        return 1
    files = sorted(
        path
        for path in directory.glob("*.json")
        if path.is_file() and path.name not in {"schema.json", "TEMPLATE.json"}
    )
    if not files:
        print_result("(none)", FAIL, ["未验证的声明：没有 evidence 文件"])
        return 1
    verdicts: list[str] = []
    for path in files:
        verdict, reasons, claim_id = verify_one(root, path, require_filename_id=True)
        verdicts.append(verdict)
        print_result(claim_id, verdict, reasons)
    counts = {name: verdicts.count(name) for name in (PASS, FAIL, UNVERIFIED)}
    print(
        f"SUMMARY: pass={counts[PASS]} fail={counts[FAIL]} unverified={counts[UNVERIFIED]}"
        f"（exit {exit_code(verdicts)}）"
    )
    return exit_code(verdicts)


if __name__ == "__main__":
    sys.exit(main())
