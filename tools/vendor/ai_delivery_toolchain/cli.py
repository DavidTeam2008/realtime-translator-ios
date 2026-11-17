"""Command line entry point for the delivery toolchain."""
from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
from pathlib import Path

from .junit_strict import StrictJUnitError, count_file
from .manifest import (
    ManifestError,
    build_manifest,
    load_manifest,
    verify_manifest,
    write_manifest,
)
from .xcresult import ConversionError, convert_bundle

TOOLCHAIN_VERSION = "0.1.0"
ENV_KEYS = ("id", "host", "xcode", "xcresulttool")
TARGET_FLAGS = {
    "project": "project",
    "scheme": "scheme",
    "destination": "destination",
    "derived_data_path": "derivedDataPath",
    "result_bundle_path": "resultBundlePath",
    "only_testing": "onlyTesting",
}


class ToolchainError(RuntimeError):
    pass


def _run_text(command: list[str], label: str) -> str:
    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ToolchainError(f"无法读取 {label}：{exc}") from exc
    if completed.returncode != 0:
        raise ToolchainError(f"读取 {label} 失败（exit {completed.returncode}）")
    lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    if not lines:
        raise ToolchainError(f"读取 {label} 没有输出")
    return " / ".join(lines[:2])


def _detect_environment(overrides: dict[str, str]) -> dict[str, str]:
    values = {"id": "local-simulator"}
    if "host" not in overrides:
        version = platform.mac_ver()[0]
        if not version:
            raise ToolchainError("无法识别 macOS 版本；用 --environment host=... 显式提供")
        values["host"] = f"macOS {version}"
    if "xcode" not in overrides:
        values["xcode"] = _run_text(["xcodebuild", "-version"], "Xcode 版本")
    if "xcresulttool" not in overrides:
        values["xcresulttool"] = _run_text(["xcrun", "xcresulttool", "version"], "xcresulttool 版本")
    values.update(overrides)
    return {key: values[key] for key in ENV_KEYS}


def _parse_environment(pairs: list[str]) -> dict[str, str]:
    overrides: dict[str, str] = {}
    for pair in pairs:
        if "=" not in pair:
            raise ToolchainError(f"--environment 需要 KEY=VALUE：{pair!r}")
        key, value = pair.split("=", 1)
        key = key.strip()
        if key not in ENV_KEYS:
            raise ToolchainError(f"--environment 未知键 {key!r}（可用：{', '.join(ENV_KEYS)}）")
        if key in overrides:
            raise ToolchainError(f"--environment 重复键：{key!r}")
        if not value.strip():
            raise ToolchainError(f"--environment {key} 不能为空")
        overrides[key] = value.strip()
    return overrides


