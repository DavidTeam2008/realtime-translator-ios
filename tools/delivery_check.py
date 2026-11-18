#!/usr/bin/env python3
"""Host adapter for the pinned ai-delivery-toolchain delivery-check.

The adapter only translates the host profile/config into the external tool's
CLI. Task state remains in OpenSpec tasks.md; this script does not copy tasks.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))

from evidence_chain import load_pin  # noqa: E402


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_pointer(document: dict, pointer: str) -> object:
    current: object = document
    for part in pointer.split("."):
        if not isinstance(current, dict) or part not in current:
            raise ValueError(f"baseline 缺字段：{pointer}")
        current = current[part]
    return current


def _latest_manifest_target(root: Path, claim: str) -> str | None:
    evidence = root / "harness" / "evidence"
    candidates = sorted(evidence.glob(f"*{claim}.json"))
    for path in reversed(candidates):
        if path.parent.name == "_archive":
            continue
        try:
            doc = _load(path)
            if doc.get("claim") != claim or doc.get("verdict") != "PASS":
                continue
            manifest_rel = doc.get("result", {}).get("manifest")
            if not isinstance(manifest_rel, str):
                continue
            manifest = _load(root / manifest_rel)
            target = manifest.get("target")
            if isinstance(target, dict) and isinstance(target.get("resultBundlePath"), str):
                return target["resultBundlePath"]
        except (OSError, ValueError, KeyError):
            continue
    return None


def build_profile(root: Path, change: str) -> dict:
    config = _load(root / "harness" / "config.json")
    baseline = _load(root / "harness" / "test-baseline.json")
    claims = {}
    for claim in config.get("claims", []):
        name = claim.get("name")
        if not isinstance(name, str) or claim.get("type") != "test-count":
            continue
        target = dict(claim.get("expectedTarget") or {})
        bundle = _latest_manifest_target(root, name)
        if bundle:
            target["resultBundlePath"] = bundle
        floor = claim.get("floor")
        skipped = claim.get("expectedSkipped")
        if not isinstance(target, dict) or not isinstance(floor, str):
            continue
        claims[name] = {
            "target": target,
            "passedFloor": int(_resolve_pointer(baseline, floor)),
            "expectedSkipped": int(_resolve_pointer(baseline, skipped)) if isinstance(skipped, str) else 0,
            "freshness": (config.get("freshness") or {}).get(name, []),
        }
    delivery = config.get("delivery") if isinstance(config.get("delivery"), dict) else {}
    ci = delivery.get("ci") if isinstance(delivery.get("ci"), dict) else {}
    discipline = delivery.get("discipline") if isinstance(delivery.get("discipline"), dict) else None
    provenance = delivery.get("provenance")
    if provenance is not None and not isinstance(provenance, dict):
        raise ValueError("delivery.provenance 必须是 object")
    contract_lint = delivery.get("contractLint")
    if contract_lint is not None and not isinstance(contract_lint, dict):
        raise ValueError("delivery.contractLint 必须是 object")
    skills = delivery.get("skills")
    if skills is not None and not isinstance(skills, dict):
        raise ValueError("delivery.skills 必须是 object")
    skills_profile = None
    if skills is not None:
        roots = skills.get("roots")
        if roots is None:
            roots_path = root / "harness" / "skills-roots.json"
            roots = json.loads(roots_path.read_text(encoding="utf-8")) if roots_path.is_file() else {}
        if not isinstance(roots, dict):
            raise ValueError("delivery.skills.roots 必须是 object")
        skills_profile = {**skills, "roots": roots}
    provenance_profile = None
    if provenance is not None:
        provenance_profile = dict(provenance)
        provenance_profile.setdefault("receiptsDir", provenance.get("dir", "harness/receipts/openspec"))
    return {
        "evidenceDir": (config.get("paths") or {}).get("evidence", "harness/evidence"),
        "claims": claims,
        "ci": ci,
        "requiredJobs": delivery.get("requiredJobs", []),
        "discipline": discipline,
        "provenance": provenance_profile,
        "contractLint": contract_lint,
        "skills": skills_profile,
    }


def _check_pin_metadata(root: Path) -> None:
    pin = json.loads((root / "tools" / "vendor" / "ai_delivery_toolchain" / "PIN.json").read_text(encoding="utf-8"))
    if pin.get("version") != "0.4.0" or pin.get("tag") != "v0.4.0":
        raise ValueError("PIN 必须固定 v0.4.0")
    if pin.get("tagType") != "annotated":
        raise ValueError("PIN.tagType 必须是 annotated")
    for key in ("tagObject", "sourceTree"):
        value = pin.get(key)
        if not isinstance(value, str) or len(value) != 40:
            raise ValueError(f"PIN.{key} 必须是 40 位 commit/tree hash")
    if pin.get("tagCommit") != pin.get("sourceCommit"):
        raise ValueError("PIN.tagCommit 必须等于 sourceCommit")


def run(
    change: str,
    root: Path,
    tasks: str | None,
    ci_json: str | None,
    validate_json: str | None = None,
    apply_json: str | None = None,
) -> int:
    load_pin(root)
    _check_pin_metadata(root)
    profile = build_profile(root, change)
    tasks_path = tasks or f"openspec/changes/{change}/tasks.md"
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as handle:
        json.dump(profile, handle, ensure_ascii=False)
        profile_path = handle.name
    env = dict(os.environ)
    vendor = str(root / "tools" / "vendor")
    env["PYTHONPATH"] = vendor + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    args = [
        sys.executable,
        "-m",
        "ai_delivery_toolchain.delivery_cli",
        "check",
        "--root",
        str(root),
        "--tasks",
        tasks_path,
        "--change",
        change,
        "--profile",
        profile_path,
        "--openspec",
        str(root / "tools" / "openspec"),
    ]
    if validate_json:
        args.extend(["--validate-json", validate_json])
    if apply_json:
        args.extend(["--apply-json", apply_json])
    if ci_json:
        args.extend(["--ci-json", ci_json])
    try:
        completed = subprocess.run(args, cwd=root, env=env, capture_output=True, text=True)
    finally:
        Path(profile_path).unlink(missing_ok=True)
    if completed.stdout:
        print(completed.stdout.strip())
    if completed.stderr:
        print(completed.stderr.strip(), file=sys.stderr)
    return completed.returncode


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--change")
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--tasks")
    parser.add_argument("--ci-json")
    parser.add_argument("--validate-json")
    parser.add_argument("--apply-json")
    parser.add_argument("--pin-only", action="store_true")
    args = parser.parse_args()
    try:
        root = Path(args.root).resolve()
        if args.pin_only:
            _check_pin_metadata(root)
            load_pin(root)
            print(f"PASS delivery pin v0.4.0 ({root / 'tools/vendor/ai_delivery_toolchain/PIN.json'})")
            return 0
        if not args.change:
            raise ValueError("非 --pin-only 模式必须提供 --change")
        return run(args.change, root, args.tasks, args.ci_json, args.validate_json, args.apply_json)
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