def _target_from_args(args: argparse.Namespace, result_bundle_path: str | None = None) -> dict:
    target_json = getattr(args, "target_json", None)
    if target_json:
        try:
            document = json.loads(Path(target_json).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ToolchainError(f"--target-json 无法读取：{exc}") from exc
        if not isinstance(document, dict):
            raise ToolchainError("--target-json 顶层必须是 object")
        return document
    target = {}
    for arg_name, key in TARGET_FLAGS.items():
        value = result_bundle_path if key == "resultBundlePath" and result_bundle_path else getattr(args, arg_name)
        if not value:
            raise ToolchainError(f"缺少 --{arg_name.replace('_', '-')}（或 --target-json）")
        target[key] = value
    return target


def _same_directory(first: Path, second: Path) -> bool:
    return first.resolve().parent == second.resolve().parent


def cmd_convert(args: argparse.Namespace) -> int:
    xcresult_path = Path(args.xcresult).expanduser()
    junit_path = Path(args.junit).expanduser()
    manifest_path = Path(args.manifest).expanduser()
    if not _same_directory(junit_path, manifest_path):
        raise ToolchainError("--junit 与 --manifest 必须在同一目录（manifest 按文件名绑定）")
    overrides = _parse_environment(args.environment)
    environment = _detect_environment(overrides)
    target = _target_from_args(args, result_bundle_path=str(xcresult_path))
    redact_paths = tuple(str(Path(item).expanduser().resolve()) for item in args.redact_path)
    redact_paths += (str(Path.cwd().resolve()),)

    junit_written = False
    manifest_written = False
    try:
        conversion = convert_bundle(
            xcresult_path,
            junit_path,
            testsuites_name=args.only_testing,
            redact_paths=redact_paths,
        )
        junit_written = True
        manifest = build_manifest(
            claim=args.claim,
            target=target,
            environment=environment,
            conversion=conversion,
            xcresult_name=xcresult_path.name,
            junit_name=junit_path.name,
            run_id=args.run_id,
            created_at=args.created_at,
        )
        write_manifest(manifest_path, manifest)
        manifest_written = True
        verify_manifest(
            manifest,
            junit_path.read_bytes(),
            expected_claim=args.claim,
            expected_target=target,
            junit_name=junit_path.name,
        )
    except Exception:
        if manifest_written:
            manifest_path.unlink(missing_ok=True)
        if junit_written:
            junit_path.unlink(missing_ok=True)
        raise

    summary = {
        "claim": manifest["claim"],
        "runId": manifest["runId"],
        "junit": str(junit_path),
        "manifest": str(manifest_path),
        "tests": manifest["junit"]["tests"],
        "passed": manifest["junit"]["passed"],
        "failed": manifest["junit"]["failed"],
        "skipped": manifest["junit"]["skipped"],
        "caseIdsSha256": manifest["junit"]["caseIdsSha256"],
    }
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    manifest_path = Path(args.manifest).expanduser()
    junit_path = Path(args.junit).expanduser()
    if not _same_directory(junit_path, manifest_path):
        raise ToolchainError("--junit 与 --manifest 必须在同一目录")
    manifest = load_manifest(manifest_path)
    target = _target_from_args(args)
    text = verify_manifest(
        manifest,
        junit_path.read_bytes(),
        expected_claim=args.claim,
        expected_target=target,
        junit_name=junit_path.name,
    )
    print(f"PASS {text}")
    return 0


def cmd_recount(args: argparse.Namespace) -> int:
    counts = count_file(Path(args.junit).expanduser())
    print(
        f"tests={counts.tests} passed={counts.passed} failed={counts.failed} "
        f"skipped={counts.skipped} durationSec={counts.duration:.3f}"
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ai-delivery-toolchain",
        description="Convert xcresult into strict JUnit plus a single-run manifest.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {TOOLCHAIN_VERSION}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    convert = subparsers.add_parser("convert", help="convert an xcresult bundle and write a manifest")
    convert.add_argument("--xcresult", required=True)
    convert.add_argument("--junit", required=True)
    convert.add_argument("--manifest", required=True)
    convert.add_argument("--claim", required=True)
    convert.add_argument("--project", required=True)
    convert.add_argument("--scheme", required=True)
    convert.add_argument("--destination", required=True)
    convert.add_argument("--derived-data-path", required=True)
    convert.add_argument("--only-testing", required=True)
    convert.add_argument("--environment", action="append", default=[], metavar="KEY=VALUE")
    convert.add_argument("--redact-path", action="append", default=[])
    convert.add_argument("--run-id")
    convert.add_argument("--created-at")
    convert.set_defaults(func=cmd_convert)

    verify = subparsers.add_parser("verify", help="verify a manifest against its JUnit")
    verify.add_argument("--manifest", required=True)
    verify.add_argument("--junit", required=True)
    verify.add_argument("--claim", required=True)
    verify.add_argument("--target-json")
    verify.add_argument("--project")
    verify.add_argument("--scheme")
    verify.add_argument("--destination")
    verify.add_argument("--derived-data-path")
    verify.add_argument("--result-bundle-path")
    verify.add_argument("--only-testing")
    verify.set_defaults(func=cmd_verify)

    recount = subparsers.add_parser("recount", help="strictly recount a JUnit XML")
    recount.add_argument("--junit", required=True)
    recount.set_defaults(func=cmd_recount)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (ToolchainError, ConversionError, ManifestError, StrictJUnitError, OSError) as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
